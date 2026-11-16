"""Rigid-body engine: table + theorems vs direct integration. Expected values are hand-derived in comments."""
import pytest
import sympy as sp

from cqse.core.evidence import CheckStatus
from cqse.physics.rigid_body import SHAPES, compute_inertia, solve_and_verify
from cqse.verification.pipeline import software_blocking

SYM = lambda u: {"value": "symbolic", "unit": u}  # noqa: E731
M, R = sp.symbols("M R", positive=True)
DIMS = {"point": {}, "rod": {"L": "R"}, "ring": {"R": "R"}, "semi_ring": {"R": "R"}, "disc": {"R": "R"},
        "annular_disc": {"R1": "R/2", "R2": "R"}, "semi_disc": {"R": "R"},
        "solid_cylinder": {"R": "R", "L": "2*R"}, "hollow_cylinder": {"R": "R", "L": "2*R"},
        "thick_cylinder": {"R1": "R/2", "R2": "R", "L": "R"}, "solid_sphere": {"R": "R"},
        "spherical_shell": {"R": "R"}, "thick_spherical_shell": {"R1": "R/2", "R2": "R"},
        "solid_hemisphere": {"R": "R"}, "hemispherical_shell": {"R": "R"}, "rect_plate": {"a": "R", "b": "2*R"},
        "cuboid": {"a": "R", "b": "2*R", "c": "3*R"}, "cube": {"a": "R"}, "solid_cone": {"R": "R", "H": "2*R"}}


def _I(bodies, axis, extra_knowns=None):
    kn = {"M": SYM("kg"), "R": SYM("m"), **(extra_knowns or {})}
    vals, _, recs = compute_inertia({"knowns": kn, "bodies": bodies, "inertia": {"I": {"bodies": list(bodies),
                                                                                      "axis": axis}}})
    return vals["I"], recs[0]


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_table_and_integral_agree_on_oblique_axis(shape):
    # tilted body (normal (0,1,1)), off-centre, oblique axis: both methods must agree exactly
    body = {"b": {"shape": shape, "mass": "M", "dims": DIMS[shape], "center": ["R", "0", "R/3"],
                  "axis": [0, 1, 1], "u": [1, 0, 0]}}
    _, rec = _I(body, {"point": ["0", "R", "0"], "dir": [1, 2, 2]})
    assert rec.status == CheckStatus.EXACT_CHECKED, rec.result


@pytest.mark.parametrize("shape,dims,axis_dir,expected", [
    ("ring", {"R": "R"}, [0, 0, 1], M * R**2),
    ("ring", {"R": "R"}, [1, 0, 0], M * R**2 / 2),                 # perpendicular-axis theorem
    ("disc", {"R": "R"}, [0, 0, 1], M * R**2 / 2),
    ("disc", {"R": "R"}, [0, 1, 0], M * R**2 / 4),
    ("solid_sphere", {"R": "R"}, [0, 0, 1], sp.Rational(2, 5) * M * R**2),
    ("spherical_shell", {"R": "R"}, [1, 1, 0], sp.Rational(2, 3) * M * R**2),
    ("rod", {"L": "R"}, [0, 0, 1], M * R**2 / 12),
    ("rect_plate", {"a": "R", "b": "R"}, [0, 0, 1], M * R**2 / 6),
    ("solid_cone", {"R": "R", "H": "R"}, [0, 0, 1], sp.Rational(3, 10) * M * R**2),
    ("semi_disc", {"R": "R"}, [0, 0, 1], M * R**2 / 2),             # about the full circle's centre
])
def test_standard_values(shape, dims, axis_dir, expected):
    I, rec = _I({"b": {"shape": shape, "mass": "M", "dims": dims}}, {"dir": axis_dir})
    assert rec.status == CheckStatus.EXACT_CHECKED
    assert sp.simplify(I - expected) == 0


def test_parallel_axis_disc_edge_and_rod_end():
    # disc about a normal axis through the rim: MR^2/2 + MR^2 = 3/2 MR^2
    I, _ = _I({"d": {"shape": "disc", "mass": "M", "dims": {"R": "R"}}}, {"point": ["R", "0", "0"], "dir": [0, 0, 1]})
    assert sp.simplify(I - sp.Rational(3, 2) * M * R**2) == 0
    # rod of length R about an end: MR^2/3
    I, _ = _I({"r": {"shape": "rod", "mass": "M", "dims": {"L": "R"}}}, {"point": ["R/2", "0", "0"], "dir": [0, 0, 1]})
    assert sp.simplify(I - M * R**2 / 3) == 0
    # square plate about a normal axis through a corner: Ma^2/6 + M a^2/2 = 2/3 M a^2
    I, _ = _I({"p": {"shape": "rect_plate", "mass": "M", "dims": {"a": "R", "b": "R"}}},
              {"point": ["R/2", "R/2", "0"], "dir": [0, 0, 1]})
    assert sp.simplify(I - sp.Rational(2, 3) * M * R**2) == 0


def test_removed_disc():
    # disc (M, R) with a hole of radius R/2 centred at R/2; hole mass M/4.
    # about the centre normal: MR^2/2 - [ (M/4)(R/2)^2/2 + (M/4)(R/2)^2 ] = MR^2/2 - 3MR^2/32 = 13/32 MR^2
    bodies = {"d": {"shape": "disc", "mass": "M", "dims": {"R": "R"}},
              "h": {"shape": "disc", "density": "M/(pi*R**2)", "dims": {"R": "R/2"}, "center": ["R/2", "0", "0"],
                    "sign": -1}}
    I, rec = _I(bodies, {"dir": [0, 0, 1]})
    assert rec.status == CheckStatus.EXACT_CHECKED
    assert sp.simplify(I - sp.Rational(13, 32) * M * R**2) == 0


def test_variable_density_disc_and_rod():
    # sigma = k r^2: I = M * (int r^5)/(int r^3) = M * (R^6/6)/(R^4/4) = 2/3 M R^2
    I, rec = _I({"d": {"shape": "disc", "mass": "M", "dims": {"R": "R"}, "density_profile": "r_**2"}}, {"dir": [0, 0, 1]})
    assert rec.status == CheckStatus.EXACT_CHECKED and sp.simplify(I - sp.Rational(2, 3) * M * R**2) == 0
    # rod length R, lambda ∝ (1 + x/R), x from end A, axis through A: (7/18) M R^2
    I, rec = _I({"r": {"shape": "rod", "mass": "M", "dims": {"L": "R"}, "density_profile": "1 + (s_ + R/2)/R"}},
                {"point": ["-R/2", "0", "0"], "dir": [0, 0, 1]})
    assert rec.status == CheckStatus.EXACT_CHECKED and sp.simplify(I - sp.Rational(7, 18) * M * R**2) == 0


def test_bridge_rolling_and_ratio():
    # solid sphere rolling down 30 deg, g = 10: a = g sin(th)/(1 + 2/5) = 5/(7/5) = 25/7
    f = {"knowns": {"M": SYM("kg"), "R": SYM("m"), "g": {"value": "10", "unit": "m/s^2"},
                    "th": {"value": "30", "unit": "degree"}},
         "bodies": {"s": {"shape": "solid_sphere", "mass": "M", "dims": {"R": "R"}}},
         "inertia": {"I": {"bodies": ["s"], "axis": {"dir": [0, 0, 1]}}},
         "relations": [{"template": "rolling_incline", "a": "a", "M": "M", "I": "I", "R": "R", "g": "g", "th": "th"}],
         "unknowns": {"a": {"unit": "m/s^2"}}, "target": "a"}
    r = solve_and_verify(f)
    assert r.value == sp.Rational(25, 7) and not software_blocking(r.records)


def test_numeric_knowns_and_radius_of_gyration():
    # rod 10*sqrt(3) m about the centre: k^2 = L^2/12 = 300/12 = 25 -> k = 5 m (mass cancels)
    f = {"knowns": {"m": SYM("kg"), "L": {"value": "10*sqrt(3)", "unit": "m"}},
         "bodies": {"r": {"shape": "rod", "mass": "m", "dims": {"L": "L"}}},
         "inertia": {"I": {"bodies": ["r"], "axis": {"dir": [0, 0, 1]}}}, "masses": {"Mt": ["r"]},
         "unknowns": {"k": {"unit": "m", "domain": "positive"}}, "equations": ["I = Mt*k**2"], "target": "k"}
    r = solve_and_verify(f)
    assert r.value == 5 and not software_blocking(r.records)


def test_fail_closed_unknown_body():
    r = solve_and_verify({"knowns": {"M": SYM("kg"), "R": SYM("m")},
                          "bodies": {"b": {"shape": "torus", "mass": "M", "dims": {"R": "R"}}},
                          "inertia": {"I": {"bodies": ["b"], "axis": {"dir": [0, 0, 1]}}}})
    assert r.value is None and software_blocking(r.records)


def test_fail_closed_on_disagreement(monkeypatch):
    import cqse.physics.rigid_body as rb
    real = rb._table

    def wrong(shape, Mm, d):  # planted error: ring tabulated as MR^2/2
        diag, off = real(shape, Mm, d)
        return (tuple(x / 2 for x in diag), off) if shape == "ring" else (diag, off)
    monkeypatch.setattr(rb, "_table", wrong)
    r = solve_and_verify({"knowns": {"M": SYM("kg"), "R": SYM("m")},
                          "bodies": {"b": {"shape": "ring", "mass": "M", "dims": {"R": "R"}}},
                          "inertia": {"I": {"bodies": ["b"], "axis": {"dir": [0, 0, 1]}}}})
    assert r.value is None
    assert any(x.status == CheckStatus.FAILED and x.check_id == "rigid.inertia.I" for x in r.records)


def test_fail_closed_bad_geometry():
    r = solve_and_verify({"knowns": {"M": SYM("kg"), "R": SYM("m")},
                          "bodies": {"b": {"shape": "disc", "mass": "M", "dims": {"R": "R"}, "axis": [0, 0, 1],
                                           "u": [0, 0, 1]}},
                          "inertia": {"I": {"bodies": ["b"], "axis": {"dir": [0, 0, 1]}}}})
    assert r.value is None and software_blocking(r.records)


def test_formal_names_r_and_s_do_not_collide_with_integration_variables():
    """Regression: a sphere of radius r centred at L + r used to make table and integral disagree."""
    from cqse.core.problem import Subject
    from cqse.physics.rigid_body import solve_and_verify
    K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
    f = {"kind": "rigid_body",
         "knowns": {"M": K("2", "kg"), "r": K("1/10", "m"), "L": K("1", "m")},
         "bodies": {"b": {"shape": "solid_sphere", "dims": {"R": "r"}, "center": ["L + r", "0", "0"],
                          "axis": ["0", "0", "1"], "mass": "M"}},
         "inertia": {"I": {"bodies": ["b"], "axis": {"point": ["0", "0", "0"], "dir": ["0", "0", "1"]}}},
         "unknowns": {"x": {"unit": "kg*m^2", "domain": "positive"}},
         "equations": ["x = I"], "target": "x"}
    res = solve_and_verify(f, Subject.PHYSICS)
    import sympy as sp
    assert res.value is not None and sp.nsimplify(res.value) == sp.Rational(2, 5) * 2 * sp.Rational(1, 100) + 2 * sp.Rational(121, 100)
