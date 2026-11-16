import importlib.util
import json
from pathlib import Path

import pytest
import sympy as sp

from cqse.core.evidence import CheckStatus
from cqse.ingest.pyq import IngestStatus, PYQRecord, ingest_record
from cqse.math.geometry3d import solve_and_verify

ROOT = Path(__file__).resolve().parents[1]
G = "geometry3d"


def _val(formal):
    r = solve_and_verify(formal)
    return r.value, r


def test_shortest_distance_two_methods():
    v, r = _val({"kind": G, "objects": {"L1": "line((7, 6, 2), (-3, 2, 4))", "L2": "line((5, 3, 4), (2, 1, 3))"},
                 "target": "sd(L1, L2)"})
    assert sp.simplify(v - 23 / sp.sqrt(38)) == 0
    st = {x.check_id: x.status for x in r.records}
    assert st["geometry3d.methods_agree"] == CheckStatus.EXACT_CHECKED
    assert st["geometry3d.numeric_crosscheck"] == CheckStatus.NUMERICALLY_CHECKED


def test_image_in_line_symmetric_form():
    v, _ = _val({"kind": G, "objects": {"L": {"symmetric": "(x-1)/2 = (y-2)/1 = (z-1)/3"},
                                         "Q": "image((4, 4, 3), L)"}, "target": "cx(Q) + cy(Q) + cz(Q)"})
    assert v == 9


def test_zero_denominator_in_symmetric_form():
    v, _ = _val({"kind": G, "objects": {"P": "(7, 10, 11)", "L1": {"symmetric": "(x-4)/1 = (y-4)/0 = (z-2)/3"},
                                         "Q": "meet(line(P, (2, 3, 6)), L1)"}, "target": "dist(P, Q)"})
    assert v == 14


def test_parallel_lines_fail_closed():
    v, r = _val({"kind": G, "objects": {"L1": "line((0, 0, 0), (1, 2, 3))", "L2": "line((1, 0, 0), (2, 4, 6))"},
                 "target": "sd2(L1, L2)"})
    assert v is None
    assert any(not x.is_affirmative() and x.hard for x in r.records)


def test_non_intersecting_lines_fail_closed():
    v, _ = _val({"kind": G, "objects": {"L1": "line((0, 0, 0), (1, 0, 0))", "L2": "line((0, 1, 1), (0, 1, 0))",
                                         "X": "meet(L1, L2)"}, "target": "cx(X)"})
    assert v is None


def test_two_admissible_values_fail_closed_without_selection():
    f = {"kind": G, "params": {"al": "real", "be": "real"},
         "objects": {"L1": {"symmetric": "(x-3)/3 = (y-al)/-1 = (z-3)/1"},
                     "L2": {"symmetric": "(x+3)/-3 = (y+7)/2 = (z-be)/4"}},
         "conditions": ["sd2(L1, L2) = 270"], "target": "5*al + be"}
    v, r = _val(f)
    assert v is None
    assert any(x.check_id == "geometry3d.target_determined" and x.status == CheckStatus.FAILED for x in r.records)
    v2, _ = _val({**f, "select": ["target > 0"]})
    assert v2 == 46
    v3, _ = _val({**f, "answer": "set"})
    assert v3 == sp.FiniteSet(46, -134)


def test_target_varying_over_continuum_fails():
    v, _ = _val({"kind": G, "params": {"t": "real"}, "objects": {"L": "line((0, 0, 0), (1, 1, 1))", "P": "at(L, t)"},
                 "target": "cx(P)"})
    assert v is None


def test_sum_of_all_values():
    v, _ = _val({"kind": G, "params": {"al": "real"},
                 "objects": {"L1": {"symmetric": "(x-1)/2 = (y-2)/3 = (z-3)/4"},
                             "L2": {"symmetric": "x/1 = y/al = (z-5)/1"}},
                 "conditions": ["sd2(L1, L2) = 25/6"], "target": "al", "answer": "sum"})
    assert v == -3


def test_which_requires_unique_candidate():
    base = {"kind": G, "objects": {"L": "line((0, 0, 0), (1, 1, 1))"},
            "target": {"which": "on(V, L)", "var": "V", "candidates": ["(2, 2, 2)", "(1, 2, 3)"]}}
    assert _val(base)[0] == 1
    two = {**base, "target": {**base["target"], "candidates": ["(2, 2, 2)", "(3, 3, 3)"]}}
    assert _val(two)[0] is None


def test_triangle_centres_and_conics():
    v, _ = _val({"kind": G, "params": {"a": "real", "b": "real"},
                 "objects": {"P": "(5, 4)", "Q": "(-2, 4)", "R": "(a, b)", "G": "centroid(P, Q, R)"},
                 "conditions": ["area2(P, Q, R) = 35^2", "orthocentre(P, Q, R) = (2, 14/5)"],
                 "target": "cx(G) + 2*cy(G)"})
    assert v == 3
    v, _ = _val({"kind": G, "params": {"A2": "positive", "B2": "positive"}, "objects": {"H": "hyperbola(A2, B2)"},
                 "conditions": ["focus(H, 1) = (sqrt(10), 0)", "directrix(H, 1) = 9/sqrt(10)"],
                 "target": "9*(ecc(H)^2 + latus_rectum(H))"})
    assert v == 16


def test_malformed_formal_fails_closed():
    v, r = _val({"kind": G, "objects": {"P": "(1, 2, 3)"}, "target": "foo(P)"})
    assert v is None and r.records[0].status == CheckStatus.UNRESOLVED


def _formals():
    spec = importlib.util.spec_from_file_location("maths_geometry", ROOT / "data/pyq/formals/maths_geometry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.FORMALS


def _record(ext):
    for line in (ROOT / "data/pyq/ascent_maths.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["pyq_id"] == f"ASCENT-{ext}":
            return rec
    raise KeyError(ext)


@pytest.mark.parametrize("ext,planted", [("m9fnuqsf", "A"), ("m9dr3ju6", "D")])
def test_planted_wrong_key_detected(ext, planted):
    entry = _formals()[ext]
    rec = _record(ext)
    rec = {**rec, "formal": entry["formal"],
           "options": [{**o, "value": entry["option_values"][o["id"]]} for o in rec["options"]]}
    ok = ingest_record(PYQRecord(**rec))
    assert IngestStatus.PARENT_VERIFIED in ok.statuses
    bad = ingest_record(PYQRecord(**{**rec, "answer_key": planted}))
    assert IngestStatus.QUARANTINED_KEY_DISAGREEMENT in bad.statuses
