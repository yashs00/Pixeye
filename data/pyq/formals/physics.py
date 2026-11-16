"""Formalizations of the 100 ASCENT physics questions (data/pyq/ascent_phy.jsonl).

Every entry models the STEM (never the key or the database explanation). Option values come from the
option TEXT, in the unit / encoding of the formal's target. Encodings used for non-scalar answers:

* dimensionless ratio  - symbolic knowns, target k with  X = k * (reference expression)   (symbolic options)
* irrational basis     - a vector / pair (x, y, z) of RATIONAL components is encoded as  x + sqrt(2) y + sqrt(3) z
                          (1, sqrt2, sqrt3, sqrt5 are linearly independent over Q, so the code is injective)
* option claims        - statement_set / select_combination with one statement per OPTION (labels A..D), each
                          statement's truth computed by a sub-formal (e.g. an equilibrium residual == 0); the
                          derived code {i} is compared with option values "{1}".."{4}".

Questions whose needed geometry / circuit / graph exists only in an image are NOT formalized (see OMITTED).
"""

K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
S = lambda u="": {"value": "symbolic", "unit": u}  # noqa: E731
U = lambda u="", d="real": {"unit": u, "domain": d}  # noqa: E731
MU0 = K("4*pi*10**-7", "T*m/A")
OPT_SETS = {"A": "{1}", "B": "{2}", "C": "{3}", "D": "{4}"}


def ES(knowns, unknowns, equations, target, model, **extra):
    return {"kind": "equation_system", "knowns": knowns, "unknowns": unknowns, "equations": equations,
            "target": target, "model": model, **extra}


def COMP(formal, claim):
    return {"formal": formal, "claim": claim, "subject": "PHYSICS"}


def CUR(truth, note):
    return {"truth": truth, "basis": "curated", "note": note}


def SEL(statements):
    return {"kind": "statement_set", "format": "select_combination", "statements": statements}


def AR(a, r, explains=None):
    f = {"kind": "statement_set", "format": "assertion_reason", "statements": {"A": a, "R": r}}
    if explains is not None:
        f["explains"] = explains
    return f


FORMALS = {}

# ------------------------------------------------------------------ Rotational motion
FORMALS["m6srn52d"] = {
    "formal": ES({"g": S("m/s^2"), "L": S("m"), "t1": K("30", "degree"), "t2": K("45", "degree")},
                 {"v1s": U("m^2/s^2", "positive"), "v2s": U("m^2/s^2", "positive"), "x": U("", "positive")},
                 ["7*v1s = 10*g*L*sin(t1)", "7*v2s = 10*g*L*sin(t2)", "x*v2s = v1s"], "x",
                 ["rolling solid sphere from rest: m g L sin(theta) = (1/2) m v^2 (1 + 2/5)",
                  "x = v1^2 / v2^2"]),
    "option_values": {"A": "1/3", "B": "1/2", "C": "1/sqrt(2)", "D": "1/sqrt(3)"},
    "note": "v^2 = (10/7) g L sin(theta); ratio sin30/sin45 = 1/sqrt2."}

FORMALS["m6w9nzw8"] = {
    "formal": ES({"M": S("kg"), "R2": S("m")}, {"R1": U("m", "positive"), "n": U("", "positive")},
                 ["M*R1**2/4 = (5/2)*(M*R2**2/2)", "(2/5)*M*R1**2 = n*(M*R2**2/2)"], "n",
                 ["disc about diameter M R1^2/4; ring about diameter M R2^2/2; sphere radius R1: 2/5 M R1^2",
                  "equal masses"]),
    "explanation_value": "4", "note": "R1^2 = 5 R2^2 -> n = 4."}

FORMALS["m9ghxmzt"] = {
    "formal": ES({"kr": K("1"), "ks": K("2/5")}, {"x": U("", "positive")},
                 ["x/5 = (1 + ks)/(1 + kr)"], "x",
                 ["v^2 = 2gh/(1+k^2/R^2); ratio v_ring/v_sphere = sqrt(x/5)"]),
    "explanation_value": "4",
    "note": "exact x = 7/2 = 3.5; no rounding instruction in the stem -> nearest-integer rounding is ambiguous."}

FORMALS["m6rkxfo3"] = {
    "formal": ES({"B": S("T"), "v": S("m/s"), "c": S(""), "t1": S("s")},
                 {"E1": U("V", "positive"), "E2": U("V", "positive"), "n": U("")},
                 ["E1 = B*v*(c*v*t1)", "E2 = B*v*(c*v*(2*t1))", "E2 = 2**n*E1"], "n",
                 ["rails are straight lines meeting at the vertex (stem: 'starts from the vertex'), so the "
                  "length of bar between the rails is l = c x with c a geometry constant", "x = v t, E = B l v",
                  "power-law exponent from E(2t)/E(t) = 2^n"]),
    "explanation_value": "1",
    "note": "figure only fixes the angle c, which cancels; straight rails assumed from 'vertex' (teacher confirm)."}

FORMALS["m9ghxmfx"] = {
    "formal": SEL({
        "A": CUR(False, "r x L is not torque (dimensionally kg m^3/s); torque = dL/dt"),
        "B": CUR(True, "d/dt (r x p) = dL/dt = torque"),
        "C": CUR(True, "r x dp/dt = r x F (since v x p = 0)"),
        "D": CUR(True, "I alpha for rotation about a fixed axis / principal axis"),
        "E": CUR(True, "definition r x F")}),
    "note": "B, C, D, E correct."}

FORMALS["m9e5j2f6"] = {
    "formal": ES({"M": S("kg"), "r": S("m")},
                 {"R": U("m", "positive"), "I": U("kg*m^2", "positive"), "k": U("", "positive")},
                 ["2*R = r", "I = M*R**2/2 + M*R**2", "I = k*M*r**2"], "k",
                 ["ring radius R = r/2 (r is the DIAMETER)", "in-plane diameter axis M R^2/2, parallel axis to "
                  "the tangent in the plane: + M R^2"]),
    "option_values": {"A": "3/8", "B": "2", "C": "1/2", "D": "3/2"},
    "note": "target k with I = k M r^2."}

FORMALS["m9e5j3wx"] = {
    "formal": ES({"F": K("10", "N"), "R": K("0.2", "m"), "al": K("2", "1/s^2")},
                 {"I": U("kg*m^2", "positive")}, ["F*R = I*al"], "I",
                 ["string tension 10 N acts tangentially at the rim (stated in the stem)", "tau = I alpha",
                  "g is not needed"]),
    "explanation_value": "1", "note": "all data are in the text; the figure only shows the string."}

FORMALS["m9dnmwcl"] = {
    "formal": ES({"lam": S("kg/m"), "L": S("m")},
                 {"M": U("kg", "positive"), "R": U("m", "positive"), "I": U("kg*m^2", "positive"),
                  "k": U("", "positive")},
                 ["M = lam*L", "L = 2*pi*R", "I = M*R**2/2", "I = k*lam*L**3"], "k",
                 ["ring about a diameter: M R^2 / 2"]),
    "option_values": {"A": "1/(8*pi**2)", "B": "1/(16*pi**2)", "C": "1/(4*pi**2)", "D": "1/12"},
    "note": "target k with I = k lambda L^3."}

FORMALS["m6v426tx"] = {
    "formal": ES({"m": S("kg"), "R": S("m"), "v": S("m/s")},
                 {"w": U("1/s", "positive"), "I": U("kg*m^2", "positive"), "x": U("", "positive")},
                 ["v = w*R", "I = (2/5)*m*R**2", "x*(I*w**2/2) = m*v**2/2"], "x",
                 ["rolling without slipping v = w R", "solid sphere I = 2/5 m R^2"]),
    "option_values": {"A": "3/4", "B": "4/3", "C": "5/2", "D": "2/5"}, "note": ""}

FORMALS["m9dunp8m"] = {
    "formal": ES({"M": S("kg"), "L": S("m")},
                 {"al": U("kg*m^2", "positive"), "I": U("kg*m^2", "positive"), "k": U("", "positive")},
                 ["al = M*L**2/12", "I = 2*((M/2)*(L/2)**2/12)", "I = k*al"], "k",
                 ["each half (M/2, L/2) rotates about its own centre (cross joined at the midpoints)"]),
    "option_values": {"A": "1/4", "B": "1/8", "C": "1", "D": "1/2"}, "note": "target k with I = k alpha."}

FORMALS["m6w9ob6b"] = {
    "formal": ES({"s": S("kg/m^2"), "R1": S("m")},
                 {"R2": U("m", "positive"), "M1": U("kg", "positive"), "M2": U("kg", "positive"),
                  "I1": U("kg*m^2", "positive"), "I2": U("kg*m^2", "positive"), "x": U("", "positive")},
                 ["R2 = 2*R1", "M1 = s*pi*R1**2", "M2 = s*pi*R2**2", "I1 = M1*R1**2/2", "I2 = M2*R2**2/2",
                  "x*I1 = I2"], "x",
                 ["same material (iron) and same (negligible) thickness -> same mass per area s",
                  "axis: central, perpendicular (ratio is the same for any corresponding axis)"]),
    "explanation_value": "16", "note": "equal thickness assumed (implied by 'negligible thickness', same iron)."}

FORMALS["m6v42h24"] = {
    "formal": SEL({lab: COMP(ES({"g": S("m/s^2"), "s": S(""), "L": S("m")},
                                {"a1": U("m/s^2", "positive"), "a2": U("m/s^2", "positive"),
                                 "t1": U("s", "positive"), "t2": U("s", "positive"), "q": U("", "positive")},
                                ["a1 = (5/7)*g*s", "a2 = (3/5)*g*s", "L = a1*t1**2/2", "L = a2*t2**2/2",
                                 "q*t2 = t1"], "q",
                                ["rolling without slipping: a = g sin(theta)/(1 + k^2/R^2)", "s = sin(theta)",
                                 "same incline length L, from rest"]), c)
                   for lab, c in {"A": "< 1", "B": "== 2", "C": "> 1", "D": "== 1"}.items()}),
    "option_values": OPT_SETS,
    "note": "option claims on q = t1/t2 = sqrt(21)/5: A t1<t2, B t1=2t2, C t1>t2, D t1=t2."}

FORMALS["m9gxgdp9"] = {
    "formal": ES({"m": K("1", "kg"), "vi": K("10", "m/s"), "k": K("10", "N/m"), "x1": K("0.1", "m"),
                  "x2": K("1.9", "m")}, {"v": U("m/s", "positive")},
                 ["m*v**2 = m*vi**2 - k*(x2**2 - x1**2)"], "v",
                 ["work-energy; 'kr' in the stem read as k x"]),
    "option_values": {"A": "4", "B": "10", "C": "8", "D": "6"}, "note": "reused from verify_ascent300_calcs."}

FORMALS["m6rja0g8"] = {
    "formal": ES({"M": K("250", "g"), "m1": K("400", "g")}, {"m": U("g", "positive")},
                 ["m1*30 = M*10 + m*50"], "m", ["torques about the 40 cm pivot; rod weight at 50 cm"]),
    "option_values": {"A": "290", "B": "200", "C": "190", "D": "300"}, "note": "reused."}

FORMALS["m9do8yt4"] = {
    "formal": ES({"m": K("1", "kg"), "w1": K("1800*2*pi/60", "1/s"), "w2": K("2100*2*pi/60", "1/s"),
                  "tau": K("25*pi", "N*m"), "t": K("40", "s")},
                 {"I": U("kg*m^2", "positive"), "R": U("m", "positive"), "D": U("m", "positive")},
                 ["I = m*R**2/4", "tau*t = I*(w2 - w1)", "D = 2*R"], "D",
                 ["thin disc about a diameter I = m R^2/4", "angular impulse = change of angular momentum",
                  "rpm converted exactly: 1 rpm = 2 pi/60 rad/s"]),
    "explanation_value": "40", "note": ""}

FORMALS["m6t9xvoz"] = {
    "formal": ES({"M": S("kg"), "R": S("m"), "c2": K("5", "1/s^2"), "c1": K("-8", "1/s"), "t": K("2", "s"),
                  "u": K("1", "1/s^3")},
                 {"w": U("1/s"), "al": U("1/s^2"), "I": U("kg*m^2", "positive"), "tau": U("N*m"),
                  "P": U("W"), "k": U("")},
                 ["w = 2*c2*t + c1", "al = 2*c2", "I = M*R**2/2", "tau = I*al", "P = tau*w", "P = k*M*R**2*u"],
                 "k",
                 ["theta = c2 t^2 + c1 t -> omega = 2 c2 t + c1, alpha = 2 c2", "disc about its central "
                  "perpendicular axis I = M R^2/2", "P = tau omega; M, R numerically in kg, m"]),
    "option_values": {"A": "60", "B": "72", "C": "8", "D": "108"}, "note": "target k with P = k M R^2 (SI)."}

FORMALS["m6ulvpn1"] = {
    "formal": ES({"g": S("m/s^2"), "th": K("45", "degree")}, {"a": U("m/s^2", "positive"), "k": U("", "positive")},
                 ["a*(1 + 1/2) = g*sin(th)", "a = k*g"], "k",
                 ["solid cylinder rolling without slipping: a = g sin(theta)/(1 + 1/2)"]),
    "option_values": {"A": "sqrt(2)", "B": "1/sqrt(2)", "C": "1/(3*sqrt(2))", "D": "sqrt(2)/3"}, "note": ""}

FORMALS["m6rp5u2s"] = {
    "formal": ES({"rx": K("1"), "ry": K("1"), "rz": K("1"), "Fx": K("2"), "Fy": K("1"), "Fz": K("2")},
                 {"tx": U(), "ty": U(), "tz": U(), "z": U()},
                 ["tx = ry*Fz - rz*Fy", "ty = rz*Fx - rx*Fz", "tz = rx*Fy - ry*Fx",
                  "z = tx + sqrt(2)*ty + sqrt(3)*tz"], "z",
                 ["tau = r x F", "vector encoded as tx + sqrt2 ty + sqrt3 tz (injective on rational vectors)"]),
    "option_values": {"A": "sqrt(2) + sqrt(3)", "B": "1 - sqrt(3)", "C": "1 - sqrt(2) + sqrt(3)", "D": "1 + sqrt(3)"},
    "note": "tau = (1, 0, -1)."}

_VV_KN = {"m": S("kg"), "a": S("m"), "w": S("1/s"), "ph": K("30", "degree")}
_FX, _FY = "(-m*a*w**2*cos(ph))", "(-m*a*w**2*sin(ph))"
_PX, _PY = "(-m*a*w*sin(ph))", "(m*a*w*cos(ph))"
_LZ = "(m*a**2*w*(cos(ph)**2 + sin(ph)**2))"


def _vv(xx, xy, xunit, dot_zero=False):
    eqs = [f"Fm**2 = {_FX}**2 + {_FY}**2", f"Xm**2 = ({xx})**2 + ({xy})**2",
           "c*Fm*Xm = 0" if dot_zero else f"c*Fm*Xm = {_FX}*({xx}) + {_FY}*({xy})"]
    return ES(_VV_KN, {"c": U(""), "Fm": U("N", "positive"), "Xm": U(xunit, "positive")}, eqs, "c",
              ["r = a(cos wt, sin wt); p = m dr/dt; F = m d2r/dt2; L = r x p (along z)",
               "c = cosine of the angle between F and the listed vector; 'opposite' means c = -1",
               "evaluated at the instant wt = 30 deg (the angle is time independent)"])


FORMALS["m9ghxmvv"] = {
    "formal": SEL({
        "A": COMP(ES(_VV_KN, {"c": U(""), "Fm": U("N", "positive"), "Xm": U("kg*m^2/s", "positive")},
                     [f"Fm**2 = {_FX}**2 + {_FY}**2", f"Xm**2 = {_LZ}**2", "c*Fm*Xm = 0"], "c",
                     ["L = r x p is along z; F lies in the xy plane (F.L = 0)",
                      "c = cosine of the angle between F and L; 'opposite' means c = -1"]), "== -1"),
        "B": COMP(_vv(f"(-{_LZ}*{_PY})", f"({_LZ}*{_PX})", "kg^2*m^3/s^2"), "== -1"),
        "C": COMP(_vv("a*cos(ph)", "a*sin(ph)", "m"), "== -1"),
        "D": COMP(_vv(_PX, _PY, "kg*m/s"), "== -1")}),
    "option_values": OPT_SETS,
    "note": "L x P = (-Lz Py, Lz Px, 0) is parallel to F; only 'opposite to r' holds."}

FORMALS["m9fnutuj"] = {
    "formal": ES({"M1": S("kg"), "R1": S("m"), "w1": S("1/s")},
                 {"R2": U("m", "positive"), "M2": U("kg", "positive"), "w2": U("1/s", "positive"),
                  "x": U("", "positive")},
                 ["2*R2 = R1", "M2*R1**3 = M1*R2**3", "(2/5)*M1*R1**2*w1 = (2/5)*M2*R2**2*w2", "w2 = x*w1"], "x",
                 ["uniform density, shape unchanged: M proportional to R^3",
                  "angular momentum I omega of the sphere conserved (JEE convention; lost mass assumed to carry "
                  "no angular momentum)"]),
    "explanation_value": "32", "note": "physically debatable conservation assumption flagged in model."}

FORMALS["m9fnuree"] = {
    "formal": ES({"F": K("49", "N"), "m": K("20", "kg")}, {"a": U("m/s^2", "positive")},
                 ["a*(7*m/5) = 2*F"], "a",
                 ["force tangential at the top (stated); torque about contact: F*2R = (7/5) m R^2 alpha, a = R alpha"]),
    "option_values": {"A": "2.5", "B": "3.5", "C": "0.25", "D": "0.35"}, "note": "reused."}

FORMALS["m9dunojt"] = {
    "formal": ES({"M": K("10", "kg"), "R": K("10", "cm"), "F": K("20", "N"), "s": K("1", "m")},
                 {"I": U("kg*m^2", "positive"), "w": U("1/s", "positive")},
                 ["I = M*R**2", "F*s = I*w**2/2"], "w",
                 ["spokes negligible -> wheel is a ring I = M R^2", "work F s = rotational KE (frictionless)"]),
    "option_values": {"A": "20", "B": "30", "C": "10", "D": "0"}, "note": "all data in the text."}

FORMALS["m6qvblt7"] = {
    "formal": ES({"a1": K("1", "m/s^2"), "a3": K("2", "m/s"), "b1": K("2", "m/s"), "b2": K("-1", "m/s^2"),
                  "u2": K("3", "m/s"), "u3": K("4", "m/s"), "t": K("1", "s"), "m": K("1", "kg"),
                  "uL": K("1", "kg*m^2/s")},
                 {"n": U(""), "p": U(""), "rx": U("m"), "ry": U("m"), "rz": U("m"), "Lx": U("kg*m^2/s"),
                  "Ly": U("kg*m^2/s"), "Lz": U("kg*m^2/s"), "x": U("", "positive")},
                 ["(2*a1*t)**2 + (u2*n)**2 + a3**2 = b1**2 + (2*b2*t)**2 + (u3*p)**2",
                  "(2*a1*t)*b1 + (u2*n)*(2*b2*t) + a3*(u3*p) = 0",
                  "rx = a1*t**2 - b1*t", "ry = u2*n*t - b2*t**2", "rz = a3*t - u3*p*t",
                  "Lx = m*(ry*a3 - rz*u2*n)", "Ly = m*(rz*2*a1*t - rx*a3)", "Lz = m*(rx*u2*n - ry*2*a1*t)",
                  "x*uL**2 = Lx**2 + Ly**2 + Lz**2"], "x",
                 ["r_A = (a1 t^2, 3n t, a3 t), r_B = (b1 t, b2 t^2, 4p t) ('beta1 t-hat' read as beta1 t)",
                  "v_A = (2 a1 t, 3n, a3), v_B = (b1, 2 b2 t, 4p); |v_A| = |v_B| and v_A . v_B = 0 at t = 1 s",
                  "L = (r_A - r_B) x m v_A; |L| = sqrt(x)"]),
    "explanation_value": "90", "note": "n = 1/3, p = -1/4, L = (1, 8, -5)."}

FORMALS["m6qn64qy"] = {
    "formal": ES({"rx": K("1", "m"), "ry": K("1", "m"), "Fx": K("1", "N"), "Fy": K("-1", "N")},
                 {"tz": U("N*m"), "x": U("N*m", "positive")}, ["tz = rx*Fy - ry*Fx", "x**2 = tz**2"], "x",
                 ["tau = r x F; z component; F taken in N"]),
    "explanation_value": "2", "note": ""}

FORMALS["m6rju9w4"] = {
    "formal": ES({"M": S("kg"), "g": S("m/s^2"), "r1": K("1/10"), "r2": K("1/5"), "r3": K("1/2")},
                 {"F1": U("N"), "F2": U("N"), "F3": U("N"), "x1": U("kg", "positive"), "x2": U("kg", "positive"),
                  "x3": U("kg", "positive"), "al": U(""), "be": U(""), "z": U("")},
                 ["F1 - M*g = M*r1*g", "F1 - (M - x1)*g = 3*(M - x1)*r1*g",
                  "F2 - M*g = M*r2*g", "F2 - (M - x2)*g = 3*(M - x2)*r2*g",
                  "F3 - M*g = M*r3*g", "F3 - (M - x3)*g = 3*(M - x3)*r3*g",
                  "M*r1*g = x1*(al*r1*g + be*g)", "M*r2*g = x2*(al*r2*g + be*g)", "M*r3*g = x3*(al*r3*g + be*g)",
                  "z = al + sqrt(2)*be"], "z",
                 ["buoyant force F unchanged when mass x is released: F - Mg = Ma, F - (M-x)g = (M-x)3a",
                  "solved at three instances a = r g (r = 1/10, 1/5, 1/2); the answer is written as "
                  "x = M a/(al a + be g) and (al, be) are fitted exactly (2 instances fix them, the 3rd checks "
                  "the form); encoding z = al + sqrt2 be"]),
    "option_values": {"A": "2/3 + sqrt(2)/3", "B": "3/2 + sqrt(2)/2", "C": "2/3 - sqrt(2)/3",
                      "D": "3/2 - sqrt(2)/2"},
    "note": "options x = M a/(al a + be g): A (2/3,1/3), B (3/2,1/2), C (2/3,-1/3), D (3/2,-1/2)."}

FORMALS["m9ejm6t2"] = {
    "formal": ES({"m": K("500", "g"), "c": K("4", "m^(1/2)/s")},
                 {"a": U("m/s^2", "positive"), "F": U("N", "positive")},
                 ["a = c**2/2", "F = m*a"], "F",
                 ["v = c sqrt(x) -> a = v dv/dx = c^2/2 (constant)", "F = m a"]),
    "option_values": {"A": "8", "B": "4", "C": "5", "D": "6"}, "note": ""}

FORMALS["m9e5j8ub"] = {
    "formal": ES({"g": S("m/s^2"), "th": K("60", "degree")}, {"mu": U("", "positive")},
                 ["g*sin(th) - mu*g*cos(th) = g/2"], "mu", ["block sliding down: a = g sin - mu g cos"]),
    "option_values": {"A": "sqrt(3)/2", "B": "sqrt(2)/3", "C": "1 - sqrt(3)/2", "D": "sqrt(3) - 1"}, "note": ""}


def _ghxmo3(t1, t2, c):
    return COMP(ES({"m": S("kg"), "g": S("m/s^2"), "t1": K(t1, "degree"), "t2": K(t2, "degree"), "c": K(c)},
                   {"T2": U("N", "positive"), "T1": U("N", "positive"), "z": U("")},
                   ["T2 = c*m*g", "T1 = sqrt(3)*T2",
                    "z*(m*g)**2 = (T1*cos(t1) - T2*cos(t2))**2 + (T1*sin(t1) + T2*sin(t2) - m*g)**2"], "z",
                   ["strings at angles t1, t2 to the horizontal ceiling, on opposite sides of the body",
                    "z = squared equilibrium residual / (mg)^2 for the option's (t1, t2, T2) with T1 = sqrt3 T2"]),
                "== 0")


FORMALS["m9ghxmo3"] = {
    "formal": SEL({"A": _ghxmo3("30", "60", "3/4"), "B": _ghxmo3("45", "45", "3/4"),
                   "C": _ghxmo3("30", "60", "4/5"), "D": _ghxmo3("60", "30", "1/2")}),
    "option_values": OPT_SETS,
    "note": "the stem alone is underdetermined; each option is checked for equilibrium (residual == 0)."}

# ------------------------------------------------------------------ EMI
FORMALS["m6rjhb8t"] = {
    "formal": ES({"B": K("0.4", "T"), "R": K("20", "cm"), "w": K("10*3.14", "1/s")}, {"V": U("V", "positive")},
                 ["V = B*w*R**2/2"], "V", ["rotating disc emf B omega R^2/2", "pi = 3.14 as instructed"]),
    "option_values": {"A": "0.5024", "B": "0.0628", "C": "0.2512", "D": "0.1256"}, "note": ""}

FORMALS["m6srn3xq"] = {
    "formal": SEL({
        "A": CUR(True, "L depends on geometry (turns, area, length)"),
        "B": CUR(False, "L = mu N^2 A/l depends on permeability"),
        "C": CUR(True, "Lenz: self-induced emf opposes change of current"),
        "D": CUR(True, "inductance is the analogue of mass (inertia)"),
        "E": CUR(True, "work against back emf is stored as LI^2/2")}),
    "note": "A, C, D, E."}

FORMALS["m6qkgtpo"] = {
    "formal": ES({"N": S(""), "A": S("m^2"), "B": S("T"), "w": S("1/s"), "th": K("90", "degree")},
                 {"phi": U("Wb"), "e": U("V"), "k1": U(""), "k2": U(""), "z": U("")},
                 ["phi = A*B*cos(th)", "e = N*A*B*w*sin(th)", "phi = k1*A*B", "e = k2*N*A*B*w",
                  "z = k1 + sqrt(2)*k2"], "z",
                 ["th = angle between B and the coil's area vector = 90 deg when B is parallel to the plane",
                  "phi per turn = A B cos(th); emf = N A B w sin(th)",
                  "pair (phi/AB, emf/NABw) encoded as k1 + sqrt2 k2"]),
    "option_values": {"A": "1 + sqrt(2)", "B": "1", "C": "0", "D": "sqrt(2)"},
    "note": "option A's second 'phi' read as emf (typo)."}

FORMALS["m6qkyxgd"] = {
    "formal": ES({"L1": K("2", "H"), "M": K("3", "H"), "r1": K("5", "A/s"), "r2": K("7", "A/s")},
                 {"e": U("V")}, ["e = -(L1*r1 + M*r2)"], "e",
                 ["flux through coil 1: phi1 = L1 I1 + M12 I2; e1 = -d(phi1)/dt",
                  "evaluated at the sample L1 = 2 H, M12 = 3 H, dI1/dt = 5 A/s, dI2/dt = 7 A/s"]),
    "option_values": {"A": "-29", "B": "11", "C": "-25", "D": "-31"},
    "note": "symbolic options compared at a generic sample point (wrong options are disproved; the match is "
            "an instance, the identity follows from phi1 = L1 I1 + M12 I2)."}

# ------------------------------------------------------------------ Laws of motion
FORMALS["m9do23fv"] = {
    "formal": ES({"m": K("2", "kg"), "vx": K("3", "m/s"), "vy": K("4", "m/s"), "F": K("6", "N"),
                  "t": K("5/3", "s"), "uv": K("1", "m/s")},
                 {"vz": U("m/s"), "z": U("")}, ["vz = F*t/m", "z*uv = vx + sqrt(2)*vy + sqrt(3)*vz"], "z",
                 ["constant force along +z only changes v_z", "vector encoded as vx + sqrt2 vy + sqrt3 vz (m/s)"]),
    "option_values": {"A": "3 + 4*sqrt(2) + sqrt(15)", "B": "4 + 3*sqrt(2) + 5*sqrt(3)",
                      "C": "3 + 4*sqrt(2) - 5*sqrt(3)", "D": "3 + 4*sqrt(2) + 5*sqrt(3)"}, "note": ""}

# ------------------------------------------------------------------ Waves
FORMALS["m6w9oa23"] = {
    "formal": AR(CUR(True, "v = sqrt(B/rho); solids much stiffer -> faster"),
                 CUR(False, "gases have much SMALLER bulk modulus than solids")),
    "note": ""}

FORMALS["m6qvb92i"] = {
    "formal": ES({"Bk": S("Pa"), "r1": S("kg/m^3"), "L1": K("10", "cm")},
                 {"r2": U("kg/m^3", "positive"), "v1": U("m/s", "positive"), "v2": U("m/s", "positive"),
                  "f": U("Hz", "positive"), "L2": U("cm", "positive")},
                 ["r2 = 16*r1", "v1**2*r1 = Bk", "v2**2*r2 = Bk", "f*4*L1 = 9*v1", "f*2*L2 = 4*v2"], "L2",
                 ["v = sqrt(B/rho)", "closed tube n-th harmonic f = n v/(4L) (n odd), open f = n v/(2L)",
                  "end corrections neglected"]),
    "option_values": {"A": "15/7", "B": "20/9", "C": "20/7", "D": "15/9"}, "note": ""}


def _dnis(ao, po):
    return COMP(ES({"A1": K("4"), "A2": K("2"), "d": K("2*pi/3"), "Ao": K(ao), "po": K(po)}, {"z": U("")},
                   ["z = (A1 + A2*cos(d) - Ao*cos(po))**2 + (A2*sin(d) - Ao*sin(po))**2"], "z",
                   ["phasor sum: resultant = A1 + A2 e^{i d}; option (Ao, po) correct iff Ao e^{i po} equals it",
                    "phase measured relative to y1"]), "== 0")


FORMALS["m9dnisox"] = {
    "formal": SEL({"A": _dnis("sqrt(3)", "pi/6"), "B": _dnis("2*sqrt(3)", "pi/6"), "C": _dnis("6", "2*pi/3"),
                   "D": _dnis("6", "pi/3")}),
    "option_values": OPT_SETS, "note": "option claims via phasor residual."}

FORMALS["m9dnod3o"] = {
    "formal": ES({"T": S("N"), "rho": S("kg/m^3"), "R": S("m")},
                 {"v1": U("m/s", "positive"), "v2": U("m/s", "positive"), "x": U("", "positive")},
                 ["v1**2*rho*pi*R**2 = T", "v2**2*rho*pi*(R/2)**2 = T", "x*v1 = v2"], "x",
                 ["v = sqrt(T/mu), mu = rho pi r^2"]),
    "option_values": {"A": "8", "B": "4", "C": "2", "D": "sqrt(2)"}, "note": ""}

FORMALS["m9e5j7xb"] = {
    "formal": ES({"w1": K("1.5", "1/s"), "w2": K("50.5", "1/s")},
                 {"wa": U("1/s", "positive"), "wb": U("1/s", "positive"), "T": U("s", "positive")},
                 ["wa = w2 + w1", "wb = w2 - w1", "T*(wa - wb) = 2*pi"], "T",
                 ["2 cos A cos B = cos(A+B) + cos(A-B): component waves at 52 and 49 rad/s",
                  "beat period = 2 pi/(wa - wb) = 2 pi/3 s; stem asks 'close to nearest integer'"],
                 options_rounded={"rel_tol": "0.05"}),
    "option_values": {"A": "1", "B": "4", "C": "2", "D": "6"},
    "note": "exact 2.094 s; options_rounded 5% (stem says nearest integer)."}

FORMALS["m6t9xt1i"] = {
    "formal": ES({"k": K("20*10**-3", "1/mm"), "w": K("600", "1/s")}, {"v": U("m/s")}, ["v*k = -w"], "v",
                 ["y = A sin(kx + wt) travels towards -x with speed w/k"]),
    "option_values": {"A": "-60", "B": "60", "C": "30", "D": "-30"}, "note": ""}

FORMALS["m9ghxmmj"] = {
    "formal": ES({"v": S("m/s"), "L": S("m")}, {"f1": U("Hz", "positive"), "f2": U("Hz", "positive"), "p": U("")},
                 ["f1*4*L = v", "f2*4*(L - L/5) = v", "f2 = f1*(1 + p/100)"], "p",
                 ["closed pipe fundamental v/(4L); uniform cross-section so 1/5 volume of water shortens the air "
                  "column to 4L/5", "p = percentage change"]),
    "option_values": {"A": "20", "B": "25", "C": "-20", "D": "-25"}, "note": ""}

FORMALS["m9gxgc4u"] = {
    "formal": ES({"L1": K("100", "cm"), "L2": K("120", "cm"), "b": K("15", "Hz")}, {"v": U("m/s", "positive")},
                 ["v/(4*L1) - v/(4*L2) = b"], "v", ["closed tubes, fundamental v/(4L), end correction neglected"]),
    "option_values": {"A": "370", "B": "340", "C": "335", "D": "360"}, "note": ""}

FORMALS["m9fnut39"] = {
    "formal": ES({"w": K("628", "1/s"), "v": K("300", "m/s"), "p": K("3.14")}, {"lam": U("m", "positive")},
                 ["lam*w = 2*p*v"], "lam", ["v = omega/k, k = 2 pi/lambda, pi = 3.14"]),
    "option_values": {"A": "0.33", "B": "0.5", "C": "3", "D": "5"},
    "note": "explanation arithmetic says 2 m (wrong); exact 3 m = key C."}


def _e5j2pk(ko, wo, f0):
    return COMP(ES({"lam": K("7.5", "cm"), "dx": K("1.2", "cm"), "dt": K("0.3", "s"), "ko": K(ko, "1/cm"),
                    "wo": K(wo, "1/s"), "f0": K(f0)},
                   {"k": U("1/cm", "positive"), "v": U("cm/s", "positive"), "w": U("1/s", "positive"), "z": U("")},
                   ["k*lam = 2*pi", "v*dt = dx", "w = k*v", "z = (k/ko - 1)**2 + (w/wo - 1)**2 + (f0 - 1)**2"], "z",
                   ["k = 2 pi/lambda, v = distance/time, w = k v; +x travel -> (kx - wt)",
                    "crest at x = 0, t = 0: y(0,0)/A must be 1 (f0 = 1 for cos, 0 for sin)",
                    "printed coefficients have 2 decimals: each accepted within ~1% (z < 2e-4)"]), "< 2*10**-4")


FORMALS["m9e5j2pk"] = {
    "formal": SEL({"A": _e5j2pk("0.83", "3.35", "1"), "B": _e5j2pk("0.83", "3.5", "0"),
                   "C": _e5j2pk("0.13", "0.5", "1"), "D": _e5j2pk("3.35", "0.83", "1")}),
    "option_values": OPT_SETS,
    "note": "exact k = 0.8378/cm (printed 0.83 is truncated), w = 3.351/s."}

FORMALS["m9e8b438"] = {
    "formal": ES({"k": K("20*pi", "1/m")}, {"lam": U("m", "positive"), "d": U("cm", "positive")},
                 ["k*lam = 2*pi", "d = lam/2"], "d",
                 ["'same oscillating speed' read as same speed at ALL times -> points half a wavelength apart"]),
    "option_values": {"A": "10", "B": "2.5", "C": "20", "D": "5"}, "note": ""}

# ------------------------------------------------------------------ Capacitors
FORMALS["m9gxgby4"] = {
    "formal": ES({"C0": K("100", "pF"), "V0": K("60", "V"), "V": K("20", "V")}, {"C": U("pF", "positive")},
                 ["C0*V0 = (C0 + C)*V"], "C", ["charge conserved after battery removed; common voltage"]),
    "option_values": {"A": "600", "B": "100", "C": "400", "D": "200"}, "note": ""}


def _ulvj8c(l, b, d):
    return COMP(ES({"l0": K("3", "cm"), "b0": K("1", "cm"), "d0": K("3", "um"), "l": K(l, "cm"), "b": K(b, "cm"),
                    "d": K(d, "um")}, {"f": U("", "positive")}, ["f*l0*b0*d = l*b*d0"], "f",
                   ["C = eps0 l b/d; f = C_new/C_old"]), "== 10")


FORMALS["m6ulvj8c"] = {
    "formal": SEL({"A": _ulvj8c("30", "1", "1"), "B": _ulvj8c("3", "1", "30"), "C": _ulvj8c("6", "5", "3"),
                   "D": _ulvj8c("1", "1", "10"), "E": _ulvj8c("5", "2", "1")}),
    "note": "factors 30, 0.1, 10, 1/30, 10 -> C and E."}

FORMALS["m9ej6s0x"] = {
    "formal": ES({"q": K("5*10**-6", "C"), "qi": K("4*10**-6", "C")}, {"K": U("", "positive")},
                 ["qi = q*(1 - 1/K)"], "K", ["induced charge q' = q (1 - 1/K)"]),
    "explanation_value": "5", "note": ""}

FORMALS["m6rko5o0"] = {
    "formal": ES({"V": K("20", "V"), "d": K("1", "um"), "e0": K("8.85*10**-12", "F/m")},
                 {"E": U("V/m", "positive"), "u": U("J/m^3", "positive")}, ["E*d = V", "u = e0*E**2/2"], "u",
                 ["u = eps0 E^2/2, E = V/d", "eps0 = 8.85e-12 F/m is NOT given in the stem (standard value)"],
                 options_rounded={"rel_tol": "0.02"}),
    "option_values": {"A": "1.8*10**3", "B": "2*10**2", "C": "2*10**-4", "D": "1.8*10**5"},
    "note": "exact 1770 J/m^3; printed 1.8e3 (1.7%)."}

FORMALS["m6qvbt5l"] = {
    "formal": ES({"e": K("1.6*10**-19", "C"), "E": K("9.1", "V/cm"), "l": K("10", "cm"),
                  "m": K("9.1*10**-31", "kg"), "vx": K("10**6", "m/s")},
                 {"vy": U("m/s", "positive")}, ["vy*m*vx = e*E*l"], "vy", ["a = eE/m for t = l/vx"]),
    "option_values": {"A": "1*10**6", "B": "16*10**6", "C": "16*10**4", "D": "0"}, "note": "reused."}

FORMALS["m6qvbk94"] = {
    "formal": ES({"C": K("40", "uF"), "V": K("100", "V"), "K": K("2"), "uq": K("1", "mC"), "uj": K("1", "J")},
                 {"dQ": U("C"), "dU": U("J"), "z": U("")},
                 ["dQ = (K - 1)*C*V", "dU = (K - 1)*C*V**2/2", "z = dQ/uq + sqrt(2)*dU/uj"], "z",
                 ["battery stays connected: V constant", "pair (dQ in mC, dU in J) encoded as dQ + sqrt2 dU"]),
    "option_values": {"A": "8 + 2*sqrt(2)", "B": "4 + sqrt(2)/5", "C": "2 + sqrt(2)/5", "D": "2 + 2*sqrt(2)/5"},
    "note": "4 mC and 0.2 J."}

FORMALS["m6qjznvt"] = {
    "formal": ES({"e0": K("9*10**-12", "F/m"), "p": K("22/7"), "r": K("10", "cm"), "I": K("0.15", "A"),
                  "dV": K("7*10**8", "V/s"), "um": K("1", "um")},
                 {"d": U("m", "positive"), "x": U("", "positive")},
                 ["I*d = e0*p*r**2*dV", "d = x*um"], "x", ["I = C dV/dt, C = e0 A/d"]),
    "explanation_value": "1320", "note": "reused."}

FORMALS["m6rp5unr"] = {
    "formal": ES({}, {"em": U(), "el": U(), "et": U(), "vq": U(), "vm": U(), "vl": U(), "vt": U(),
                      "cq": U(), "cm": U(), "cl": U(), "ct": U(), "z": U()},
                 ["em = 1", "el = 2", "et = -2", "vq = -1", "vm = em", "vl = el", "vt = et",
                  "cq = 1 - vq", "cm = -vm", "cl = -vl", "ct = -vt",
                  "z = cq + sqrt(2)*cm + sqrt(3)*cl + sqrt(5)*ct"], "z",
                 ["exponents of (charge, M, L, T): energy = M L^2 T^-2; potential = energy/charge; "
                  "capacitance = charge/potential", "encoding z = q + sqrt2 m + sqrt3 l + sqrt5 t"]),
    "option_values": {"A": "1 - sqrt(2) - 2*sqrt(3) + 2*sqrt(5)", "B": "2 - 2*sqrt(2) + 2*sqrt(3) + 2*sqrt(5)",
                      "C": "2 - sqrt(2) - 2*sqrt(3) + 2*sqrt(5)", "D": "1 - 2*sqrt(2) - 2*sqrt(3) - 2*sqrt(5)"},
    "note": "[C^2 M^-1 L^-2 T^2]."}

# ------------------------------------------------------------------ Magnetics
FORMALS["m9gxgcl8"] = {
    "formal": AR(
        COMP(ES({"p": S("kg*m/s"), "B": S("T"), "e": S("C")},
                {"rO": U("m", "positive"), "rH": U("m", "positive"), "x": U("", "positive")},
                ["rO*2*e*B = p", "rH*e*B = p", "x*rO = rH"], "x",
                ["r = p/(|q| B); curvature = 1/r; x = curvature(O2-)/curvature(H+)",
                 "assertion 'O2- has smaller curvature' <-> x < 1"]), "< 1"),
        COMP(ES({"p": S("kg*m/s"), "B": S("T"), "e": S("C")},
                {"rp": U("m", "positive"), "re": U("m", "positive"), "y": U("", "positive")},
                ["rp*e*B = p", "re*e*B = p", "y*re = rp"], "y",
                ["r = p/(|q| B); y = r_proton/r_electron", "reason 'proton radius smaller' <-> y < 1"]), "< 1")),
    "note": "literal reading: O2- radius is HALF -> LARGER curvature, so A is false; equal |q| and p -> equal "
            "radii, so R is false. Code 0 (both false) is not among the options -> expected disagreement."}

FORMALS["m9fnutvk"] = {
    "formal": ES({"mr": K("10/pi"), "er": K("1/0.0885")}, {"x": U("", "positive")}, ["x**2 = mr*er"], "x",
                 ["v = c/sqrt(mu_r eps_r)"]),
    "explanation_value": "6", "note": "reused."}

FORMALS["m9fnurpn"] = {
    "formal": ES({"L": K("4", "cm"), "I": K("8", "A"), "B": K("0.15", "T")}, {"F": U("mN", "positive")},
                 ["F = B*I*L"], "F", ["F = B I L sin 90"]),
    "explanation_value": "48", "note": ""}

FORMALS["m9e5j2hj"] = {
    "formal": ES({"N1": K("15"), "A1": K("3.6*10**-3", "m^2"), "B1": K("0.25", "T"), "R1": K("5", "ohm"),
                  "N2": K("21"), "A2": K("1.8*10**-3", "m^2"), "B2": K("0.5", "T"), "R2": K("7", "ohm")},
                 {"x": U("", "positive")}, ["x*N2*A2*B2*R1 = N1*A1*B1*R2"], "x",
                 ["voltage sensitivity S_V = N A B/(k R), same k"]),
    "option_values": {"A": "1", "B": "1/3", "C": "1/2", "D": "1/4"}, "note": "reused; x = S_V1/S_V2."}

FORMALS["m9dunofb"] = {
    "formal": ES({"R": S("m"), "I": S("A"), "mu": S("H/m")},
                 {"x": U("m", "positive"), "B1": U("T", "positive"), "B2": U("T", "positive"),
                  "q": U("", "positive")},
                 ["4*x = 3*R", "B1*2*R = mu*I", "B2*2*(R**2 + x**2)**(3/2) = mu*I*R**2", "q*B1 = B2"], "q",
                 ["centre B = mu I/(2R); axis B = mu I R^2/(2 (R^2+x^2)^(3/2))"]),
    "option_values": {"A": "64/125", "B": "25/16", "C": "4/5", "D": "16/25"}, "note": ""}

FORMALS["m9e5j2rw"] = {
    "formal": SEL({**{lab: COMP(ES({"B": S("T"), "A": S("m^2"), "l": S("m"), "mu0": S("H/m"), "mur": K("2")},
                                   {"W": U("J", "positive"), "k": U("", "positive")},
                                   ["W = B**2*A*l/(2*mur*mu0)", "W = k*B**2*A*l/mu0"], "k",
                                   ["energy density B^2/(2 mu), mu = mu_r mu0, volume A l", "W = k B^2 A l/mu0"]), c)
                      for lab, c in {"A": "== 1/4", "B": "== 1/2", "C": "== 1"}.items()},
                   "D": CUR(False, "B^2 A l has no 1/mu0: not even an energy dimensionally")}),
    "option_values": OPT_SETS, "note": "A, B, C computed on k; D curated false (dimensionally inconsistent)."}

FORMALS["m6v42le1"] = {
    "formal": ES({"m": K("9*10**-31", "kg"), "q": K("1.6*10**-19", "C"), "mu": MU0, "I": K("1.5", "A"),
                  "T": K("75", "ns")}, {"n": U("1/m", "positive")}, ["T*q*mu*n*I = 2*pi*m"], "n",
                 ["T = 2 pi m/(qB), B = mu0 n I"]),
    "explanation_value": "250", "note": "reused."}

_W7 = ["wire along z; B = mu I/(2 pi r) (azimuthal); magnetic force does no work, speed stays v0",
       "m dv_z = q B dr  ->  m (v_z - v0) = (q mu I/2pi) ln(r/a); turning point: radial velocity 0 -> v_z = -v0",
       "hence 2 m v0 = (q mu I/2pi) ln(a/x)"]
FORMALS["m6w9o7vn"] = {
    "formal": SEL({
        "A": COMP(ES({"G": K("1/(4*pi)")}, {"r": U("", "positive")}, ["4*pi*G = log(1/r)"], "r",
                     _W7 + ["specialised at G = m v0/(q mu I) = 1/(4 pi); r = x/a; an identity must hold here"]),
                  "== 1 - 1/(8*pi)"),
        "B": COMP(ES({"m": S("kg"), "v0": S("m/s"), "q": S("C"), "I": S("A"), "mu": S("H/m"), "a": S("m")},
                     {"x": U("m", "positive"), "y": U("")},
                     ["2*m*v0 = (q*mu*I/(2*pi))*log(a/x)", "log(a/x) = y*m*v0/(q*mu*I)"], "y", _W7), "== 4*pi"),
        "C": CUR(False, "a[1 - (m v/q) mu0 I] is dimensionally inconsistent ((m v/q) mu0 I is not dimensionless)"),
        "D": COMP(ES({"G": K("1/(4*pi)")}, {"r": U("", "positive")}, ["4*pi*G = log(1/r)"], "r",
                     _W7 + ["specialised at G = m v0/(q mu I) = 1/(4 pi); r = x/a"]), "== 1/2")}),
    "option_values": OPT_SETS,
    "note": "B proved generally (ln(a/x) = 4 pi m v0/(q mu0 I)); A, D refuted at a sample; C curated."}

FORMALS["m9dnfepu"] = {
    "formal": ES({"I": S("A"), "a": S("m"), "r": S("ohm"), "mu": S("H/m"), "th": K("45", "degree")},
                 {"i1": U("A", "positive"), "i2": U("A", "positive"), "B1": U("T", "positive"),
                  "B2": U("T", "positive"), "B": U("T", "positive"), "k": U("")},
                 ["i1*r = i2*2*r", "i1 + i2 = I", "B1*4*pi*(a/2) = mu*i1*2*sin(th)",
                  "B2*4*pi*(a/2) = mu*i2*2*sin(th)", "B = 2*B1 - 2*B2", "B*a = k*mu*I"], "k",
                 ["current I enters at A, leaves at C (ABC and ADC are the two parallel paths named in the stem)",
                  "each side at distance a/2 from the centre: B = mu i/(4 pi a/2) (2 sin 45)",
                  "the two paths circulate in opposite senses -> fields subtract"]),
    "option_values": {"A": "2/(3*pi)", "B": "sqrt(2)/(3*pi)", "C": "3*pi/sqrt(2)", "D": "1/(2*pi)"},
    "note": "target k with B = k mu0 I/a; entry/exit at A, C inferred from the stem's ABC / ADC parts."}

FORMALS["m6rp6kg1"] = {
    "formal": ES({"mu": MU0, "I1": K("5", "A"), "I2": K("4", "A"), "r1": K("10", "cm"), "r2": K("4", "cm"),
                  "u": K("10**-5", "T")}, {"B": U("T"), "x": U("")},
                 ["2*pi*B = mu*(I2/r2 - I1/r1)", "B = x*u"], "x",
                 ["P outside the pair, 4 cm from Y (from figure); explanation's 0.01 m is a typo"]),
    "explanation_value": "1", "note": "reused from verify_ascent300_calcs (figure placement of P)."}

FORMALS["m6ulvdwc"] = {
    "formal": ES({"I": K("5", "A"), "s": K("1/sqrt(2)", "m"), "mu": MU0, "th": K("45", "degree"),
                  "u": K("10**-6", "T")},
                 {"d": U("m", "positive"), "B1": U("T", "positive"), "B": U("T", "positive"), "p": U("")},
                 ["2*d = s", "B1*4*pi*d = mu*I*2*sin(th)", "B = 4*B1", "B = p*u"], "p",
                 ["finite wire: B = mu I/(4 pi d)(sin a1 + sin a2), d = side/2, angles 45 deg; 4 sides"]),
    "explanation_value": "8", "note": ""}

FORMALS["m6qkgtjp"] = {
    "formal": ES({"I": S("A"), "a": S("m"), "mu": S("H/m")},
                 {"Bm": U("T", "positive"), "ri": U("m", "positive"), "ro": U("m", "positive"), "z": U("")},
                 ["Bm*2*pi*a = mu*I", "mu*I*ri/(2*pi*a**2) = Bm/2", "mu*I/(2*pi*ro) = Bm/2", "z*a = ri + sqrt(2)*ro"],
                 "z", ["inside B = mu I r/(2 pi a^2), outside mu I/(2 pi r); max at r = a",
                       "pair (r_in/a, r_out/a) encoded as r_in/a + sqrt2 r_out/a"]),
    "option_values": {"A": "1/2 + 3*sqrt(2)", "B": "1/4 + 3*sqrt(2)/2", "C": "1/2 + 2*sqrt(2)",
                      "D": "1/4 + 2*sqrt(2)"}, "note": ""}

FORMALS["m6rp62so"] = {
    "formal": ES({"h": S("J*s"), "e": S("C"), "B": S("T"), "m": S("kg"), "n": K("2")},
                 {"r": U("m", "positive"), "v": U("m/s", "positive"), "k": U("", "positive")},
                 ["m*v*r = n*h/(2*pi)", "m*v = e*B*r", "r**2 = k*h/(e*B)"], "k",
                 ["Bohr: m v r = n h/(2 pi); circular motion r = m v/(eB); first excited state n = 2"]),
    "option_values": {"A": "1/pi", "B": "4/pi", "C": "1/(2*pi)", "D": "2/pi"},
    "note": "target k with r^2 = k h/(eB); option C's printed 'e eB' read as eB (typo)."}

FORMALS["m6rp6a8d"] = {
    "formal": ES({"v": K("2*10**5", "m/s"), "r": K("2", "cm"), "m": K("1.6*10**-27", "kg"),
                  "q": K("1.6*10**-19", "C"), "u": K("10**4", "N/C")},
                 {"B": U("T", "positive"), "E": U("N/C", "positive"), "x": U("", "positive")},
                 ["q*v*B = m*v**2/r", "E = v*B", "E = x*u"], "x",
                 ["undeflected: qE = qvB; circle r = m v/(qB)", "proton charge 1.6e-19 C (not given in stem)"]),
    "explanation_value": "2", "note": ""}

FORMALS["m6qjznxx"] = {
    "formal": ES({"N": K("200"), "I": K("0.29", "A"), "B": K("2.9*10**-4", "T"), "mu": MU0, "u": K("1", "cm")},
                 {"L": U("m", "positive"), "x": U("", "positive")}, ["B*L = mu*N*I", "L = x*pi*u"], "x",
                 ["long solenoid B = mu0 N I/L"]),
    "explanation_value": "8", "note": ""}

FORMALS["m6v42mhq"] = {
    "formal": AR(CUR(True, "possible: v parallel to B gives zero magnetic force -> uniform straight motion"),
                 CUR(True, "if B is along v, F = q v x B = 0"),
                 explains=CUR(True, "zero force because v || B is exactly why the motion is uniform")),
    "note": ""}

# ------------------------------------------------------------------ Wave optics
FORMALS["m9fnutwn"] = {
    "formal": ES({"d": K("1.5", "mm"), "D": K("2", "m"), "lam": K("400", "nm"), "u": K("10**-3", "cm")},
                 {"a": U("m", "positive"), "x": U("", "positive")},
                 ["2*lam*D/a = 20*lam*D/d", "a = x*u"], "x",
                 ["central diffraction maximum width 2 lambda D/a holds 20 fringe widths lambda D/d"]),
    "explanation_value": "15", "note": "'20 maxima contained' read as width = 20 fringe widths."}

FORMALS["m9ghxmak"] = {
    "formal": ES({"lam": S("m"), "D": S("m"), "d1": K("0.2", "mm"), "d2": K("0.4", "mm")},
                 {"b1": U("m", "positive"), "b2": U("m", "positive"), "p": U("")},
                 ["b1*d1 = lam*D", "b2*d2 = lam*D", "b2 = b1*(1 - p/100)"], "p",
                 ["fringe width lambda D/d", "p = percentage DECREASE (options are magnitudes)"]),
    "option_values": {"A": "25", "B": "50", "C": "0", "D": "100"}, "note": ""}

FORMALS["m9fnutoo"] = {
    "formal": ES({}, {"s": U("", "positive"), "c": U(""), "th": U("rad", "positive")},
                 ["1 - 2*s = 0", "c = 1 - 2*s", "2*th = acos(c)"], "th",
                 ["I3 = (I0/2) cos^2(th) sin^2(th) = (I0/2) s (1 - s), s = sin^2(th), th = angle P2-P3 "
                  "(P1 _|_ P2)", "maximum of the concave s(1-s): d/ds = 1 - 2s = 0", "cos 2th = 1 - 2s, th in "
                  "(0, pi/2)"]),
    "option_values": {"A": "pi/6", "B": "pi/3", "C": "pi/4", "D": "pi/8"}, "note": "stationarity written by hand."}

FORMALS["m9gxgde2"] = {
    "formal": ES({"I1": S("W/m^2")},
                 {"I2": U("W/m^2", "positive"), "Imax": U("W/m^2", "positive"), "Imin": U("W/m^2", "positive"),
                  "x": U("", "positive")},
                 ["I2 = 9*I1", "Imax = (sqrt(I1) + sqrt(I2))**2", "Imin = (sqrt(I2) - sqrt(I1))**2", "x*Imin = Imax"],
                 "x", ["I = I1 + I2 +- 2 sqrt(I1 I2)"]),
    "option_values": {"A": "8", "B": "4", "C": "3", "D": "9"}, "note": ""}

FORMALS["m9dunnrf"] = {
    "formal": ES({"lam": K("628", "nm"), "th": K("30", "degree")},
                 {"u": U("", "positive"), "c2": U("", "positive"), "a": U("um", "positive")},
                 ["c2**2 + 4*u**2 = 1", "3*u = sin(th)*c2 - cos(th)*2*u", "a*u = lam"], "a",
                 ["minima a sin(theta_n) = n lambda; theta_2 (left) + theta_3 (right) = 30 deg",
                  "u = lambda/a, sin(theta_2) = 2u, cos(theta_2) = c2, sin(theta_3) = sin(30 - theta_2) = 3u",
                  "exact (no small-angle approximation): a = 6.07 um"]),
    "explanation_value": "6", "note": "small-angle gives 5.997 um; both round to 6."}

FORMALS["m9e5j875"] = {
    "formal": ES({"E0": S("V/m"), "d": K("60", "degree")}, {"E": U("V/m", "positive"), "k": U("", "positive")},
                 ["E**2 = 2*E0**2 + 2*E0**2*cos(d)", "E = k*E0"], "k",
                 ["superposition of equal amplitudes with phase difference pi/3"],
                 options_rounded={"rel_tol": "0.02"}),
    "option_values": {"A": "1.7", "B": "1", "C": "0.9", "D": "3.4"}, "note": "exact sqrt3 = 1.732."}

FORMALS["m9dunr0t"] = {
    "formal": ES({}, {"c": U("", "positive"), "th": U("rad", "nonnegative")}, ["c*sqrt(3) = 1", "th = acos(c)"], "th",
                 ["propagation along the normal (1,1,1) of x + y + z = const; direction cosine 1/sqrt3"]),
    "option_values": {"A": "acos(2/3)", "B": "acos(1/sqrt(3))", "C": "acos(1/3)", "D": "acos(sqrt(2/3))"},
    "note": ""}

FORMALS["m9fnurol"] = {
    "formal": ES({"I": S("W/m^2")}, {"Imax": U("W/m^2", "positive"), "Imin": U("W/m^2", "positive"), "x": U("")},
                 ["Imax = (sqrt(4*I) + sqrt(9*I))**2", "Imin = (sqrt(9*I) - sqrt(4*I))**2", "Imax - Imin = x*I"],
                 "x", ["coherent superposition I = I1 + I2 +- 2 sqrt(I1 I2)"]),
    "explanation_value": "24", "note": ""}

FORMALS["m9gxgcbi"] = {
    "formal": ES({"s": S("W/m^3"), "w1": S("m")},
                 {"I1": U("W/m^2", "positive"), "I2": U("W/m^2", "positive"), "Imax": U("W/m^2", "positive"),
                  "Imin": U("W/m^2", "positive"), "x": U("", "positive")},
                 ["I1 = s*w1", "I2 = s*(2*w1)", "Imax = (sqrt(I1) + sqrt(I2))**2", "Imin = (sqrt(I2) - sqrt(I1))**2",
                  "x*Imin = Imax"], "x",
                 ["intensity from a slit proportional to its width (standard JEE model)"]),
    "option_values": {"A": "3", "B": "(2*sqrt(2) + 1)/(2*sqrt(2) - 1)", "C": "9",
                      "D": "(3 + 2*sqrt(2))/(3 - 2*sqrt(2))"}, "note": ""}

FORMALS["m6v42s3f"] = {
    "formal": ES({"lam": K("690", "nm"), "mu": K("1.44"), "d": K("1.5", "mm"), "D": K("0.72", "m")},
                 {"b": U("mm", "positive")}, ["b*mu*d = lam*D"], "b", ["fringe width (lambda/mu) D/d in the liquid"]),
    "option_values": {"A": "0.63", "B": "0.33", "C": "0.46", "D": "0.23"}, "note": "exact 0.23 mm."}

# ------------------------------------------------------------------ not formalized
OMITTED = {
    "m6srn9ar": "image-only: emf source and inductance values are only in the figure",
    "m9e5j3jq": "image-only: string angles only in the figure",
    "m9eiu3p3": "image-only: position of the removed disc only in the figure",
    "m9dunrik": "image-only: forces on the lamina only in the figure",
    "m9ghxn1s": "image-only: shape/angles of ABCDE only in the figure",
    "m6rp6kty": "graph options",
    "m6qvbxqu": "image-only: position of the removed part only in the figure",
    "m9e5j921": "image-only: arrangement of bodies about PQ only in the figure",
    "m9ghxn2p": "image-only: capacitor network",
    "m9doh010": "image-only: dielectric arrangement",
    "m9fnurcp": "image-only: the two dielectric configurations",
    "m6srn9a6": "image-only: circuit (position of R)",
    "m6t9yjrz": "image-only: circuit",
    "m6w9ofxk": "image-only: charge-time graph",
    "m9e5j7zn": "graph options",
    "m9fnutma": "image-only: capacitor network",
    "m9fnuro2": "image-only: sense of the two semicircles",
    "m6rjz7x8": "image-only: bent-wire geometry",
    "m6v43dm8": "image-only: placement of Amperian loops",
    "m9e5j89t": "image-only: relative directions of B1 and B2",
    "m6v43dfw": "graph options",
    "m6v43dsv": "image-only: placement of P1/P2 on the slits (also: unpolarized light through orthogonal "
                "polarizers gives mutually INCOHERENT beams -> I0/2, not the keyed I0/4)",
}
