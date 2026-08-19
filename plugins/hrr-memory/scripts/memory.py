#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 K. S. Ernest (iFire) Lee
"""Fabric memory: ETNF relations as USD layers, built into a SQLite index.

The .usda relations are the source and the only thing committed. The SQLite
database and its HRR vectors are derived: encode_atom is SHA-256 over the text,
so `build` reproduces them byte for byte from the same relations on any machine.
Committing both would store the same facts twice, and the derived copy is 31x
the size of the source it came from.

The vector is the index. A query is encoded the same way and compared by phase
cosine similarity, so recall is nearest-neighbour over meaning rather than a
substring match. Vectors are byte-identical to `tw_hrr.hpp` and to the planner's
holographic.py, which is what lets the same rows be read from C++ or Python.

The database is an ordinary SQLite file. It opens through the `weft_fdb` VFS when
one is registered -- the same VFS `datasource-queen` opens `queen` with -- and as a
plain file when none is, so the rows are the same either way.

  memory.py build                      usda -> sqlite, with the vectors
  memory.py add "<content>" --kind feedback --entities fabric cassie
  memory.py recall "<query>" [-n 5]
  memory.py verify
"""
import argparse, datetime, hashlib, re, sqlite3, subprocess, sys, uuid, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import hrr

ROOT = pathlib.Path(__file__).resolve().parents[1] / "memory"
DB = ROOT / "fabric.sqlite3"          # derived, gitignored
RELATIONS = ("kinds", "entities", "memory", "memory_entity")
# Each relation sorts on its own key rather than on whatever column happens to come first
# alphabetically. The keys are uuid7, so sorting on them is sorting by creation time, and a
# new tuple lands at the end of the file instead of in the middle: the diff for one added
# memory is the lines that were added. Sorting memory_entity by entity_id would scatter them.
# The Parquet Variant type each column holds, by the spec's own primitive type ids.
# https://parquet.apache.org/docs/file-format/types/variantencoding/
#
# The spec fixes 21 primitive types and does not say how JSON maps onto them, which is the
# whole hazard of storing these relations as JSON: a uuid, a date and a string are all bare
# JSON strings, so the type survives nowhere and "equivalent to the parquet" is a claim
# nobody can check. int8 through int64 and decimal4 through decimal16 collapse the same way,
# which is the reason the identifiers are uuid (id 20) rather than the integers they were.
#
# Declaring the id here makes the claim checkable: verify round-trips every value through
# the binary encoding the spec names and fails when the value is not exactly what that
# encoding gives back. A date that is not a real date, an id that is not sixteen bytes, or a
# string that is not valid UTF-8 stops being a string that merely looks wrong.
VARIANT = {
    "kinds": {"kind_id": 20, "name": 16},
    "entities": {"entity_id": 20, "name": 16},
    # `recorded` is the instant and `utc_offset` is the offset it was observed at. The two are
    # independent -- neither can be computed from the other -- and everything anybody wants
    # from a timestamp derives from the pair: the civil local time, its date, the day of the
    # week. `created` used to sit here as a date beside them and was removed for exactly that
    # reason. A date that is a function of a column already present is a second source of
    # truth for one fact, and the two disagree the first time one is edited and the other is
    # not. It is now computed where it is needed, which is `tuple_id`.
    #
    # Variant type 12 is UTC-normalised: it stores micros since the epoch and has nowhere to
    # put an offset. That is the whole reason the offset is its own column rather than being
    # carried inside an RFC 3339 string -- encoding "…-07:00" as a 12 and reading it back
    # gives the same instant spelled in UTC, so the offset would be silently dropped by the
    # very check that is supposed to prove nothing was lost.
    "memory": {"memory_id": 20, "kind_id": 20, "content": 16, "recorded": 12, "utc_offset": 16},
    "memory_entity": {"memory_id": 20, "entity_id": 20},
}
VARIANT_NAMES = {11: "date", 12: "timestamp", 16: "string", 20: "uuid"}

SORT_KEYS = {
    "kinds": ("kind_id",),
    "entities": ("entity_id",),
    "memory": ("memory_id",),
    "memory_entity": ("memory_id", "entity_id"),
}
VFS = "weft_fdb"          # registered by store-plane; absent means a plain file
KINDS = ("user", "feedback", "project", "reference")

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
  id       TEXT PRIMARY KEY,
  kind     TEXT NOT NULL,
  content  TEXT NOT NULL,
  entities TEXT NOT NULL,
  dim      INT  NOT NULL,
  vec      BLOB NOT NULL,
  recorded   TEXT NOT NULL,
  utc_offset TEXT NOT NULL,
  -- Derived from the two above by civil_date. Present because queries want a date and
  -- absent from the layers for the same reason: there, it would be a second source of truth.
  created    TEXT NOT NULL
);
-- What produced the vectors, so a reader can tell whether they are still valid.
CREATE TABLE IF NOT EXISTS provenance (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);
"""


def connect(path=DB):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        con = sqlite3.connect(f"file:{path}?vfs={VFS}", uri=True)
    except sqlite3.Error:
        con = sqlite3.connect(path)      # no store-plane VFS registered here
    con.executescript(SCHEMA)
    return con


def civil_date(recorded, utc_offset):
    """The calendar date the instant fell on where it was recorded.

    This is the derivation that lets `created` stop being stored. A date is what `tuple_id`
    wants and what a reader asks for, and it is a function of the pair rather than a fact of
    its own -- the same instant is two different dates either side of a date line, which is
    exactly why the offset has to be part of the derivation rather than assumed to be UTC.
    """
    tz = datetime.datetime.strptime(utc_offset, "%z").tzinfo
    return datetime.datetime.fromisoformat(recorded).astimezone(tz).date().isoformat()


def now_recorded():
    """The instant, and the offset this desk is keeping civil time at, as a pair."""
    now = datetime.datetime.now().astimezone()
    return (now.astimezone(datetime.timezone.utc).isoformat(timespec="microseconds"),
            now.strftime("%z")[:3] + ":" + now.strftime("%z")[3:])


def tuple_id(kind, key, created):
    """A time-ordered identifier derived from the tuple, RFC 9562 version 8.

        48 bits  the creation date in unix milliseconds, big-endian
         4 bits  version 8, which the RFC reserves for exactly this
        74 bits  SHA-256 over the relation and the tuple's natural key

    Not a counter. `max(id) + 1` needs every existing tuple in hand to allocate one, so two
    people adding a memory on two branches take the same number and the merge keeps one
    row's content under the other's edges.

    Not a v7 either, though v7 was tried first and is what the shape is copied from. A v7
    takes its low bits from the clock and a random source, so it is not reproducible: regenerate
    these relations from any source -- a re-seed, a rebuild from prose, a second machine
    replaying the same additions -- and every identifier changes, every line of every file
    changes with it, and the diff says nothing about what actually moved. Deriving the low
    bits from the tuple instead means the same fact gets the same identifier wherever it is
    built, so a regenerated file is byte-identical where the facts are and differs only where
    they are not.

    The date prefix keeps the sort time-ordered, which is what makes an added tuple append to
    a sorted file rather than land in the middle of it. Two tuples with the same natural key
    on the same day are the same fact and collapse to one row, which is the behaviour a set
    of facts should have.
    """
    ms = int(datetime.datetime.strptime(created, "%Y-%m-%d")
             .replace(tzinfo=datetime.timezone.utc).timestamp()) * 1000
    h = hashlib.sha256(f"{kind}\0{key}".encode()).digest()
    b = bytearray(ms.to_bytes(6, "big") + h[:10])
    b[6] = 0x80 | (b[6] & 0x0F)          # version 8: custom
    b[8] = 0x80 | (b[8] & 0x3F)          # variant 10
    x = b.hex()
    return f"{x[0:8]}-{x[8:12]}-{x[12:16]}-{x[16:20]}-{x[20:32]}"


def variant_encode(type_id, value):
    """The value as the Variant spec's physical encoding for that primitive type id.

    Only the three this data uses are implemented, each exactly as the spec states it:

      11  date       4 byte little-endian, days since 1970-01-01
      12  timestamp  8 byte little-endian, micros since 1970-01-01T00:00:00Z, UTC-normalised
      16  string     4 byte little-endian size, then UTF-8 bytes
      20  uuid       16 bytes, big-endian

    Raising is the point. An encoder that quietly accepts whatever it is handed cannot tell
    a date from a string that resembles one, which is the ambiguity JSON introduces and the
    reason this exists at all.
    """
    if type_id == 11:
        days = (datetime.date.fromisoformat(value) - datetime.date(1970, 1, 1)).days
        return days.to_bytes(4, "little", signed=True)
    if type_id == 12:
        t = datetime.datetime.fromisoformat(value)
        if t.tzinfo is None:
            raise ValueError(f"{value!r} has no offset; a type 12 is a point in time")
        micros = round(t.timestamp() * 1_000_000)
        return micros.to_bytes(8, "little", signed=True)
    if type_id == 16:
        b = value.encode("utf-8")
        return len(b).to_bytes(4, "little") + b
    if type_id == 20:
        return uuid.UUID(value).bytes
    raise ValueError(f"variant type {type_id} is not implemented here")


def variant_decode(type_id, blob):
    """The inverse, so a round trip can be compared against the value it started from."""
    if type_id == 11:
        return (datetime.date(1970, 1, 1)
                + datetime.timedelta(days=int.from_bytes(blob, "little", signed=True))).isoformat()
    if type_id == 12:
        micros = int.from_bytes(blob, "little", signed=True)
        return datetime.datetime.fromtimestamp(
            micros / 1_000_000, datetime.timezone.utc).isoformat(timespec="microseconds")
    if type_id == 16:
        n = int.from_bytes(blob[:4], "little")
        return blob[4:4 + n].decode("utf-8")
    if type_id == 20:
        return str(uuid.UUID(bytes=blob))
    raise ValueError(f"variant type {type_id} is not implemented here")


USDA_HEADER = "#usda 1.0\n(\n    customLayerData = {\n"


def _usda_escape(s):
    """USD string literal quoting: backslash and double quote, then the C escapes."""
    return (s.replace("\\", "\\\\").replace('"', '\\"')
             .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))


def _usda_unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append({"n": "\n", "r": "\r", "t": "\t"}.get(nxt, nxt)); i += 2
        else:
            out.append(c); i += 1
    return "".join(out)


def _write_relations(rel):
    """One USD layer per relation, as a typed dictionary keyed by the relation's own key.

    Written with the standard library rather than through pxr, on purpose. The V-Sekai
    codeless schemas in openusd-fabric already record why: their own docstring says
    skipCodeGeneration exists to avoid "the ABI trap between Blender's bundled USD, Unity's
    bundled USD, and the build idtx-flow links against". A pip-installed pxr would be a
    fourth USD in that list, pinned to this script, for the sake of reading four flat tables
    of strings. The layer this emits is plain canonical usda, so every USD already in the
    workspace reads it and none of them is a dependency of this file.

    What keeps the emitter honest is not care, it is usdcat: verify re-emits every layer
    through the system USD and requires the bytes back to be the bytes written. An emitter
    that drifts from canonical form fails there rather than at the next reader.

    The key is not repeated inside its value, and memory_entity groups its edges under the
    memory they belong to. That is a storage encoding; _read_relations returns flat tuples,
    so the relations stay in the first normal form every other check reads them as.
    """
    for n, rows in rel.items():
        assert all(v is not None for r in rows for v in r.values()), f"nulls in {n} violate ETNF"
        d = {}
        if n == "memory_entity":
            for r in rows:
                d.setdefault(r["memory_id"], []).append(r["entity_id"])
            body = "".join(
                f'            dictionary "{k}" = {{\n'
                f'                string[] entity_id = [{", ".join(chr(34) + _usda_escape(e) + chr(34) for e in sorted(set(v)))}]\n'
                f'            }}\n'
                for k, v in sorted(d.items()))
        else:
            key = SORT_KEYS[n][0]
            for r in rows:
                d[r[key]] = {c: v for c, v in r.items() if c != key}
            body = "".join(
                f'            dictionary "{k}" = {{\n'
                + "".join(f'                string {c} = "{_usda_escape(v[c])}"\n' for c in sorted(v))
                + f'            }}\n'
                for k, v in sorted(d.items()))
        text = (USDA_HEADER + f"        dictionary {n} = {{\n" + body
                + "        }\n    }\n)\n\n")
        (ROOT / f"{n}.usda").write_text(text, encoding="utf-8")


_ENTRY = re.compile(r'^\s*dictionary "([^"]+)" = \{$')
_STR = re.compile(r'^\s*string (\w+) = "(.*)"$')
_ARR = re.compile(r'^\s*string\[\] (\w+) = \[(.*)\]$')


def _read_relations():
    """The relations, from one USD layer each, parsed over the subset this file writes.

    Deliberately narrow. It reads the canonical form _write_relations emits and nothing
    else, which is safe only because usdcat is what certifies that form: a layer that parses
    here but is not canonical usda fails verify, and a layer that is canonical usda but was
    written by something else is not what this reads. The narrowness is the contract.
    """
    rel = {}
    for n in RELATIONS:
        rows, key = [], None
        for line in (ROOT / f"{n}.usda").read_text(encoding="utf-8").splitlines():
            m = _ENTRY.match(line)
            if m:
                key = _usda_unescape(m.group(1)); cur = {}
                if n != "memory_entity":
                    cur[SORT_KEYS[n][0]] = key
                    rows.append(cur)
                continue
            m = _ARR.match(line)
            if m and key is not None:
                for e in re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(2)):
                    rows.append({"memory_id": key, "entity_id": _usda_unescape(e)})
                continue
            m = _STR.match(line)
            if m and key is not None:
                cur[m.group(1)] = _usda_unescape(m.group(2))
        assert all(v is not None for r in rows for v in r.values()), f"nulls in {n} violate ETNF"
        rel[n] = rows
    return rel


def usdcat_roundtrip(path):
    """The bytes system USD gives back for a layer, or None when it will not read it."""
    out = pathlib.Path(str(path) + ".check.usda")
    try:
        r = subprocess.run(["usdcat", str(path), "-o", str(out)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None, (r.stderr.strip().splitlines() or [""])[-1][:160]
        return out.read_text(encoding="utf-8"), None
    finally:
        out.unlink(missing_ok=True)


def build(con):
    """Join the relations, encode each fact, and fill the index. Idempotent.

    Entities are sorted for a stable `entities` column. The vectors no longer
    need it: they are stored on the uint16 phase grid, which absorbs the ~1e-14
    float difference that component order used to produce, so the bytes are equal
    either way.
    """
    rel = _read_relations()
    kind = {r["kind_id"]: r["name"] for r in rel["kinds"]}
    ent = {r["entity_id"]: r["name"] for r in rel["entities"]}
    by_mem = {}
    for r in rel["memory_entity"]:
        by_mem.setdefault(r["memory_id"], []).append(ent[r["entity_id"]])
    con.execute("DELETE FROM memory")
    for r in rel["memory"]:
        ents = sorted(by_mem.get(r["memory_id"], []))
        vec = hrr.encode_fact(r["content"], ents)
        con.execute(
            "INSERT INTO memory(id, kind, content, entities, dim, vec, recorded,"
            " utc_offset, created) VALUES (?,?,?,?,?,?,?,?,?)",
            (r["memory_id"], kind[r["kind_id"]], r["content"], " ".join(ents),
             hrr.DIM, hrr.phases_to_u16(vec), r["recorded"], r["utc_offset"],
             # Derived, and only here. The index may hold a computed column because it is
             # rebuilt from the layers on every build; the layers may not.
             civil_date(r["recorded"], r["utc_offset"])))
    con.commit()
    return len(rel["memory"])


def add(con, content, kind, entities):
    if kind not in KINDS:
        raise SystemExit(f"kind must be one of {KINDS}")
    rel = _read_relations()
    recorded, utc_offset = now_recorded()
    today = civil_date(recorded, utc_offset)
    # Kinds and entities take the store's own first date rather than today's, because that is
    # the date `verify` re-derives them from. Stamping them with today instead passes on the
    # day the store is created -- when the two dates are the same -- and fails for every
    # entity coined afterwards, which is a gate that only goes red on the second day of use.
    # The name's hash is unaffected either way: only the 48-bit date prefix moved.
    first = min((civil_date(r["recorded"], r["utc_offset"]) for r in rel["memory"]),
                default=today)
    if kind not in {r["name"] for r in rel["kinds"]}:
        rel["kinds"].append({"kind_id": tuple_id("kind", kind, first), "name": kind})
    kid = {r["name"]: r["kind_id"] for r in rel["kinds"]}[kind]
    for e in entities:
        if e not in {r["name"] for r in rel["entities"]}:
            rel["entities"].append({"entity_id": tuple_id("entity", e, first), "name": e})
    eid = {r["name"]: r["entity_id"] for r in rel["entities"]}
    mid = tuple_id("memory", content, today)
    rel["memory"].append({"memory_id": mid, "kind_id": kid, "content": content,
                          "recorded": recorded, "utc_offset": utc_offset})
    for e in entities:
        rel["memory_entity"].append({"memory_id": mid, "entity_id": eid[e]})
    _write_relations(rel)
    build(con)


def edit(con, match, content):
    """Rewrite one memory's content, and everything that derives from it.

    Correcting a memory by hand is four steps and three of them are invisible until a gate
    fails. memory_id is tuple_id(content, date), so new words mean a new id; the dictionary
    key in memory.usda is that id; every memory_entity edge points at it; and the relations
    are sorted, so the new id belongs somewhere else in the file. Doing that by hand on
    2026-08-19 failed twice -- once on the derivation, once on canonical ordering -- and each
    failure was a separate round trip through verify.

    They are one operation because they are one change. The date is not restamped: the fact
    was recorded when it was recorded, and a correction is not a new observation.
    """
    rel = _read_relations()
    hits = [r for r in rel["memory"]
            if r["memory_id"].startswith(match) or match.lower() in r["content"].lower()]
    if not hits:
        raise SystemExit(f"no memory matches {match!r}")
    if len(hits) > 1:
        for r in hits:
            print(f"  {r['memory_id']}  {r['content'][:70]}")
        raise SystemExit(f"{len(hits)} memories match {match!r}; give an id prefix")

    row = hits[0]
    old_id = row["memory_id"]
    new_id = tuple_id("memory", content, civil_date(row["recorded"], row["utc_offset"]))
    if new_id == old_id:
        print("content is unchanged; nothing to do")
        return
    row["content"] = content
    row["memory_id"] = new_id
    moved = 0
    for e in rel["memory_entity"]:
        if e["memory_id"] == old_id:
            e["memory_id"] = new_id
            moved += 1
    _write_relations(rel)
    build(con)
    print(f"edited {old_id} -> {new_id}, {moved} edge(s) followed")


def recall(con, query, n=5):
    q = hrr.encode_text(query)
    rows = []
    for mid, kind, content, ents, blob in con.execute(
            "SELECT id, kind, content, entities, vec FROM memory"):
        # The stored fact is a bundle; its content component is bound to the
        # content role, so unbind by that role before comparing.
        stored = hrr.unbind(hrr.u16_to_phases(blob), hrr.encode_atom(hrr.ROLE_CONTENT))
        rows.append((hrr.similarity(q, stored), mid, kind, content, ents))
    rows.sort(reverse=True)
    return rows[:n]


def verify(con):
    """Every stored vector must re-encode to itself, and every id must re-derive from its tuple.

    The second half is what makes the identifiers auditable rather than merely present. An id
    that no longer equals tuple_id of the row it sits on is an id that came from somewhere
    else -- a hand edit, a generator that was not this one, or a random source -- and that is
    the drift a random identifier introduces silently: nothing else in the file would notice.
    """
    bad = 0
    rel = _read_relations()
    # Every value must survive the encoding its column declares, and this runs first: a value
    # that is not a valid uuid or date is not a broken reference or a wrong identifier, it is
    # not the type it claims, and reporting it as anything else sends the reader to the wrong
    # file. Ordering is part of what a check says.
    for n, cols in VARIANT.items():
        for r in rel[n]:
            for col, tid in cols.items():
                try:
                    back = variant_decode(tid, variant_encode(tid, r[col]))
                except Exception as e:
                    print(f"  {n}.{col}: {r[col]!r} is not a valid "
                          f"{VARIANT_NAMES[tid]} (variant type {tid}): {e}"); bad += 1
                    continue
                if back != r[col]:
                    print(f"  {n}.{col}: {r[col]!r} round-trips through "
                          f"{VARIANT_NAMES[tid]} as {back!r}"); bad += 1
    if bad:
        print(f"{bad} rows wrong")
        return bad

    # System USD must accept every layer and give back the bytes that were written. This
    # replaces the sort-order check that used to sit here: usdcat re-emits canonical form,
    # which sorts the keys, so a layer whose entries are out of order comes back different
    # and fails. One check now covers both, and the authority for what canonical means is
    # USD rather than this file.
    #
    # The order still matters for the same two reasons it did. An added tuple appends to a
    # sorted file rather than landing in its middle, and Parquet's DELTA_BYTE_ARRAY stores
    # each byte array as a prefix length into the previous entry plus the suffix, so sorted
    # keys that share a prefix cost only their difference. Measured over these relations,
    # sorted against the same values shuffled, that is worth 2.3x on memory_entity, where
    # the same memory_id repeats across edges, and almost nothing on the columns of distinct
    # ids -- a uuid8 shares its date prefix whatever the order and the bytes below are hash.
    for n in RELATIONS:
        path = ROOT / f"{n}.usda"
        got, err = usdcat_roundtrip(path)
        if err is not None:
            print(f"  {n}.usda: system USD will not read it: {err}"); bad += 1
        elif got != path.read_text(encoding="utf-8"):
            print(f"  {n}.usda: is not canonical USD; usdcat re-emits it differently"); bad += 1
    if bad:
        print(f"{bad} rows wrong")
        return bad

    # Every reference must resolve before anything else is asked. A half-migrated set of
    # relations -- memory.jsonl on one generation of identifiers and kinds.jsonl on the next
    # -- is exactly what a KeyError deep inside build() reports badly and a review does not
    # catch at all, because each file is internally well formed and only the join is broken.
    kn = {r["kind_id"] for r in rel["kinds"]}
    en = {r["entity_id"] for r in rel["entities"]}
    mn = {r["memory_id"] for r in rel["memory"]}
    for r in rel["memory"]:
        if r["kind_id"] not in kn:
            print(f"  memory {r['memory_id']}: kind_id {r['kind_id']} is in no kinds tuple"); bad += 1
    for r in rel["memory_entity"]:
        if r["memory_id"] not in mn:
            print(f"  edge: memory_id {r['memory_id']} is in no memory tuple"); bad += 1
        if r["entity_id"] not in en:
            print(f"  edge: entity_id {r['entity_id']} is in no entities tuple"); bad += 1
    if bad:
        print(f"{bad} rows wrong")
        return bad
    first = min(civil_date(r["recorded"], r["utc_offset"]) for r in rel["memory"])
    for r in rel["kinds"]:
        if r["kind_id"] != tuple_id("kind", r["name"], first):
            print(f"  kind {r['name']}: id does not derive from its tuple"); bad += 1
    for r in rel["entities"]:
        if r["entity_id"] != tuple_id("entity", r["name"], first):
            print(f"  entity {r['name']}: id does not derive from its tuple"); bad += 1
    for r in rel["memory"]:
        if r["memory_id"] != tuple_id("memory", r["content"],
                                      civil_date(r["recorded"], r["utc_offset"])):
            print(f"  memory {r['memory_id']}: id does not derive from its tuple"); bad += 1
    for mid, content, ents, dim, blob in con.execute(
            "SELECT id, content, entities, dim, vec FROM memory"):
        want = hrr.phases_to_u16(hrr.encode_fact(content, ents.split() if ents else []))
        if want != blob:
            print(f"  row {mid}: vector does not match its own content"); bad += 1
        if dim != hrr.DIM:
            print(f"  row {mid}: dim {dim} != {hrr.DIM}"); bad += 1
    print(f"{'MEMORY VERIFY PASS' if bad == 0 else f'{bad} rows wrong'}")
    return bad


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add");    a.add_argument("content"); a.add_argument("--kind", required=True); a.add_argument("--entities", nargs="*", default=[])
    e = sub.add_parser("edit");   e.add_argument("match", help="memory id prefix, or text it contains"); e.add_argument("--content", required=True)
    r = sub.add_parser("recall"); r.add_argument("query");   r.add_argument("-n", type=int, default=5)
    sub.add_parser("verify"); sub.add_parser("build")
    args = p.parse_args()
    con = connect()
    if args.cmd == "build":
        print(f"built {build(con)} memories into {DB.name}")
    elif args.cmd == "add":
        add(con, args.content, args.kind, args.entities); print("stored")
    elif args.cmd == "edit":
        edit(con, args.match, args.content)
    elif args.cmd == "recall":
        for s, mid, kind, content, ents in recall(con, args.query, args.n):
            print(f"  {s:+.4f}  [{kind}] {content}" + (f"  ({ents})" if ents else ""))
    else:
        sys.exit(1 if verify(con) else 0)


if __name__ == "__main__":
    main()
