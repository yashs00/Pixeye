import pytest

from cqse.core.problem import Subject
from cqse.verification.pipeline import build_item

PROFILE = "JEE_MAIN-2027-v1"

GOOD_FORMALS = {
    "math_domain": (Subject.MATHEMATICS, dict(kind="equation", lhs="x**2-x-6", rhs="0", var="x",
                                              domain="positive_reals", target="sum")),
    "math_trap": (Subject.MATHEMATICS, dict(kind="equation", lhs="(x**2-x-6)/(x+2)", rhs="0", var="x",
                                            domain="reals", target="sum")),
    "proj_range": (Subject.PHYSICS, dict(kind="projectile_level", u="20", theta_deg="30", g="10", target="range")),
    "incline_static": (Subject.PHYSICS, dict(kind="incline_friction", m="2", theta_deg="30", mu_s="0.7",
                                             mu_k="0.5", g="10", target="friction_force")),
    "stoich": (Subject.CHEMISTRY, dict(kind="stoichiometry", reaction="2 H2 + O2 -> 2 H2O",
                                       given={"H2": {"mass_g": "4"}, "O2": {"mass_g": "48"}},
                                       atomic_masses={"H": "1", "O": "16"},
                                       target={"species": "H2O", "quantity": "mass_g"})),
}


@pytest.fixture(params=list(GOOD_FORMALS))
def good_item(request):
    subj, formal = GOOD_FORMALS[request.param]
    return build_item(f"T-{request.param}", subj, formal, PROFILE)
