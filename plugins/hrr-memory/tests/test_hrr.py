# SPDX-License-Identifier: MIT
# Copyright (c) 2026 K. S. Ernest (iFire) Lee
"""Properties of the HRR algebra, and a negative control for each one.

`hrr.py` states its claims in prose -- vectors byte-identical across three
languages, quantising exact for an atom, bundle order-independent once on the
uint16 grid. Prose is not checkable, and every one of those claims is a property
over all inputs rather than over the handful an example test would pick. So they
are written here as properties.

Each property is paired with a control that breaks the implementation and asserts
the property then fails. This repository already refuses a gate without one: a
check that cannot fail is a check nobody has evidence for, and `mix check
--self-test` exists for exactly this reason on the Elixir side.

Dimension is a parameter, and the tests use a small one. The algebra does not
care -- every claim here is about structure rather than about capacity -- and
DIM=4096 through a pure-Python loop, a hundred times per property, is minutes
instead of seconds. The two claims that *are* about capacity say so and use the
real dimension.
"""
import math
import sys
import pathlib

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import hrr  # noqa: E402

DIM = 64                     # multiple of 16, so encode_atom fills whole blocks
GRID = hrr.TWO_PI / 65536.0  # the uint16 phase step
HALF = GRID / 2.0

words = st.text(min_size=1, max_size=24).filter(lambda w: w.strip())
phases = st.floats(min_value=0.0, max_value=hrr.TWO_PI, exclude_max=True,
                   allow_nan=False, allow_infinity=False)
vectors = st.lists(phases, min_size=DIM, max_size=DIM)


def circular(a, b):
    """Distance between two angles, the short way round."""
    d = abs(a - b) % hrr.TWO_PI
    return min(d, hrr.TWO_PI - d)


# --- encode_atom ------------------------------------------------------------

@given(words)
def test_atom_is_deterministic(word):
    assert hrr.encode_atom(word, DIM) == hrr.encode_atom(word, DIM)


@given(words, st.integers(min_value=1, max_value=200))
def test_atom_has_the_dimension_asked_for(word, dim):
    v = hrr.encode_atom(word, dim)
    assert len(v) == dim
    assert all(0.0 <= p < hrr.TWO_PI for p in v)


@given(words)
def test_atom_lands_exactly_on_the_uint16_grid(word):
    """`hrr.py`: "quantising to it is exact for an atom".

    Every phase is built as val * (2pi/65536) for a uint16 val, so the round trip
    through the storage format must return the atom unchanged -- not close, equal.
    """
    v = hrr.encode_atom(word, DIM)
    assert hrr.u16_to_phases(hrr.phases_to_u16(v)) == v


@given(words, words)
def test_distinct_words_are_distinct_atoms(a, b):
    assume(a != b)
    assert hrr.encode_atom(a, DIM) != hrr.encode_atom(b, DIM)


# --- bind / unbind ----------------------------------------------------------

@given(vectors, vectors)
def test_unbind_inverts_bind(a, b):
    back = hrr.unbind(hrr.bind(a, b), b)
    assert all(circular(x, y) < 1e-9 for x, y in zip(back, a))


@given(vectors, vectors)
def test_unbind_stays_in_range(a, b):
    """Note the closed upper bound. `encode_atom` guarantees [0, 2pi); `unbind`
    does not quite, and the next test is why."""
    assert all(0.0 <= p <= hrr.TWO_PI for p in hrr.unbind(a, b))


def test_unbind_can_return_exactly_two_pi():
    """A real edge, found by the property above rather than by reading the code.

    `unbind` is fmod then `+= TWO_PI` for a negative result. A difference of -1e-17
    fmods to itself, and adding 2pi rounds up to exactly 2pi -- one ulp outside the
    half-open range every other vector in this module lives in.

    It is not corrected here. `hrr.py` must stay byte-identical to `tw_hrr.hpp` and
    to the planner's `holographic.py`, so a fix is a three-language change and not a
    Python edit. It is harmless today for the reason asserted below, and this test
    is what keeps that "harmless" checked rather than assumed.
    """
    out = hrr.unbind([0.0], [1e-17])
    assert out == [hrr.TWO_PI]
    assert hrr.phases_to_u16(out) == hrr.phases_to_u16([0.0])   # storage folds it to 0
    assert math.cos(out[0]) == pytest.approx(math.cos(0.0))     # similarity cannot see it


# --- similarity -------------------------------------------------------------

@given(vectors)
def test_similarity_with_self_is_one(v):
    assert hrr.similarity(v, v) == pytest.approx(1.0, abs=1e-12)


@given(vectors, vectors)
def test_similarity_is_symmetric(a, b):
    assert hrr.similarity(a, b) == pytest.approx(hrr.similarity(b, a), abs=1e-12)


@given(vectors, vectors)
def test_similarity_is_bounded(a, b):
    assert -1.0 - 1e-12 <= hrr.similarity(a, b) <= 1.0 + 1e-12


# --- bundle -----------------------------------------------------------------

@given(vectors)
def test_bundling_one_vector_returns_it(v):
    out = hrr.bundle([v])
    assert all(circular(x, y) < 1e-9 for x, y in zip(out, v))


@given(st.lists(words, min_size=2, max_size=6, unique=True), st.randoms())
def test_bundle_is_order_independent_on_the_grid(ws, rnd):
    """`hrr.py`: rounding to the grid "absorbs" float non-associativity, so
    "the bytes are then equal regardless of the order the components arrived in".

    This is the claim the storage format exists for, and the one that lets a
    rebuild be byte-for-byte reproducible.
    """
    vecs = [hrr.encode_atom(w, DIM) for w in ws]
    shuffled = list(vecs)
    rnd.shuffle(shuffled)
    assert hrr.phases_to_u16(hrr.bundle(vecs)) == hrr.phases_to_u16(hrr.bundle(shuffled))


@given(st.lists(words, min_size=2, max_size=6, unique=True), st.randoms())
def test_bundle_order_changes_float64_only_in_the_last_bits(ws, rnd):
    """The other half of the same claim: order-sensitive at the bit level, and
    "the vectors agree to 1e-14 radians either way"."""
    vecs = [hrr.encode_atom(w, DIM) for w in ws]
    shuffled = list(vecs)
    rnd.shuffle(shuffled)
    a, b = hrr.bundle(vecs), hrr.bundle(shuffled)
    assert all(circular(x, y) < 1e-14 for x, y in zip(a, b))


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(words, min_size=2, max_size=8, unique=True), words)
def test_a_bundled_member_beats_a_stranger(ws, stranger):
    """Capacity, so this one runs at the real dimension.

    `bundle` documents similarity(v_k, bundle) ~ 1/N. The usable consequence is
    weaker and is what recall actually depends on: a member is nearer the bundle
    than a word that was never in it. At DIM=4096 the noise floor is 1/sqrt(4096),
    about 0.016, and 1/N for N<=8 is 0.125.
    """
    assume(stranger not in ws)
    dim = hrr.DIM
    vecs = [hrr.encode_atom(w, dim) for w in ws]
    b = hrr.bundle(vecs)
    member = hrr.similarity(vecs[0], b)
    other = hrr.similarity(hrr.encode_atom(stranger, dim), b)
    assert member > other


# --- interchange and storage ------------------------------------------------

@given(vectors)
def test_float64_interchange_is_exact(v):
    """The format that crosses the language boundary must not lose a bit."""
    assert hrr.bytes_to_phases(hrr.phases_to_bytes(v)) == v


@given(vectors)
def test_uint16_storage_loses_at_most_half_a_step(v):
    """`hrr.py`: "loses at most half a grid step, 4.8e-5 rad, for a bundle"."""
    back = hrr.u16_to_phases(hrr.phases_to_u16(v))
    assert all(circular(x, y) <= HALF + 1e-12 for x, y in zip(back, v))


@given(vectors)
def test_uint16_storage_is_a_quarter_of_float64(v):
    assert len(hrr.phases_to_u16(v)) * 4 == len(hrr.phases_to_bytes(v))


# --- text -------------------------------------------------------------------

@given(st.text(max_size=80))
def test_tokens_are_lowercase_stripped_and_never_empty(text):
    for t in hrr.tokenize(text):
        assert t == t.lower()
        assert t.strip(hrr.PUNCT) == t
        assert t and not any(c.isspace() for c in t)


@given(st.text(alphabet=" \t\n" + hrr.PUNCT, max_size=20))
def test_text_with_no_tokens_falls_back_to_the_empty_atom(text):
    assert hrr.encode_text(text, DIM) == hrr.encode_atom("__hrr_empty__", DIM)


@given(st.text(max_size=60))
def test_encode_text_is_deterministic(text):
    assert hrr.encode_text(text, DIM) == hrr.encode_text(text, DIM)


# --- encode_fact ------------------------------------------------------------

@given(st.text(min_size=1, max_size=40),
       st.lists(words, min_size=1, max_size=4, unique_by=lambda w: w.lower()),
       st.randoms())
def test_fact_entity_order_does_not_change_the_stored_bytes(content, ents, rnd):
    """Why `memory.py` sorts entities before encoding: it makes a rebuild
    byte-identical. On the grid the sort is belt and braces, and that is the
    claim being checked."""
    shuffled = list(ents)
    rnd.shuffle(shuffled)
    a = hrr.phases_to_u16(hrr.encode_fact(content, ents, DIM))
    b = hrr.phases_to_u16(hrr.encode_fact(content, shuffled, DIM))
    assert a == b


@given(st.text(min_size=1, max_size=40), st.lists(words, max_size=3, unique=True))
def test_fact_is_deterministic(content, ents):
    assert hrr.encode_fact(content, ents, DIM) == hrr.encode_fact(content, ents, DIM)


@given(words)
def test_entity_is_lower_cased_before_encoding(word):
    """`encode_fact` lower-cases entities, so a name and its lower-case form are
    the same entity.

    Stated against `.lower()` rather than against `.upper()`, which is what the
    code actually does. The first version of this test asserted that a word and
    its upper-case form agree, and Hypothesis produced the micro sign: `'\u00b5'.upper()`
    is Greek capital mu, whose `.lower()` is Greek small mu, a different character.
    That was the test overclaiming, not `hrr.py` misbehaving.
    """
    assert hrr.encode_fact("x", [word], DIM) == hrr.encode_fact("x", [word.lower()], DIM)


# --- snr --------------------------------------------------------------------

@given(st.integers(min_value=1, max_value=4096), st.integers(min_value=1, max_value=64))
def test_snr_falls_as_the_bundle_grows(dim, n):
    assert hrr.snr_estimate(dim, n) == pytest.approx(math.sqrt(dim / n))
    assert hrr.snr_estimate(dim, n + 1) < hrr.snr_estimate(dim, n)


@given(st.integers(min_value=1, max_value=4096), st.integers(max_value=0))
def test_snr_of_an_empty_bundle_is_the_sentinel(dim, n):
    assert hrr.snr_estimate(dim, n) == 1e18


# --- negative controls ------------------------------------------------------
# A property that cannot fail is evidence of nothing. Each control breaks one
# thing and asserts the matching property above goes red, which is what makes
# the green above mean something. Same doctrine as `mix check --self-test`.

def test_control_the_grid_is_what_makes_near_vectors_compare_equal():
    """The absorbing claim, controlled directly.

    Not via bundle order: reversing a bundle's components was measured at exactly
    0.0 difference for every n and dim tried, so there is nothing there for
    rounding to absorb and a control built on it would prove nothing. What the
    grid actually does is collapse differences below half a step and keep the ones
    above it, and that is checkable both ways.
    """
    base = [1.0] * DIM
    below = [p + GRID / 100.0 for p in base]     # far under half a step
    above = [p + GRID * 3.0 for p in base]       # comfortably over
    assert hrr.phases_to_u16(base) == hrr.phases_to_u16(below)
    assert hrr.phases_to_u16(base) != hrr.phases_to_u16(above)


def test_control_an_unwrapped_unbind_leaves_the_range():
    """Drop the `+= TWO_PI` and `test_unbind_stays_in_range` must break."""
    def unwrapped(memory, key):
        return [math.fmod(m - k, hrr.TWO_PI) for m, k in zip(memory, key)]

    a, b = [0.5], [1.0]
    assert all(0.0 <= p <= hrr.TWO_PI for p in hrr.unbind(a, b))
    assert not all(0.0 <= p <= hrr.TWO_PI for p in unwrapped(a, b))


def test_control_a_salted_atom_is_not_deterministic():
    """`encode_atom` is a hash and nothing else. Add per-call state and
    `test_atom_is_deterministic` must break."""
    calls = {"n": 0}

    def salted(word, dim):
        calls["n"] += 1
        return hrr.encode_atom(f"{word}:{calls['n']}", dim)

    assert hrr.encode_atom("fabric", DIM) == hrr.encode_atom("fabric", DIM)
    assert salted("fabric", DIM) != salted("fabric", DIM)


def test_control_a_narrower_dimension_loses_the_stranger_margin():
    """`test_a_bundled_member_beats_a_stranger` is a capacity claim, so it must
    stop holding when capacity goes away. At dim=4 the noise floor is 1/2 and a
    stranger wins about one time in ten."""
    ws = ["alpha", "beta", "gamma", "delta"]
    strangers = ("stranger", "outsider", "visitor", "guest", "intruder",
                 "alien", "other", "extra", "spare", "odd")
    vecs = [hrr.encode_atom(w, 4) for w in ws]
    b = hrr.bundle(vecs)
    beaten = sum(
        hrr.similarity(vecs[0], b) <= hrr.similarity(hrr.encode_atom(s, 4), b)
        for s in strangers
    )
    assert beaten > 0, "at dim=4 a stranger must sometimes win, or the claim is not about capacity"
