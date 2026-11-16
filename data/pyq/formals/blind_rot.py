"""Blind chapter batch rot (Rotational Motion): written from blind/rot/questions.md ONLY (keys/explanations sealed).

Conventions
  * rigid_body formals compute every moment of inertia twice (standard table + theorems vs direct integration).
  * Symbolic-answer MCQs: a dimensionless ratio target (e.g. k in I = k M R^2); each option's k is read from its
    TEXT. When the options depend on two or more free parameters, the stem is solved at a generic numeric
    instance (stated in the note) and every option is evaluated at the same instance.
  * A dimensionally inconsistent option is encoded as -1 (it cannot equal any admissible positive ratio).
  * Conceptual / range MCQs use statement_set (select_combination, option k <-> "{k}"); truths are computed by a
    sub-formal wherever a computation exists, otherwise curated (teacher must confirm).
"""
K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
S = lambda u="": {"value": "symbolic", "unit": u}  # noqa: E731
U = lambda u="", d="real": {"unit": u, "domain": d}  # noqa: E731
C = lambda t, n="": {"truth": t, "basis": "curated", "note": n}  # noqa: E731
P = "PHYSICS"
ONE = {"A": "{1}", "B": "{2}", "C": "{3}", "D": "{4}"}


def body(shape, mass=None, center=("0", "0", "0"), axis=(0, 0, 1), u=None, sign=1, density=None,
         profile=None, **dims):
    b = {"shape": shape, "dims": dims, "center": list(center), "axis": list(axis), "sign": sign}
    if mass is not None:
        b["mass"] = mass
    if density is not None:
        b["density"] = density
    if profile is not None:
        b["density_profile"] = profile
    if u is not None:
        b["u"] = list(u)
    return b


def ax(bodies, point=("0", "0", "0"), d=(0, 0, 1)):
    return {"bodies": list(bodies), "axis": {"point": list(point), "dir": list(d)}}


def rb(knowns, bodies=None, inertia=None, unknowns=None, equations=None, target=None, model=(), **extra):
    f = {"kind": "rigid_body", "knowns": knowns, "bodies": bodies or {}, "inertia": inertia or {},
         "unknowns": unknowns or {}, "equations": equations or [], "model": list(model), **extra}
    if target:
        f["target"] = target
    return f


def es(knowns, unknowns, equations, target, model=(), **extra):
    return {"kind": "equation_system", "knowns": knowns, "unknowns": unknowns, "equations": equations,
            "target": target, "model": list(model), **extra}


def T(formal, claim):
    return {"formal": formal, "claim": claim, "subject": P}


def sel(statements):
    return {"kind": "statement_set", "format": "select_combination", "statements": statements}


def E(formal, ov=None, note=""):
    d = {"formal": formal, "note": note}
    if ov is not None:
        d["option_values"] = ov
    return d


FORMALS: dict = {}
SKIPPED: dict = {}

# ============================================================== chunk 1 (questions 1-25)
FORMALS["JtkUq44cynQYPh0c"] = E(
    rb({"M": S("kg"), "R": S("m")}, {"w": body("ring", "M", R="R")}, {"I": ax(["w"], d=(1, 0, 0))},
       {"k": U("", "positive")}, ["I = k*M*R**2"], "k", ["circular wire = ring; axis = a diameter (in its plane)"]),
    {"A": "1/2", "B": "1", "C": "2", "D": "1/4"}, "ratio target k, I = k M R^2")

FORMALS["74sEsWoySBVGwUIk"] = E(
    rb({"M": K("7", "kg"), "m": K("3", "kg"), "R": S("m"), "w1": S("1/s")},
       {"d": body("disc", "M", R="R"), "p1": body("point", "m", center=("R", "0", "0")),
        "p2": body("point", "m", center=("-R", "0", "0"))},
       {"Ii": ax(["d"]), "If": ax(["d", "p1", "p2"])},
       {"w2": U("1/s", "positive"), "x": U("", "positive")}, ["Ii*w1 = If*w2", "x = w2/w1"], "x",
       ["no external torque about the axis: angular momentum conserved", "small spheres = point masses at the rim"]),
    {"A": "(7+3)/7", "B": "(7+3)/3", "C": "7/(7+4*3)", "D": "7/(7+2*3)"},
    "ratio w2/w1 at generic instance M = 7 kg, m = 3 kg; options evaluated at the same instance")

_slide = es({"g": S("m/s^2"), "th": K("30", "degree"), "m1": S("kg"), "m2": S("kg"), "m3": S("kg")},
            {"a1": U("m/s^2"), "a2": U("m/s^2"), "a3": U("m/s^2"), "D2": U("m^2/s^4")},
            ["m1*a1 = m1*g*sin(th)", "m2*a2 = m2*g*sin(th)", "m3*a3 = m3*g*sin(th)",
             "D2 = (a1 - a2)**2 + (a1 - a3)**2"], "D2",
            ["frictionless incline: no friction torque, pure sliding; Newton's 2nd law along the slope",
             "incline angle instance 30 deg (result independent of the angle)"])
FORMALS["atNumTaIjE3kMyJr"] = E(sel({
    "A": C(False, "strict maximum impossible: all three accelerations are equal (statement D computed)"),
    "B": C(False, "as A"), "C": C(False, "as A"),
    "D": T(_slide, "== 0")}), ONE, "option k <-> {k}; D computed (spread of accelerations is exactly 0)")

FORMALS["KZnaV6RylgRhrevz"] = E(
    es({"m": S("kg"), "w": S("1/s"), "K1": S("J")},
       {"r1": U("m", "positive"), "r2": U("m", "positive"), "L1": U("J*s"), "L2": U("J*s"), "x": U("", "positive")},
       ["K1 = m*r1**2*w**2/2", "K1/2 = m*r2**2*(2*w)**2/2", "L1 = m*r1**2*w", "L2 = m*r2**2*(2*w)", "x = L2/L1"],
       "x", ["particle in uniform circular motion: KE = m r^2 w^2/2, L = m r^2 w; mass unchanged"]),
    {"A": "1/4", "B": "2", "C": "4", "D": "1/2"}, "ratio L'/L")

_vk = {n: S("m") for n in ("rx", "ry", "rz")} | {n: S("N") for n in ("Fx", "Fy", "Fz")}
_vu = {"tx": U("N*m"), "ty": U("N*m"), "tz": U("N*m"), "d1": U("N*m^2"), "d2": U("N^2*m")}
_tau = ["tx = ry*Fz - rz*Fy", "ty = rz*Fx - rx*Fz", "tz = rx*Fy - ry*Fx", "d1 = rx*tx + ry*ty + rz*tz"]
_vf = lambda t: es(_vk, _vu, _tau + ["d2 = Fx*tx + Fy*ty + Fz*tz"], t,  # noqa: E731
                   ["tau = r x F with general symbolic components"])
_vboth = es(_vk, {k: v for k, v in _vu.items() if k != "d2"}, _tau + ["Fx*tx + Fy*ty + Fz*tz = 0"], "d1",
            ["tau = r x F, general components; F.tau = 0 imposed as an equation: the exact solve succeeds only if it "
             "holds identically, and then r.tau is computed"])
FORMALS["CIUadGcAS8eenG8f"] = E(sel({
    "A": T(_vf("d2"), "!= 0"),       # A needs F.tau != 0
    "B": T(_vf("d1"), "!= 0"),       # B needs r.tau != 0
    "C": T(_vf("d1"), "!= 0"),
    "D": T(_vboth, "== 0")}), ONE,
    "each option is false as soon as its '!= 0' half is false; D: both dot products vanish identically")

FORMALS["V3JegbNrsTWtXNtV"] = E(
    rb({"rho": S("kg/m^3"), "R": S("m"), "t": S("m")},
       {"X": body("solid_cylinder", density="rho", R="R", L="t"),
        "Y": body("solid_cylinder", density="rho", R="4*R", L="t/4")},
       {"IX": ax(["X"]), "IY": ax(["Y"])}, {"x": U("", "positive")}, ["IY = x*IX"], "x",
       ["discs = thin cylinders of the same iron; axis = the disc's own symmetry axis"]),
    {"A": "32", "B": "16", "C": "1", "D": "64"}, "ratio I_Y/I_X")

_sph = rb({"M": S("kg"), "R": S("m")}, {"A": body("solid_sphere", "M", R="R"), "B": body("spherical_shell", "M", R="R")},
          {"IA": ax(["A"]), "IB": ax(["B"])}, {"x": U("", "positive")}, ["x = IA/IB"], "x",
          ["hollow sphere = thin spherical shell of the same outer radius"])
FORMALS["vnOj5CKUn7CTtjDi"] = E(sel({
    "A": T(_sph, "< 1"), "B": T(_sph, "> 1"), "C": T(_sph, "== 1"),
    "D": C(False, "I_A/I_B = 3/5 is fixed while the density ratio depends on the shell thickness")}), ONE,
    "computed I_A/I_B; option k <-> {k}")


def _free(target):
    return rb({"M": S("kg"), "R1": S("m"), "w1": S("1/s")},
              {"s1": body("solid_sphere", "M", R="R1"), "s2": body("solid_sphere", "M", R="2*R1")},
              {"I1": ax(["s1"]), "I2": ax(["s2"])},
              {"w2": U("1/s", "positive"), "xw": U(""), "xL": U(""), "xI": U(""), "xE": U("")},
              ["I1*w1 = I2*w2", "xw = w2/w1", "xL = (I2*w2)/(I1*w1)", "xI = I2/I1",
               "xE = (I2*w2**2/2)/(I1*w1**2/2)"], target,
              ["free space: no external torque -> L conserved", "instance: radius doubled, mass fixed"])


FORMALS["2yrP77y91dEoBdH3"] = E(sel({
    "A": T(_free("xw"), "== 1"), "B": T(_free("xL"), "== 1"), "C": T(_free("xI"), "== 1"),
    "D": T(_free("xE"), "== 1")}), ONE, "statement k = 'quantity k unchanged' (ratio == 1); option k <-> {k}")

FORMALS["TwPowX0a7PgaEvAY"] = E(
    rb({"M": S("kg"), "r": S("m")},
       {"h": body("semi_disc", "M", R="r")}, {"I": ax(["h"])}, {"k": U("", "positive")}, ["I = k*M*r**2"], "k",
       ["axis normal to the plane through the centre of the full circle"]),
    {"A": "2/5", "B": "-1", "C": "1/2", "D": "1"},
    "ratio k (I = k M r^2); option B 'Mr/4' is dimensionally wrong -> -1")

FORMALS["nbiRKpbN7QLxHsp0"] = E(
    es({"m": S("kg"), "w": S("1/s"), "R1": K("2", "m"), "R2": K("5", "m")},
       {"F1": U("N"), "F2": U("N"), "x": U("", "positive")},
       ["F1 = m*w**2*R1", "F2 = m*w**2*R2", "x = F1/F2"], "x",
       ["centre moves uniformly (inertial frame); each particle (equal masses) needs centripetal force m w^2 r",
        "generic instance R1 = 2 m, R2 = 5 m"]),
    {"A": "(2/5)**2", "B": "5/2", "C": "2/5", "D": "1"}, "ratio F1/F2 at R1 = 2, R2 = 5; options at the same instance")

FORMALS["WH2jIqhtfbspNMF1"] = E(
    rb({"m": S("kg"), "l": S("m")},
       {"A": body("point", "m"), "B": body("point", "m", center=("l", "0", "0")),
        "C": body("point", "m", center=("l", "l", "0")), "D": body("point", "m", center=("0", "l", "0"))},
       {"I": ax(["A", "B", "C", "D"], d=(-1, 1, 0))}, {"k": U("", "positive")}, ["I = k*m*l**2"], "k",
       ["A(0,0), B(l,0), C(l,l), D(0,l); axis through A along BD"]),
    {"A": "2", "B": "sqrt(3)", "C": "3", "D": "1"}, "ratio k, I = k m l^2")

FORMALS["5l4RYg5NGcZktK2L"] = E(
    rb({"m": K("7", "kg"), "M": K("3", "kg"), "R": S("m"), "w": S("1/s")},
       {"g": body("ring", "m", R="R"), "p1": body("point", "M", center=("R", "0", "0")),
        "p2": body("point", "M", center=("-R", "0", "0"))},
       {"Ii": ax(["g"]), "If": ax(["g", "p1", "p2"])},
       {"w2": U("1/s", "positive"), "x": U("", "positive")}, ["Ii*w = If*w2", "x = w2/w"], "x",
       ["angular momentum about the axis conserved"]),
    {"A": "(7+2*3)/7", "B": "(7-2*3)/(7+2*3)", "C": "7/(7+3)", "D": "7/(7+2*3)"},
    "ratio w'/w at instance m = 7, M = 3")

FORMALS["KQJHwKrZeCnzHTDE"] = E(
    rb({"M": S("kg"), "R": S("m"), "g": S("m/s^2"), "th": K("30", "degree")}, {}, {},
       {"I": U("kg*m^2", "positive"), "a": U("m/s^2"), "x": U("")},
       ["I = 3*M*R**2/7", "x = a/(g*sin(th))"], "x",
       ["Newton + torque about the centre + a = alpha R (template rolling_incline)",
        "generic instance I = (3/7) M R^2, theta = 30 deg"],
       relations=[{"template": "rolling_incline", "a": "a", "M": "M", "I": "I", "R": "R", "g": "g", "th": "th"}]),
    {"A": "1/(1 - 7/3)", "B": "1/(1 + 3/7)", "C": "1/(1 + 7/3)", "D": "1/(1 - 3/7)"},
    "ratio a/(g sin th) at instance I/(MR^2) = 3/7; options at the same instance")

FORMALS["QQ11TAciudDuQhyM"] = E(sel({
    "A": C(False, "torque of a central force is zero, not a nonzero constant"),
    "B": C(False, "a central force is not constant in direction"),
    "C": C(False, "linear momentum is not constant in circular/central motion"),
    "D": T(es({"x": S("m"), "y": S("m"), "c": S("N/m")}, {"Fx": U("N"), "Fy": U("N"), "tz": U("N*m")},
              ["Fx = c*x", "Fy = c*y", "tz = x*Fy - y*Fx"], "tz", ["central force F = c r (along r)"]), "== 0")}),
    ONE, "D computed: torque of F parallel to r vanishes identically")

FORMALS["ZTrPc4vdtmcrBxoR"] = E(
    rb({"m": S("kg"), "a": S("m")}, {"p": body("rect_plate", "m", a="a", b="a")},
       {"I": ax(["p"], point=("a/2", "a/2", "0"))}, {"k": U("", "positive")}, ["I = k*m*a**2"], "k",
       ["normal axis through a corner"]),
    {"A": "5/6", "B": "1/12", "C": "7/12", "D": "2/3"}, "ratio k, I = k m a^2")

FORMALS["22tooMeZBtDgsgfY"] = E(
    rb({"m": S("kg"), "l": S("m"), "w": S("1/s"), "g": S("m/s^2")},
       {"r": body("rod", "m", center=("l/2", "0", "0"), u=(1, 0, 0), L="l")}, {"I": ax(["r"])},
       {"h": U("m", "positive"), "x": U("", "positive")}, ["I*w**2/2 = m*g*h", "x = h*g/(l**2*w**2)"], "x",
       ["max angular speed at the lowest point; energy conservation about the fixed end"]),
    {"A": "-1", "B": "1/2", "C": "1/6", "D": "1/3"},
    "ratio h g/(l^2 w^2); option A (l w/g, not a length) is dimensionally wrong -> -1")


def _pulley(target, c1="20", c2="5", R="2", I="10"):
    return rb({"c1": K(c1, "N/s"), "c2": K(c2, "N/s^2"), "Rp": K(R, "m"), "Ip": K(I, "kg*m^2")}, {}, {},
              {"T": U("s", "positive"), "w": U("1/s"), "th": U(""), "n": U(""), "y": U("")},
              ["w = 0", "n = th/(2*pi)", target], "y",
              ["tau = F R = I alpha; pulley starts from rest", "reversal when omega returns to 0 (t > 0)",
               "theta(T) = int_0^T (T - t) alpha(t) dt (Cauchy repeated integral)"],
              calculus={"w": {"integral": "(c1*t - c2*t**2)*Rp/Ip", "var": "t", "lower": "0", "upper": "T"},
                        "th": {"integral": "(T - t)*(c1*t - c2*t**2)*Rp/Ip", "var": "t", "lower": "0", "upper": "T"}})


FORMALS["xmtiN91wgRQTentL"] = E(sel({
    "A": T(_pulley("y = (n - 3)*(6 - n)"), "> 0"), "B": T(_pulley("y = (n - 6)*(9 - n)"), "> 0"),
    "C": T(_pulley("y = n"), "> 9"), "D": T(_pulley("y = n"), "< 3")}), ONE,
    "range options as computed claims on the number of rotations n")

FORMALS["SkXe9OycfhSpUpyH"] = E(
    rb({"m": S("kg"), "R": S("m"), "g": S("m/s^2")}, {"p": body("disc", "m", R="R")}, {"I": ax(["p"])},
       {"a": U("m/s^2"), "Tn": U("N"), "al": U("1/s^2"), "x": U("")},
       ["m*a = m*g - Tn", "I*al = Tn*R", "a = al*R", "x = a/g"], "x",
       ["string does not slip: a = alpha R; frictionless bearing"]),
    {"A": "1", "B": "2/3", "C": "1/3", "D": "3/2"}, "ratio a/g")

FORMALS["0P1oWpeepv5X83HE"] = E(sel({
    "A": C(False), "B": C(False),
    "C": C(True, "L conserved; I = I0 + m x^2 falls as the insect nears the centre then rises: w up then down"),
    "D": C(False)}), ONE, "curated conceptual")

FORMALS["pArPnFOcPLv5DIR5"] = E(
    rb({"m": S("kg"), "r": S("m"), "w0": S("1/s")}, {"h": body("ring", "m", R="r")}, {"I": ax(["h"])},
       {"v": U("m/s", "positive"), "x": U("", "positive")}, ["I*w0 = m*v*r + I*v/r", "x = v/(r*w0)"], "x",
       ["angular momentum about the contact point conserved (friction acts there; mg and N have zero torque)",
        "pure rolling at the end: w = v/r"]),
    {"A": "1/4", "B": "1/3", "C": "1/2", "D": "1"}, "ratio v/(r w0)")

FORMALS["2KZ8qDYvVby0twN7"] = E(sel({
    "A": C(False), "B": C(False),
    "C": C(True, "conical pendulum: |r x mv| = m l v constant (r perpendicular to v), direction precesses"),
    "D": C(False)}), ONE, "curated conceptual")

FORMALS["a6lKQHUSUq7mYL0t"] = E(
    rb({"M": S("kg"), "R": S("m")}, {"c": body("cube", density="3*M/(4*pi*R**3)", a="2*R/sqrt(3)")},
       {"I": ax(["c"])}, {"k": U("", "positive")}, ["I = k*M*R**2"], "k",
       ["largest cube: body diagonal = 2R, side 2R/sqrt(3); same density as the sphere"]),
    {"A": "4/(9*sqrt(3*pi))", "B": "4/(3*sqrt(3*pi))", "C": "1/(32*sqrt(2*pi))", "D": "1/(16*sqrt(2*pi))"},
    "ratio k, I = k M R^2; options read literally (pi under the square root as printed)")

FORMALS["81boHpwGhVR7Pk6TRTQBO"] = E(
    es({"g": K("9.8", "m/s^2"), "R": K("1.25", "m")}, {"w": U("rpm", "positive")}, ["w**2*R = g"], "w",
       ["material at the top stays on the wall if w^2 R >= g; proper mixing needs w below sqrt(g/R)"],
       options_rounded={"rel_tol": "0.02"}),
    {"A": "0.4", "B": "1.3", "C": "8.0", "D": "27.0"}, "'close to': rounded-option match within 2%")

FORMALS["MJRqack07GUqVV3WcQzZQ"] = E(sel({
    "A": C(False), "B": C(False),
    "C": C(True, "empty pans equal: (m_p + 5 mg) l_L = m_p l_R -> l_L < l_R"),
    "D": C(False, "apparent weight depends on which pan holds the object; not 'every object lighter'")}),
    ONE, "curated conceptual")

FORMALS["vZk3cBXR23HJs2Pg"] = E(
    rb({"M": S("kg"), "V": S("m^3")}, {"c": body("solid_cylinder", "M", R="R", L="l")}, {"I": ax(["c"], d=(1, 0, 0))},
       {"l": U("m", "positive"), "R": U("m", "positive"), "dI": U("kg*m"), "d2I": U("kg", "positive"),
        "x": U("", "positive")},
       ["dI = 0", "V = pi*R**2*l", "x = l/R"], "x",
       ["fixed mass and material -> fixed volume V = pi R^2 l", "dI/dl = 0 with d2I/dl2 > 0 (minimum)"],
       calculus={"dI": {"derivative": "I", "var": "l", "subs": {"R": "sqrt(V/(pi*l))"}},
                 "d2I": {"derivative": "dI", "var": "l"}}),
    {"A": "3/sqrt(2)", "B": "sqrt(3/2)", "C": "sqrt(3)/2", "D": "1"}, "ratio l/R at the minimum")

# ============================================================== chunk 2 (questions 26-50)
FORMALS["EZjw0xKukrq96OTweT4Ds"] = E(
    rb({"m": S("kg"), "d": S("m"), "q": S("C"), "Ef": S("V/m")},
       {"p1": body("point", "m", center=("d/2", "0", "0")), "p2": body("point", "m", center=("-d/2", "0", "0"))},
       {"I": ax(["p1", "p2"])}, {"w": U("1/s", "positive"), "x": U("")},
       ["I*w**2 = q*Ef*d", "x = w**2*m*d/(q*Ef)"], "x",
       ["rotation about the centre; restoring torque p E sin(th) ~ q d E th (small angle)", "SHM: w^2 = pE/I"]),
    {"A": "1", "B": "1/2", "C": "-1/2", "D": "2"}, "ratio w^2 m d/(qE); option C has -2md under the root -> -1/2")

FORMALS["TiZmOQnPzFnqfLMyGc5uA"] = E(
    rb({"m1": S("kg"), "m2": S("kg"), "m3": S("kg"), "R": S("m"), "v": S("m/s"), "g": S("m/s^2")},
       {"ring": body("ring", "m1", R="R"), "cyl": body("solid_cylinder", "m2", R="R/2", L="R"),
        "sph": body("solid_sphere", "m3", R="R/4")},
       {"I1": ax(["ring"]), "I2": ax(["cyl"]), "I3": ax(["sph"])},
       {"h1": U("m", "positive"), "h2": U("m", "positive"), "h3": U("m", "positive"), "x": U("")},
       ["m1*g*h1 = m1*v**2/2 + I1*(v/R)**2/2", "m2*g*h2 = m2*v**2/2 + I2*(2*v/R)**2/2",
        "m3*g*h3 = m3*v**2/2 + I3*(4*v/R)**2/2", "x = h1/h2 + sqrt(2)*h2/h3"], "x",
       ["rolling without slipping up the incline: all KE (trans + rot, w = v/r) -> m g h",
        "cylinder length irrelevant (axial I = m r^2/2)"]),
    {"A": "20/15 + sqrt(2)*15/14", "B": "4/3 + sqrt(2)*3/2", "C": "2/3 + sqrt(2)*3/4", "D": "10/15 + sqrt(2)*15/7"},
    "ratio triple encoded injectively as h1/h2 + sqrt(2) h2/h3 (1 and sqrt2 are Q-independent)")

FORMALS["oZMeF2P5AgHl84kp3cyQY"] = E(
    rb({"k": S("J"), "Iq": S("kg*m^2"), "th": S("")}, {}, {},
       {"w2": U("1/s^2"), "dw2": U("1/s^2"), "al": U("1/s^2"), "x": U("")},
       ["Iq*w2/2 = k*th**2", "al = dw2/2", "x = al*Iq/(k*th)"], "x",
       ["KE = I w^2/2 = k th^2", "alpha = w dw/dth = (1/2) d(w^2)/dth"],
       calculus={"dw2": {"derivative": "2*k*th**2/Iq", "var": "th"}}),
    {"A": "1/4", "B": "1", "C": "1/2", "D": "2"}, "ratio alpha I/(k th)")

FORMALS["ANiozDvSSiYK3aYNBxrC5"] = E(
    es({"I": K("1.5", "kg*m^2"), "KE": K("1200", "J"), "al": K("20", "1/s^2")},
       {"w": U("1/s", "positive"), "t": U("s", "positive")}, ["KE = I*w**2/2", "w = al*t"], "t",
       ["starts from rest, constant angular acceleration"]),
    {"A": "2.5", "B": "3", "C": "5", "D": "2"}, "time in s")

FORMALS["OcTjHmAdk2nhPme9embPM"] = E(
    rb({"M": K("7", "kg"), "m": K("3", "kg"), "L": S("m"), "w0": S("1/s")},
       {"rod": body("rod", "M", L="L"), "b1": body("point", "m", center=("L/2", "0", "0")),
        "b2": body("point", "m", center=("-L/2", "0", "0"))},
       {"Ii": ax(["rod"], d=(0, 1, 0)), "If": ax(["rod", "b1", "b2"], d=(0, 1, 0))},
       {"w": U("1/s", "positive"), "x": U("", "positive")}, ["Ii*w0 = If*w", "x = w/w0"], "x",
       ["beads start at the centre (zero I), end at opposite ends; L conserved", "rod along x, axis along y"]),
    {"A": "7/(7+3*3)", "B": "7/(7+3)", "C": "7/(7+6*3)", "D": "7/(7+2*3)"}, "ratio w/w0 at instance M = 7, m = 3")

FORMALS["byPYPbwFgB0CXsY4IZ18hoxe66ijvzn0x28"] = E(
    rb({"M": S("kg"), "R": S("m")}, {"d": body("disc", "M", profile="r_**2", R="R")}, {"I": ax(["d"])},
       {"k": U("", "positive")}, ["I = k*M*R**2"], "k", ["sigma = k r^2 normalised to total mass M"]),
    {"A": "1/3", "B": "1/6", "C": "2/3", "D": "1/2"}, "ratio k, I = k M R^2")

FORMALS["Car9pLGRIDoZfpmHFy18hoxe66ijvzn5oc0"] = E(
    es({"I1": S("kg*m^2"), "w1": S("1/s")}, {"w": U("1/s"), "Ei": U("J"), "Ef": U("J"), "x": U("")},
       ["I1*w1 + (I1/2)*(w1/2) = (I1 + I1/2)*w", "Ei = I1*w1**2/2 + (I1/2)*(w1/2)**2/2",
        "Ef = (I1 + I1/2)*w**2/2", "x = (Ef - Ei)/(I1*w1**2)"], "x",
       ["same sense of rotation; angular momentum conserved on contact"]),
    {"A": "1/24", "B": "1/12", "C": "3/8", "D": "1/6"}, "ratio (Ef - Ei)/(I1 w1^2); options read literally")

FORMALS["lIeeCoZEUWeWBWBfNL18hoxe66ijvzncp98"] = E(
    rb({"m": K("2", "kg"), "x0": K("3", "m"), "y0": K("5", "m"), "a": K("7", "m"), "b": K("11", "m"),
        "w1": K("2", "1/s"), "w2": K("3", "1/s"), "t": K("0", "s")}, {}, {},
       {"vx": U("m/s"), "vy": U("m/s"), "ax_": U("m/s^2"), "ay": U("m/s^2"), "tz": U("N*m")},
       ["tz = (x0 + a*cos(w1*t))*m*ay - (y0 + b*sin(w2*t))*m*ax_"], "tz",
       ["F = m r''; tau_z = x F_y - y F_x at t = 0", "generic instance m=2, x0=3, y0=5, a=7, b=11, w1=2, w2=3"],
       calculus={"vx": {"derivative": "x0 + a*cos(w1*t)", "var": "t"}, "ax_": {"derivative": "vx", "var": "t"},
                 "vy": {"derivative": "y0 + b*sin(w2*t)", "var": "t"}, "ay": {"derivative": "vy", "var": "t"}}),
    {"A": "0", "B": "2*5*7*2**2", "C": "-2*(3*11*3**2 - 5*7*2**2)", "D": "2*(-3*11 + 5*7)*2**2"},
    "tau_z at a generic numeric instance; options (all along k) evaluated at the same instance")

FORMALS["z1qdq6HCwPf3AM1IfK3rsa0w2w9jwzjh440"] = E(
    rb({"M": S("kg"), "R": S("m")},
       {"disc": body("disc", "7*M/8", R="2*R"), "sph": body("solid_sphere", "M/8", R="r2")},
       {"I1": ax(["disc"]), "I2": ax(["sph"])}, {"r2": U("m", "positive"), "x": U("", "positive")},
       ["M/8 = (M/(4*pi*R**3/3))*(4*pi*r2**3/3)", "x = I1/I2"], "x",
       ["second part (M/8) recast as a sphere of the same density"]),
    {"A": "65", "B": "140", "C": "185", "D": "285"}, "ratio I1/I2")

FORMALS["n2loNcUjIP1k2lGyy23rsa0w2w9jwzk8ih4"] = E(
    rb({"m": K("2", "kg"), "t": K("2", "s"), "c1": K("2", "m/s"), "c2": K("3", "m/s^2")}, {}, {},
       {"vx": U("m/s"), "vy": U("m/s"), "Lz": U("kg*m^2/s")},
       ["Lz = m*((c1*t)*vy - (-c2*t**2)*vx)"], "Lz",
       ["L = m r x v; r = 2t i - 3t^2 j (SI)"],
       calculus={"vx": {"derivative": "c1*t", "var": "t"}, "vy": {"derivative": "-c2*t**2", "var": "t"}}),
    {"A": "36", "B": "-48", "C": "-34", "D": "0"},
    "L_z component; option C -34(k - i) has L_z = -34, option D 48(i + j) has L_z = 0")

FORMALS["VK6Sm9R4lqQmcdH1T63rsa0w2w9jx3mfm29"] = E(
    es({"m": S("kg"), "g": S("m/s^2"), "L": K("1", "m"), "l": K("0.0001", "m"), "th0": K("0.01", "rad")},
       {"v1": U("m/s", "positive"), "v2": U("m/s", "positive"), "W": U("J"), "x": U("")},
       ["v1**2 = 2*g*L*(1 - cos(th0))", "L*v1 = (L - l)*v2", "W = m*v2**2/2 - m*v1**2/2 + m*g*l", "x = W/(m*g*l)"],
       "x", ["at the lowest point standing up is internal: L about the pivot conserved (CM radius L -> L - l)",
             "work = gain in KE + m g l", "exact model at instance theta0 = 0.01 rad, l/L = 1e-4; options are the "
             "small-quantity approximations, compared with rel. tolerance 1e-6"],
       options_rounded={"rel_tol": "0.000001"}),
    {"A": "1 + 0.01**2", "B": "1", "C": "1 + 0.01**2/2", "D": "1 - 0.01**2"},
    "ratio W/(m g l) at instance; approximate options -> rounded-option match")

FORMALS["8yqzWUAQ844P7o6At6Iif"] = E(
    rb({"M": S("kg"), "R": S("m")}, {"d": body("disc", "M", profile="r_", R="R")},
       {"I": ax(["d"], point=("R", "0", "0"))}, {"a": U("", "positive")}, ["I = a*M*R**2"], "a",
       ["areal density proportional to r, total mass M; normal axis through a rim point"]),
    {"A": "1/2", "B": "3/2", "C": "8/5", "D": "3/5"}, "coefficient a")

FORMALS["0jF0u1j47RGMUIQmtSBcR"] = E(
    es({"m": S("kg"), "r": S("m"), "v": S("m/s")}, {"L": U("kg*m^2/s"), "Ar": U("m^2/s"), "x": U("")},
       ["L = m*v*r", "Ar = r*v/2", "x = Ar*m/L"], "x", ["circular orbit; areal velocity = (1/2) r v"]),
    {"A": "1", "B": "4", "C": "1/2", "D": "2"}, "ratio (dA/dt) m/L")

FORMALS["99ytypmVzB3HdMTD16VFF"] = E(
    rb({"mu": S(""), "F": S("N"), "R": S("m")}, {}, {}, {"tau": U("N*m"), "x": U("")}, ["x = tau/(mu*F*R)"], "x",
       ["uniform pressure F/(pi R^2); kinetic friction on ring r..r+dr: mu p 2 pi r dr at lever arm r"],
       calculus={"tau": {"integral": "mu*F/(pi*R**2)*2*pi*r*r", "var": "r", "lower": "0", "upper": "R"}}),
    {"A": "1/2", "B": "1/3", "C": "1/6", "D": "2/3"}, "ratio tau/(mu F R)")

FORMALS["ZOIYD1k9JaLRduLLgyo8B"] = E(
    rb({"M": S("kg"), "R": S("m"), "F": S("N")}, {"c": body("solid_cylinder", "M", R="R", L="R")}, {"I": ax(["c"])},
       {"a": U("m/s^2"), "f": U("N"), "al": U("1/s^2"), "x": U("")},
       ["F - f = M*a", "f*R = I*al", "a = al*R", "x = al*M*R/F"], "x",
       ["horizontal force applied at the axle; static friction at the contact; length irrelevant"]),
    {"A": "1/2", "B": "2/3", "C": "3/2", "D": "1/3"}, "ratio alpha M R/F (options' m = M)")

FORMALS["7IgcOr0hYSrQ4geKwMzue"] = E(
    es({"tau": K("2.5", "N*m"), "F": K("1", "N"), "r": K("5", "m")}, {"th": U("", "positive"), "c": U("", "positive")},
       ["tau = r*F*sin(th)", "c = cos(th)"], "th",
       ["|r x F| = r F sin(th); acute angle taken (all four options are acute; 5pi/6 is not offered)"]),
    {"A": "pi/8", "B": "pi/6", "C": "pi/4", "D": "pi/3"}, "angle in rad")

FORMALS["ysXBZyKjbUp7UJb3f0DUM"] = E(
    rb({"M": S("kg"), "Lc": K("30", "cm"), "Ra": K("10", "cm"), "Rb": K("20", "cm")},
       {"thick": body("thick_cylinder", "M", R1="Ra", R2="Rb", L="Lc"),
        "thin": body("hollow_cylinder", "M", R="Rt", L="Lc")},
       {"I1": ax(["thick"]), "I2": ax(["thin"])}, {"Rt": U("cm", "positive")}, ["I1 = I2"], "Rt",
       ["thin cylinder = thin-walled shell of the same mass", "options rounded"],
       options_rounded={"rel_tol": "0.03"}),
    {"A": "16", "B": "12", "C": "14", "D": "18"}, "radius in cm; rounded-option match (exact 5*sqrt(10) = 15.8)")

FORMALS["BE7hgZymN0E2d9uhFNjgy2xukf6jrqfg"] = E(
    rb({"M": S("kg"), "R": S("m"), "w1": S("1/s")},
       {"d1": body("disc", "M", R="R"), "d2": body("disc", "M", R="R/2")}, {"I1": ax(["d1"]), "I2": ax(["d2"])},
       {"w2": U("1/s", "positive"), "p": U("")},
       ["I1*w1 = (I1 + I2)*w2", "p = 100*(I1*w1**2/2 - (I1 + I2)*w2**2/2)/(I1*w1**2/2)"], "p",
       ["coaxial, angular momentum conserved; loss as % of initial KE"]), None, "numerical: p")

FORMALS["qgdOpGBjkYAFKHd8zUjgy2xukfaj3opk"] = E(
    rb({"rho": S("kg/m^3"), "R": S("m"), "t": S("m")},
       {"d1": body("solid_cylinder", density="rho", R="R", L="t"),
        "d2": body("solid_cylinder", density="rho", R="al*R", L="t")},
       {"I1": ax(["d1"]), "I2": ax(["d2"])}, {"al": U("", "positive")}, ["16*I1 = I2"], "al",
       ["same material and thickness; axis = disc axis"]),
    {"A": "sqrt(2)", "B": "2", "C": "2*sqrt(2)", "D": "4"}, "alpha")

FORMALS["uR7FEcBbUtA0FRhi44jgy2xukff3xry6"] = E(
    es({"I": S("kg*m^2"), "w": S("1/s")}, {"w2": U("1/s"), "f": U("")},
       ["I*w = (I + 3*I)*w2", "f = (I*w**2/2 - 4*I*w2**2/2)/(I*w**2/2)"], "f", ["L conserved on coupling"]),
    {"A": "0", "B": "5/6", "C": "1/4", "D": "3/4"}, "fractional KE loss")

FORMALS["60q1AvE0F7mWohQowPjgy2xukfhqolwj"] = E(
    es({"rx": K("3", "m"), "ry": K("1", "m"), "rz": K("-2", "m"), "Fx": K("1", "N"), "Fy": K("2", "N"),
        "Fz": K("3", "N"), "u": K("1", "N*m")},
       {"tx": U("N*m"), "ty": U("N*m"), "tz": U("N*m"), "x": U("", "positive")},
       ["tx = ry*Fz - rz*Fy", "ty = rz*Fx - rx*Fz", "tz = rx*Fy - ry*Fx", "x*u**2 = tx**2 + ty**2 + tz**2"], "x",
       ["r = (4,3,-1) - (1,2,1) = (3,1,-2); |tau| = sqrt(x) N m"]), None, "numerical: x")

FORMALS["zT4AYz1QoP2zM4t8cfjgy2xukfl1siq0"] = E(
    rb({"M": S("kg"), "R": S("m"), "g": S("m/s^2")}, {"ring": body("ring", "M", R="R")},
       {"I1": ax(["ring"], point=("0", "R", "0"), d=(0, 0, 1)), "I2": ax(["ring"], point=("0", "R", "0"), d=(1, 0, 0))},
       {"T1": U("s", "positive"), "T2": U("s", "positive"), "x": U("", "positive")},
       ["T1**2*M*g*R = 4*pi**2*I1", "T2**2*M*g*R = 4*pi**2*I2", "x = T1/T2"], "x",
       ["physical pendulum T = 2 pi sqrt(I/(M g d)), d = R", "(i) axis normal to the plane at the nail; "
        "(ii) axis in the plane, tangent to the ring at the nail"]),
    {"A": "sqrt(2)/3", "B": "2/sqrt(3)", "C": "2/3", "D": "3/sqrt(2)"}, "ratio T1/T2")

FORMALS["VNPKX8Peju0Jhnpzopjgy2xukg0bmoa7"] = E(
    rb({"M": S("kg"), "L": S("m")}, {"rod": body("rod", "M", profile="1 + (s_ + L/2)/L", u=(1, 0, 0), L="L")},
       {"I": ax(["rod"], point=("-L/2", "0", "0"))}, {"k": U("", "positive")}, ["I = k*M*L**2"], "k",
       ["lambda = lambda0 (1 + x/L), x from A; A at s = -L/2; total mass M"]),
    {"A": "2/5", "B": "5/12", "C": "7/18", "D": "3/7"}, "ratio k, I = k M L^2")

FORMALS["WSwHvNT1JkSyc3iWsGjgy2xukf14dc5f"] = E(
    rb({"M": S("kg"), "V": S("m^3")}, {"c": body("solid_cylinder", "M", R="R", L="L")}, {"I": ax(["c"], d=(1, 0, 0))},
       {"L": U("m", "positive"), "R": U("m", "positive"), "dI": U("kg*m"), "d2I": U("kg", "positive"),
        "x": U("", "positive")},
       ["dI = 0", "V = pi*R**2*L", "x = L/R"], "x",
       ["given mass of material -> fixed volume", "dI/dL = 0 with d2I/dL2 > 0 (minimum)",
        "engine's I equals the stem's M(R^2/4 + L^2/12)"],
       calculus={"dI": {"derivative": "I", "var": "L", "subs": {"R": "sqrt(V/(pi*L))"}},
                 "d2I": {"derivative": "dI", "var": "L"}}),
    {"A": "3/2", "B": "sqrt(3/2)", "C": "sqrt(2/3)", "D": "2/3"}, "ratio L/R at the minimum")

FORMALS["2p0E2TIZzrOYy5YhX67k9k2k5djt7ib"] = E(
    rb({"m": S("kg"), "l": S("m")}, {"rod": body("rod", "m", u=(1, 0, 0), L="l")},
       {"I": ax(["rod"], point=("l/4", "0", "0"))}, {"kg": U("m", "positive"), "x": U("", "positive")},
       ["I = m*kg**2", "x = kg/l"], "x", ["axis perpendicular to the rod at l/4 from the centre"]),
    {"A": "1/8", "B": "1/4", "C": "sqrt(7/48)", "D": "sqrt(3/8)"}, "ratio k/l")

# ============================================================== chunk 3 (questions 51-75)
FORMALS["mmd27YeQWLKUu4xQ2u7k9k2k5f5eapa"] = E(
    rb({"A": K("1", "kg/m^2"), "B": K("2", "kg/m^3"), "a": K("3", "m")},
       {"d": body("disc", density="A + B*r_", R="a")}, {"I": ax(["d"])}, {}, [], "I",
       ["absolute areal density A + B r", "generic instance A = 1 kg/m^2, B = 2 kg/m^3, a = 3 m"]),
    {"A": "2*pi*3**4*(1/4 + 3*2/5)", "B": "pi*3**4*(1/4 + 3*2/5)", "C": "2*pi*3**4*(3*1/4 + 2/5)",
     "D": "2*pi*3**4*(1/4 + 2/5)"}, "I in kg m^2 at a generic instance; options evaluated at the same instance")

FORMALS["xgguUJAR2MMkuQ4aev7k9k2k5gveqgd"] = E(
    rb({"m": S("kg"), "l": S("m"), "v": S("m/s"), "th": K("pi/4", "rad")},
       {"rod": body("rod", "4*m", u=(1, 0, 0), L="l"), "p": body("point", "m", center=("l/2", "0", "0"))},
       {"I": ax(["rod", "p"])}, {"w": U("1/s"), "x": U("")},
       ["m*v*sin(th)*(l/2) = I*w", "x = w*l/v"], "x",
       ["angular momentum about the pivot conserved (pivot force has no torque)",
        "lever arm of the incoming momentum = (l/2) sin(th)"]),
    {"A": "3*sqrt(2)/7", "B": "3/7", "C": "3/(7*sqrt(2))", "D": "4/7"}, "ratio w l/v")

FORMALS["9jCyQhEAs6eWjkTr4Q7k9k2k5hhldlt"] = E(
    rb({"M": K("500", "g"), "R": S("m"), "v": K("5.00", "cm/s")}, {"s": body("solid_sphere", "M", R="R")},
       {"I": ax(["s"])}, {"KE": U("J")}, [], "KE", ["rolling without slipping: KE = M v^2/2 + I (v/R)^2/2"],
       relations=[{"template": "rolling_ke", "KE": "KE", "M": "M", "I": "I", "R": "R", "v": "v"}]),
    {"A": "8.75*10**-3", "B": "1.13*10**-3", "C": "8.75*10**-4", "D": "6.25*10**-4"}, "KE in J")

FORMALS["hdFSrrJ2kxtBiY45N57k9k2k5iodr83"] = E(
    es({"m": K("10", "kg"), "L": K("0.3", "m"), "sig": K("4.8*10**7", "N/m^2"), "A": K("10**-2", "cm^2")},
       {"w": U("1/s", "positive")}, ["sig*A = m*w**2*L"], "w",
       ["space station: no gravity, tension alone gives the centripetal force; wire mass neglected"]),
    None, "numerical: w in rad/s")

FORMALS["Z1v8NC8U95YrjXGxT6jgy2xukexxod6m"] = E(
    es({"I1": K("0.1", "kg*m^2"), "w1": K("10", "1/s"), "I2": K("0.2", "kg*m^2"), "w2": K("5", "1/s")},
       {"w": U("1/s"), "KE": U("J")}, ["I1*w1 + I2*w2 = (I1 + I2)*w", "KE = (I1 + I2)*w**2/2"], "KE",
       ["same sense; L conserved when stuck"]),
    {"A": "20/3", "B": "5/3", "C": "10/3", "D": "2/3"}, "KE in J")

FORMALS["bEtWbedAMiaQUiRiUYjgy2xukf258opx"] = E(
    rb({"mp": K("80", "kg"), "Mp": K("200", "kg"), "R": S("m"), "w1": K("5", "rpm")},
       {"plat": body("disc", "Mp", R="R"), "man": body("point", "mp", center=("R", "0", "0")),
        "man0": body("point", "mp")},
       {"Ii": ax(["plat", "man"]), "If": ax(["plat", "man0"])}, {"w2": U("rpm", "positive")},
       ["Ii*w1 = If*w2"], "w2", ["platform = uniform disc; person = point mass; L conserved"]),
    None, "numerical: rpm")


def _four(target, extra=()):
    return rb({"M": S("kg"), "R": S("m"), "Lc": S("m")},
              {"ring": body("ring", "M", R="R"), "disc": body("disc", "M", R="R"),
               "cyl": body("solid_cylinder", "M", R="R", L="Lc"), "sph": body("solid_sphere", "M", R="R")},
              {"I1": ax(["ring"], d=(1, 0, 0)), "I2": ax(["disc"]), "I3": ax(["cyl"]), "I4": ax(["sph"])},
              {"y": U("")}, list(extra) + [target], "y", ["same mass M and radius R"])


FORMALS["D69V8gdvhXmgTfrdPW1klrifuhg"] = E(sel({
    "A": T(_four("y = I3/I4", ["I1 = I2", "I2 = I3"]), "> 1"),
    "B": T(_four("y = ((I2 + I4) - (I1 + I3))/(M*R**2)"), "> 0"),
    "C": T(_four("y = I3/I4"), "< 1"),
    "D": T(_four("y = ((I1 + I2) - (I3 + 5*I4/2))/(M*R**2)"), "== 0")}), ONE,
    "A: equalities imposed as equations (exact solve succeeds only if they hold) then I3/I4 > 1; option k <-> {k}")

_hx = [("1", "0"), ("1/2", "sqrt(3)/2"), ("-1/2", "sqrt(3)/2"), ("-1", "0"), ("-1/2", "-sqrt(3)/2"), ("1/2", "-sqrt(3)/2")]
FORMALS["umi1KK6mmaGVfwcv5z1klrp546p"] = E(
    rb({"M": K("6", "kg"), "Lt": K("2.4", "m"), "u": K("0.1", "kg*m^2")},
       {f"s{i}": body("rod", "M/6", center=(f"({c})*sqrt(3)/2*Lt/6", f"({sn})*sqrt(3)/2*Lt/6", "0"),
                      u=(f"-({sn})", c, "0"), L="Lt/6") for i, (c, sn) in enumerate(_hx)},
       {"I": ax([f"s{i}" for i in range(6)])}, {"x": U("")}, ["I = x*u"], "x",
       ["regular hexagon of side Lt/6; each side's midpoint at the apothem (sqrt(3)/2) side"]),
    None, "numerical: I in units of 1e-1 kg m^2")

FORMALS["LF4awbZatQIQqlimkF1klthd0p0"] = E(
    rb({"m": S("kg"), "a": K("2", "m"), "b": K("3", "m"), "u": K("1", "m")},
       {f"s{i}": body("solid_sphere", "m", center=c, R="a")
        for i, c in enumerate([("0", "0", "0"), ("b", "0", "0"), ("0", "b", "0"), ("b", "b", "0")])},
       {"I": ax(["s0", "s1", "s2", "s3"], d=(1, 0, 0))}, {"x": U("")}, ["I = x*m*u**2"], "x",
       ["axis along the side through s0, s1 (x-axis)", "generic instance a = 2 m, b = 3 m"]),
    {"A": "4/5*2**2", "B": "8/5*2**2 + 3**2", "C": "4/5*2**2 + 2*3**2", "D": "8/5*2**2 + 2*3**2"},
    "ratio I/(m * 1 m^2) at instance a = 2, b = 3; options at the same instance")

FORMALS["WuHXW7gUgdMYj1BN9V1kluncx9i"] = E(
    es({"m": K("2", "kg"), "g": K("10", "m/s^2"), "h": K("3", "m"), "I": K("5", "kg*m^2"), "r": K("0.5", "m")},
       {"w": U("1/s", "positive"), "w2": U("1/s^2")},
       ["m*g*h = m*(w*r)**2/2 + I*w**2/2", "w2 = w**2"], "w2",
       ["energy conservation; cord does not slip (v = w r)", "instance m=2, g=10, h=3, I=5, r=0.5"]),
    {"A": "2*2*10*3/(5 + 2*2*0.5**2)", "B": "2*2*10*3/(5 + 2*0.5**2)", "C": "-1", "D": "-2"},
    "w^2 in 1/s^2 at instance; C (2gh) and D (2gh/(I+mr^2)) are dimensionally wrong -> distinct sentinels -1, -2")

FORMALS["EBY84tAudUadnrGYPm1kmiq73xb"] = E(
    es({"rx": K("0", "m"), "ry": K("-3", "m"), "rz": K("-4", "m"), "Fx": K("4", "N"), "Fy": K("3", "N"),
        "Fz": K("4", "N")},
       {"tx": U("N*m"), "ty": U("N*m"), "tz": U("N*m"), "t": U("N*m", "positive")},
       ["tx = ry*Fz - rz*Fy", "ty = rz*Fx - rx*Fz", "tz = rx*Fy - ry*Fx", "t**2 = tx**2 + ty**2 + tz**2"], "t",
       ["point of application (2,0,0); r = (2,0,0) - (2,3,4)"]), None, "numerical: |tau| in N m")

FORMALS["16kFcexlMjLkKgTlXA1kmj3ys5s"] = E(
    es({"w1": K("900", "rpm"), "w2": K("2460", "rpm"), "t": K("26", "s"), "rev": K("2*pi", "rad")},
       {"al": U("1/s^2"), "th": U(""), "n": U("")},
       ["w2 = w1 + al*t", "th = w1*t + al*t**2/2", "n = th/rev"], "n",
       ["uniform angular acceleration; engine revolutions taken equal to the wheel's"]), None, "numerical: revolutions")

FORMALS["IerYEirovFn3oJiZwY1kmkr269n"] = E(
    rb({"M": K("7", "kg"), "m": K("3", "kg"), "r": S("m"), "w": S("1/s")},
       {"g": body("ring", "M", R="r"), "p1": body("point", "m", center=("r", "0", "0")),
        "p2": body("point", "m", center=("-r", "0", "0"))},
       {"Ii": ax(["g"]), "If": ax(["g", "p1", "p2"])}, {"w2": U("1/s", "positive"), "x": U("", "positive")},
       ["Ii*w = If*w2", "x = w2/w"], "x", ["L conserved"]),
    {"A": "7/(7+3)", "B": "(7+2*3)/7", "C": "7/(7+2*3)", "D": "(7-2*3)/(7+2*3)"}, "ratio at instance M = 7, m = 3")

FORMALS["GggYuVILuLH4LnAfDQ1kmlvtyoe"] = E(
    rb({"M": S("kg"), "L": S("m")}, {"w": body("semi_ring", "M", R="R")}, {"I": ax(["w"])},
       {"R": U("m", "positive"), "k": U("", "positive")}, ["L = pi*R", "I = k*M*L**2/pi**2"], "k",
       ["semicircle of arc length L: R = L/pi; axis normal through the centre"]),
    {"A": "1/4", "B": "1/2", "C": "2/5", "D": "1"}, "ratio k, I = k M L^2/pi^2")

FORMALS["1krpq8sv4"] = E(
    rb({"M": S("kg"), "R": S("m"), "g": S("m/s^2"), "th": K("30", "degree"), "L": S("m")},
       {"d": body("disc", "M", R="R")}, {"I": ax(["d"])},
       {"a2": U("m/s^2"), "a1": U("m/s^2"), "t1": U("s", "positive"), "t2": U("s", "positive"), "x": U("", "positive")},
       ["M*a1 = M*g*sin(th)", "L = a1*t1**2/2", "L = a2*t2**2/2", "t2**2*x = 3*t1**2"], "x",
       ["slipping = frictionless sliding; rolling: template rolling_incline", "from rest; angle instance 30 deg"],
       relations=[{"template": "rolling_incline", "a": "a2", "M": "M", "I": "I", "R": "R", "g": "g", "th": "th"}]),
    None, "numerical: x")


def _ke_ratio(shape, dims):
    return rb({"M": S("kg"), "R": S("m"), "v": S("m/s")}, {"b": body(shape, "M", **dims)}, {"I": ax(["b"])},
              {"KEt": U("J"), "KEr": U("J"), "y": U("")}, ["y = KEr/KEt"], "y", ["rolling without slipping"],
              relations=[{"template": "rolling_ke", "KEt": "KEt", "KEr": "KEr", "M": "M", "I": "I", "R": "R", "v": "v"}])


FORMALS["1krqchuow"] = E(sel({
    "A": T(_ke_ratio("solid_sphere", {"R": "R"}), "== 1/2"),
    "B": T(_ke_ratio("solid_cylinder", {"R": "R", "L": "R"}), "== 1/2"),
    "C": T(_ke_ratio("hollow_cylinder", {"R": "R", "L": "R"}), "== 1/2"),
    "D": T(_ke_ratio("ring", {"R": "R"}), "== 1/2")}), ONE, "computed KE_rot/KE_trans == 1/2 per body")

FORMALS["1krqf0jpc"] = E(
    rb({"m1": S("kg"), "m2": S("kg"), "R": S("m"), "g": S("m/s^2"), "h": S("m")},
       {"ring": body("ring", "m1", R="R"), "cyl": body("solid_cylinder", "m2", R="R", L="R")},
       {"I1": ax(["ring"]), "I2": ax(["cyl"])},
       {"v1": U("m/s", "positive"), "v2": U("m/s", "positive"), "x": U("", "positive")},
       ["m1*g*h = m1*v1**2/2 + I1*(v1/R)**2/2", "m2*g*h = m2*v2**2/2 + I2*(v2/R)**2/2", "4*v1**2 = x*v2**2"], "x",
       ["energy conservation, rolling from rest through the same height"]), None, "numerical: x")

FORMALS["1krqfvxc1"] = E(
    es({"w1": K("600", "rpm"), "w2": K("1800", "rpm"), "t": K("10", "s"), "rev": K("2*pi", "rad")},
       {"al": U("1/s^2"), "th": U(""), "n": U("")},
       ["w2 = w1 + al*t", "th = w1*t + al*t**2/2", "n = th/rev"], "n", ["uniform angular acceleration"]),
    None, "numerical: rotations")


def _race(target, extra_unknowns=None, extra_eqs=()):
    # q* = v*^2 (speeds are positive, so ordering of q equals ordering of v)
    return rb({"m1": S("kg"), "m2": S("kg"), "m3": S("kg"), "R": S("m"), "g": S("m/s^2"), "h": S("m")},
              {"ring": body("ring", "m1", R="R"), "cyl": body("solid_cylinder", "m2", R="R", L="R"),
               "sph": body("solid_sphere", "m3", R="R")},
              {"I1": ax(["ring"]), "I2": ax(["cyl"]), "I3": ax(["sph"])},
              {"qr": U("m^2/s^2", "positive"), "qc": U("m^2/s^2", "positive"), "qs": U("m^2/s^2", "positive"),
               **(extra_unknowns or {}), "y": U("")},
              ["m1*g*h = m1*qr/2 + I1*qr/R**2/2", "m2*g*h = m2*qc/2 + I2*qc/R**2/2",
               "m3*g*h = m3*qs/2 + I3*qs/R**2/2", *extra_eqs, target], "y",
              ["energy conservation, rolling from rest, same height; q = v^2 (v > 0, so order of q = order of v)"])


FORMALS["1krsu72qd"] = E(sel({
    "A": T(_race("y = qr/qs"), "== 1"),
    "B": T(_race("y = qr/qs"), "> 1"),
    "C": T(_race("y = d1/d2", {"d1": U("m^2/s^2", "positive"), "d2": U("m^2/s^2", "positive")},
                 ["d1 = qs - qc", "d2 = qc - qr"]), "> 0"),
    "D": T(_race("y = qc/qs"), "> 1")}), ONE,
    "A: all equal; B needs ring > sphere; D needs cylinder > sphere; C: d1 = vs^2 - vc^2 and d2 = vc^2 - vr^2 "
    "declared positive (no admissible solution otherwise)")

FORMALS["1krsy2kia"] = E(
    es({"v0": S("m/s"), "R": S("m")}, {"w": U("1/s"), "vx": U("m/s"), "vy": U("m/s"), "x": U("", "positive")},
       ["v0 = w*R", "vx = v0", "vy = w*R", "x*v0**2 = vx**2 + vy**2"], "x",
       ["rolling without slipping: v = v_cm + w x r; at the rim point level with the centre, w x r is vertical"]),
    None, "numerical: x")

FORMALS["1krudvskt"] = E({
    "kind": "statement_set", "format": "assertion_reason",
    "statements": {
        "A": T(rb({"M": S("kg"), "R": S("m")}, {"d": body("disc", "M", R="R")},
                  {"Ix": ax(["d"], d=(1, 0, 0)), "Iz": ax(["d"])}, {"y": U("")}, ["y = Ix/Iz"], "y",
                  ["same mass: k_x = k_z iff I_x = I_z"]), "== 1"),
        "R": C(True, "definition of a rigid body (fixed mass and shape)")},
    "explains": C(False, "A is false; R does not establish it")},
    {"A": "2", "B": "4", "C": "1", "D": "3"}, "assertion_reason codes: 3 explains, 2 both true, 1 A only, 4 R only")

FORMALS["1krunysm5"] = E(
    rb({"m": S("kg"), "al": S("m/s^2"), "be": S("m/s"), "t0": K("0", "s"), "c5": K("5", "s")}, {}, {},
       {"t": U("s", "positive"), "vx": U("m/s"), "vy": U("m/s"), "vx0": U("m/s"), "vy0": U("m/s")},
       ["m*((10*al*t**2)*vy - (5*be*(t - c5))*vx) = m*((10*al*t0**2)*vy0 - (5*be*(t0 - c5))*vx0)"], "t",
       ["L_z = m (x v_y - y v_x)"],
       calculus={"vx": {"derivative": "10*al*t**2", "var": "t"}, "vy": {"derivative": "5*be*(t - c5)", "var": "t"},
                 "vx0": {"derivative": "10*al*t0**2", "var": "t0"},
                 "vy0": {"derivative": "5*be*(t0 - c5)", "var": "t0"}}),
    None, "numerical: t in s (t > 0)")

FORMALS["1krwcrwzr"] = E(
    rb({"M": K("10", "kg"), "R": K("20", "cm"), "w0": K("600", "rpm"), "t": K("10", "s"), "u": K("0.1*pi", "N*m")},
       {"d": body("disc", "M", R="R")}, {"I": ax(["d"])}, {"tau": U("N*m"), "x": U("")},
       ["I*w0 = tau*t", "tau = x*u"], "x", ["uniform retardation to rest"]), None, "numerical: tau in pi*1e-1 N m")


def _rod(mass, length, at_end):
    return rb({"M": S("kg"), "L": S("m")},
              {"r": body("rod", mass, u=(1, 0, 0), L=length)},
              {"I": ax(["r"], point=(f"({length})/2" if at_end else "0", "0", "0"))}, {"y": U("")},
              ["I = y*M*L**2"], "y", [])


FORMALS["1krytnal1"] = E({
    "kind": "statement_set", "format": "match_list",
    "pairs": {"a": ["III", T(_rod("M", "L", False), "== 1/12")], "b": ["IV", T(_rod("2*M", "L", True), "== 2/3")],
              "c": ["II", T(_rod("M", "2*L", False), "== 1/3")], "d": ["I", T(_rod("2*M", "2*L", True), "== 8/3")]}},
    {"A": "2314", "B": "2134", "C": "3421", "D": "3412"}, "match_list code = List-II index per (a)..(d)")

FORMALS["1kte0gtvo"] = E(
    rb({"M": S("kg"), "l": S("m")}, {"p": body("rect_plate", "M", a="l", b="l")},
       {"I": ax(["p"], point=("l/2", "l/2", "0"))}, {"k": U("", "positive")}, ["I = k*M*l**2"], "k",
       ["normal axis through a corner"]),
    {"A": "1/6", "B": "1", "C": "1/12", "D": "2/3"}, "ratio k")

# ============================================================== chunk 4 (questions 76-100)
FORMALS["1ktfjwrjv"] = E(
    es({"I1": K("2", "kg*m^2"), "I2": K("3", "kg*m^2"), "w1": K("5", "1/s"), "w2": K("1", "1/s")},
       {"w": U("1/s"), "dK": U("J")},
       ["I1*w1 + I2*w2 = (I1 + I2)*w", "dK = I1*w1**2/2 + I2*w2**2/2 - (I1 + I2)*w**2/2"], "dK",
       ["same sense of rotation; L conserved", "generic instance I1=2, I2=3, w1=5, w2=1 (SI)"]),
    {"A": "2*3*(5-1)**2/(2+3)", "B": "(2-3)**2*5*1/(2*(2+3))", "C": "2*3*(5-1)**2/(2*(2+3))", "D": "-1"},
    "KE loss in J at instance; option D ((w1-w2)^2/(2(I1+I2))) is not an energy -> -1")

FORMALS["1kth5aj8v"] = E(sel({
    "A": C(False), "B": C(True, "about the centre: L = m v R along the fixed normal; constant"),
    "C": C(False, "true only about a point off the plane's centre; standard reading is about the centre"),
    "D": C(False)}), ONE, "curated conceptual (angular momentum about the centre of the circle)")

FORMALS["1ktjn2zdu"] = E(
    rb({"m": K("1.5", "kg"), "r": K("50", "cm"), "d": K("5", "m")},
       {"s1": body("solid_sphere", "m", center=("d/2", "0", "0"), R="r"),
        "s2": body("solid_sphere", "m", center=("-d/2", "0", "0"), R="r")},
       {"I": ax(["s1", "s2"], d=(0, 0, 1))}, {}, [], "I", ["light rod; axis perpendicular to the rod at its midpoint"]),
    {"A": "18.75", "B": "1.905*10**5", "C": "19.05", "D": "1.875*10**5"}, "I in kg m^2")

FORMALS["1ktmwpjl2"] = E(
    rb({"m": K("2", "kg"), "L": K("0.6", "m"), "g": K("10", "m/s^2")},
       {"r": body("rod", "m", center=("0", "L/2", "0"), u=(0, 1, 0), L="L")}, {"I": ax(["r"])},
       {"w": U("1/s", "positive"), "v": U("m/s", "positive")}, ["I*w**2/2 = m*g*L", "v = w*L"], "v",
       ["starts vertical (upright) essentially from rest, hinged at the lower end; lowest position = hanging "
        "vertically down: CM falls by L"]), None, "numerical: free-end speed m/s")

FORMALS["1l54vvmmr"] = E(
    rb({"M": S("kg"), "L": S("m")},
       {"rod": body("rod", "M", u=(1, 0, 0), L="L"), "ring": body("ring", "M", R="L/(2*pi)")},
       {"I1": ax(["rod"], point=("L/2", "0", "0")), "I2": ax(["ring"], d=(1, 0, 0))}, {"x": U("")},
       ["3*I1 = x*pi**2*I2"], "x", ["ring circumference = rod length"]), None, "numerical: x")

FORMALS["1l55joigw"] = E(
    rb({"c6": K("6", "1/s^4"), "c2": K("2", "1/s^3"), "w0": K("10", "1/s"), "th0": K("4", "rad"), "T": K("2", "s")},
       {}, {}, {"th": U(""), "J": U("")},
       ["th = th0 + w0*T + J"], "th",
       ["theta(T) = theta0 + w0 T + int_0^T (T - t) alpha(t) dt", "options compared at instance t = 2 s"],
       calculus={"J": {"integral": "(T - t)*(c6*t**2 - c2*t)", "var": "t", "lower": "0", "upper": "T"}}),
    {"A": "3*2**4/2 - 2**2 + 10*2", "B": "2**4/2 - 2**3/3 + 10*2 + 4", "C": "2*2**4/3 - 2**3/6 + 10*2 + 12",
     "D": "2*2**4 - 2**3/2 + 5*2 + 4"}, "theta (rad) at instance t = 2 s; each option's expression evaluated there")


def _tan(shape, coef):
    return rb({"M": S("kg"), "R": S("m")}, {"b": body(shape, "M", R="R")},
              {"I": ax(["b"], point=("R", "0", "0"), d=(0, 1, 0) if shape not in ("ring", "disc") else (1, 0, 0))},
              {"y": U("")}, ["I = y*M*R**2"], "y", [])


FORMALS["1l568o323"] = E({
    "kind": "statement_set", "format": "match_list",
    "pairs": {"A": ["II", T(_tan("solid_sphere", 0), "== 7/5")], "B": ["I", T(_tan("spherical_shell", 0), "== 5/3")],
              "C": ["IV", T(rb({"M": S("kg"), "R": S("m")}, {"b": body("ring", "M", R="R")},
                                {"I": ax(["b"], d=(1, 0, 0))}, {"y": U("")}, ["I = y*M*R**2"], "y"), "== 1/2")],
              "D": ["III", T(rb({"M": S("kg"), "R": S("m")}, {"b": body("disc", "M", R="R")},
                                 {"I": ax(["b"], d=(1, 0, 0))}, {"y": U("")}, ["I = y*M*R**2"], "y"), "== 1/4")]}},
    {"A": "2143", "B": "1243", "C": "2134", "D": "1234"}, "match_list code; tangent = axis touching the sphere")

FORMALS["1l56a962e"] = E(
    es({"m": K("1", "kg"), "rx": K("3", "m"), "ry": K("-1", "m"), "rz": K("0", "m"), "vx": K("0", "m/s"),
        "vy": K("3", "m/s"), "vz": K("1", "m/s"), "u": K("1", "kg*m^2/s")},
       {"Lx": U("kg*m^2/s"), "Ly": U("kg*m^2/s"), "Lz": U("kg*m^2/s"), "x": U("", "positive")},
       ["Lx = m*(ry*vz - rz*vy)", "Ly = m*(rz*vx - rx*vz)", "Lz = m*(rx*vy - ry*vx)", "x*u**2 = Lx**2 + Ly**2 + Lz**2"],
       "x", ["L = m r x v"]), None, "numerical: x (|L| = sqrt(x))")

FORMALS["1l56uiw7b"] = E(
    es({"m": K("1", "kg"), "w": K("2", "1/s"), "l0": K("3", "m"), "k": K("10", "N/m")},
       {"x": U("m", "positive")}, ["k*x = m*w**2*(l0 + x)"], "x",
       ["spring force provides the centripetal force at radius l0 + x", "generic instance m=1, w=2, l0=3, k=10"]),
    {"A": "-1", "B": "1*2**2*3/(10 + 1*2**2)", "C": "1*2**2*3/(10 - 1*2**2)", "D": "-2"},
    "elongation (m) at instance; A and D add k to m w^2 l0 (dimensionally wrong) -> sentinels -1, -2")

FORMALS["1l58bgm1n"] = E(
    rb({"M": K("7", "kg"), "m": K("3", "kg"), "R": S("m"), "w": K("2", "1/s")},
       {"g": body("ring", "M", R="R"), "p1": body("point", "m", center=("R", "0", "0")),
        "p2": body("point", "m", center=("-R", "0", "0"))},
       {"Ii": ax(["g"]), "If": ax(["g", "p1", "p2"])}, {"w2": U("1/s", "positive")}, ["Ii*w = If*w2"], "w2",
       ["L conserved"]),
    {"A": "7/(7+3)", "B": "(7+2*3)/(2*7)", "C": "2*7/(7+2*3)", "D": "2*(7+2*3)/7"}, "w' (rad/s) at instance M = 7, m = 3")

FORMALS["1l58hgpl0"] = E(
    rb({"M": S("kg"), "R": S("m"), "v": S("m/s")}, {"b": body("solid_sphere", "M", R="R")}, {"I": ax(["b"])},
       {"KE": U("J"), "KEr": U("J"), "y": U("")}, ["y = KEr/KE"], "y", ["rolling: w = v/R"],
       relations=[{"template": "rolling_ke", "KE": "KE", "KEr": "KEr", "M": "M", "I": "I", "R": "R", "v": "v"}]),
    {"A": "2/5", "B": "2/7", "C": "1/5", "D": "7/10"}, "ratio KE_rot/KE_total")

FORMALS["1l59pv08s"] = E(
    rb({"M": S("kg"), "R": S("m")},
       {"s": body("solid_sphere", "M", R="2*R"), "c": body("solid_cylinder", "M", R="2*R", L="R"),
        "d": body("disc", "M", R="2*R"), "r": body("ring", "M", R="2*R")},
       {"I1": ax(["s"]), "I2": ax(["c"]), "I3": ax(["d"], d=(1, 0, 0)), "I4": ax(["r"], d=(1, 0, 0))},
       {"x": U("")}, ["2*(I2 + I3) + I4 = x*I1"], "x", ["cylinder about its own axis (length irrelevant)"]),
    None, "numerical: x")

FORMALS["1l5ak88g7"] = E(
    es({"rx": K("2", "m"), "ry": K("1", "m"), "rz": K("2", "m"), "Fx": K("3", "N"), "Fy": K("4", "N"),
        "Fz": K("-2", "N")},
       {"tx": U("N*m"), "ty": U("N*m"), "tz": U("N*m"), "z": U("N*m")},
       ["tx = ry*Fz - rz*Fy", "ty = rz*Fx - rx*Fz", "tz = rx*Fy - ry*Fx", "z = tx + sqrt(2)*ty + sqrt(3)*tz"], "z",
       ["tau = r x F"]),
    {"A": "3 + 4*sqrt(2) - 2*sqrt(3)", "B": "-10 + 10*sqrt(2) + 5*sqrt(3)", "C": "10 + 5*sqrt(2) - 10*sqrt(3)",
     "D": "10 + sqrt(2) - 5*sqrt(3)"}, "vector encoded injectively as tx + sqrt2 ty + sqrt3 tz (rational components)")

FORMALS["1l5c4u6zp"] = E(
    es({"m": K("20", "g"), "x1": K("10", "cm"), "xp": K("40", "cm"), "xc": K("50", "cm"), "u": K("10**-2", "kg")},
       {"M": U("kg", "positive"), "x": U("")}, ["m*(xp - x1) = M*(xc - xp)", "M = x*u"], "x",
       ["uniform scale: weight at the 50 cm mark; torques about the 40 cm knife edge"]), None, "numerical: x")

FORMALS["1l6dxzpz1"] = E(
    rb({"M": S("kg"), "R": S("m"), "g": S("m/s^2"), "h": S("m")},
       {"c": body("solid_cylinder", "M", R="R", L="R"), "s": body("solid_sphere", "M", R="R")},
       {"Ic": ax(["c"]), "Is": ax(["s"])},
       {"vc": U("m/s", "positive"), "vs": U("m/s", "positive"), "x": U("", "positive")},
       ["M*g*h = M*vc**2/2 + Ic*(vc/R)**2/2", "M*g*h = M*vs**2/2 + Is*(vs/R)**2/2", "x = vc/vs"], "x",
       ["rolling from rest through the same height"]),
    {"A": "sqrt(5/3)", "B": "sqrt(4/5)", "C": "sqrt(3/5)", "D": "sqrt(14/15)"}, "ratio v_cyl/v_sph")

FORMALS["1l6gnhwwx"] = E(
    rb({"M": K("1", "kg"), "m": K("1", "kg"), "R": S("m"), "g": K("10", "m/s^2")},
       {"d": body("disc", "M", R="R"), "p": body("point", "m", center=("0", "R", "0"))},
       {"I": ax(["d", "p"], point=("0", "0", "0"))},
       {"w": U("1/s", "positive"), "x": U("m/s^2", "positive")},
       ["m*g*(2*R) = I*w**2/2", "w**2 = 16*x/(3*R)"], "x",
       ["fixed horizontal axis through the centre; point mass falls 2R; I of disc + point at radius R "
        "(same for top and bottom positions)", "x carries units m/s^2 (stem's numbers are SI)"]),
    None, "numerical: x")

FORMALS["1l6i21mj2"] = E(
    rb({"M": S("kg"), "L": K("10*sqrt(3)", "m")}, {"r": body("rod", "M", u=(1, 0, 0), L="L")},
       {"I": ax(["r"])}, {"k": U("m", "positive")}, ["I = M*k**2"], "k",
       ["thin rod (radius not given: negligible)"]), None, "numerical: k in m")

FORMALS["1l6jk2emh"] = E(
    _pulley("y = n*pi", c1="12", c2="3", R="1.5", I="4.5"), None, "numerical: K = n pi")

FORMALS["1l6rhk51x"] = E(
    es({"rx": K("2", "m"), "ry": K("2", "m"), "rz": K("1", "m"), "Fx": K("5", "N"), "Fy": K("3", "N"),
        "Fz": K("-7", "N")},
       {"tx": U("N*m"), "ty": U("N*m"), "tz": U("N*m"), "z": U("N*m")},
       ["tx = ry*Fz - rz*Fy", "ty = rz*Fx - rx*Fz", "tz = rx*Fy - ry*Fx", "z = tx + sqrt(2)*ty + sqrt(3)*tz"], "z",
       ["tau = r x F"]),
    {"A": "11 + 19*sqrt(2) - 4*sqrt(3)", "B": "-11 + 9*sqrt(2) - 16*sqrt(3)", "C": "-17 + 19*sqrt(2) - 4*sqrt(3)",
     "D": "17 + 9*sqrt(2) + 16*sqrt(3)"}, "vector encoded injectively as tx + sqrt2 ty + sqrt3 tz")

FORMALS["1ldnz6bcx"] = E(
    rb({"M": S("kg"), "R": S("m")}, {"d": body("disc", "M", R="R")}, {"I": ax(["d"], point=("R", "0", "0"))},
       {"x": U("")}, ["I = x*M*R**2/2"], "x", ["normal axis through a rim point"]), None, "numerical: x")

FORMALS["ldo7la9t"] = E(
    rb({"M": S("kg"), "rho": S("kg/m^3"), "t1": K("1", "cm"), "t2": K("0.5", "cm")},
       {"d1": body("disc", density="3*rho*t1", R="R1"), "d2": body("disc", density="5*rho*t2", R="R2")},
       {"I1": ax(["d1"], d=(1, 0, 0)), "I2": ax(["d2"], d=(1, 0, 0))}, {"R1": U("m", "positive"),
                                                                       "R2": U("m", "positive"), "x": U("")},
       ["M = 3*rho*t1*pi*R1**2", "M = 5*rho*t2*pi*R2**2", "6*I1 = x*I2"], "x",
       ["thin discs (laminae, I about a diameter = M R^2/4) with areal density rho * thickness",
        "densities 3:5 for thickness 1 cm : 0.5 cm"]), None, "numerical: x")

FORMALS["1ldpmwopd"] = E(
    rb({"M": K("1", "kg"), "R": S("m"), "KE": K("7*10**-3", "J")}, {"s": body("solid_sphere", "M", R="R")},
       {"I": ax(["s"])}, {"v": U("cm/s", "positive"), "KE2": U("J")}, ["KE2 = KE"], "v", ["rolling without slipping"],
       relations=[{"template": "rolling_ke", "KE": "KE2", "M": "M", "I": "I", "R": "R", "v": "v"}]),
    None, "numerical: v in cm/s")

FORMALS["1ldr31zsc"] = E(
    rb({"A": S("m^2"), "d": S("kg/m^3"), "L": K("2", "m"), "E": S("J")},
       {"r": body("rod", density="A*d", u=(1, 0, 0), L="L")}, {"I": ax(["r"])},
       {"w": U("1/s", "positive"), "al": U("1/m^3")}, ["E = I*w**2/2", "w**2*A*d = al*E"], "al",
       ["linear density A d; the stem's alpha absorbs the 2 m length, so it carries units m^-3"]),
    None, "numerical: alpha")

FORMALS["1ldsq2v76"] = E(
    rb({"M": K("2", "kg"), "R": S("m"), "KE0": K("2240", "J")}, {"s": body("solid_sphere", "M", R="R")},
       {"I": ax(["s"])}, {"v": U("m/s", "positive"), "KE": U("J")}, ["KE = KE0"], "v", ["pure rolling"],
       relations=[{"template": "rolling_ke", "KE": "KE", "M": "M", "I": "I", "R": "R", "v": "v"}]),
    None, "numerical: v in m/s")

FORMALS["1ldtzxyz7"] = E(
    rb({"Ms": K("5", "kg"), "Md": K("4", "kg"), "R": S("m")},
       {"s": body("solid_sphere", "Ms", R="R"), "d": body("disc", "Md", R="R")},
       {"Is": ax(["s"], point=("R", "0", "0"), d=(0, 1, 0)), "Id": ax(["d"], point=("R", "0", "0"), d=(0, 1, 0))},
       {"x": U("")}, ["7*Id = x*Is"], "x", ["disc in the xy-plane; tangent in its plane at (R,0,0) along y"]),
    None, "numerical: x")

# ============================================================== chunk 5 (questions 101-127)
FORMALS["1ldws2rrh"] = E(
    rb({"rho": S("kg/m^3"), "R": S("m"), "L": S("m")},
       {"c1": body("solid_cylinder", density="rho", R="R", L="L"),
        "c2": body("solid_cylinder", density="rho", R="R/2", L="L/2")},
       {"I1": ax(["c1"]), "I2": ax(["c2"])}, {"x": U("")}, ["I1 = x*I2"], "x",
       ["carved part: concentric coaxial solid cylinder of the same material"]), None, "numerical: I1/I2")

FORMALS["lgnz71sz"] = E(
    rb({"M": S("kg"), "R": S("m")}, {"s": body("solid_sphere", "M", R="R"), "c": body("solid_cylinder", "M", R="R", L="R")},
       {"Is": ax(["s"]), "Ic": ax(["c"])},
       {"ks": U("m", "positive"), "kc": U("m", "positive"), "x": U("", "positive")},
       ["Is = M*ks**2", "Ic = M*kc**2", "ks**2*x = 4*kc**2"], "x",
       ["radii of gyration about the rolling (symmetry) axes through the centre"]), None, "numerical: x")

FORMALS["1lgp0utju"] = E(
    rb({"M": K("5", "kg"), "R": K("70", "cm"), "F": K("52.5", "N")}, {"c": body("hollow_cylinder", "M", R="R", L="R")},
       {"I": ax(["c"])}, {"al": U("1/s^2")}, ["F*R = I*al"], "al",
       ["thin-walled cylinder rotating about its fixed axis; rope tangential at the rim"]), None, "numerical: rad/s^2")

FORMALS["1lgq3lykk"] = E(
    rb({"M": S("kg"), "R": S("m"), "r0": K("pi/22", "s")}, {"s": body("solid_sphere", "M", R="R")}, {"I": ax(["s"])},
       {"w": U("1/s", "positive"), "v": U("m/s", "positive"), "KE": U("J")},
       ["v = w*R", "I*w = r0*KE"], "w",
       ["L about the axis through the centre = I w; total energy = rolling KE", "ratio pi:22 read in SI (s)"],
       relations=[{"template": "rolling_ke", "KE": "KE", "M": "M", "I": "I", "R": "R", "v": "v"}]),
    None, "numerical: w in rad/s (exact 88/(7 pi) = 4.002)")

FORMALS["1lgrjp53g"] = E(
    rb({"M": S("kg"), "R": S("m"), "v": S("m/s")}, {"b": body("spherical_shell", "M", R="R")}, {"I": ax(["b"])},
       {"KE": U("J"), "KEr": U("J"), "x": U("")}, ["KEr/KE = x/5"], "x", ["rolling: w = v/R"],
       relations=[{"template": "rolling_ke", "KE": "KE", "KEr": "KEr", "M": "M", "I": "I", "R": "R", "v": "v"}]),
    None, "numerical: x")

FORMALS["1lgsxfqv2"] = E(
    es({"I": S("kg*m^2"), "w": S("1/s")}, {"w2": U("1/s"), "x": U("")},
       ["I*w = 3*I*w2", "(I*w**2/2)/x = 3*I*w2**2/2"], "x", ["no external torque: L conserved"]),
    None, "numerical: x")

FORMALS["1lguyo8ek"] = E(
    rb({"M": K("500", "g"), "R": K("5", "cm"), "w": K("10", "1/s"), "u": K("10**-2", "s")},
       {"s": body("solid_sphere", "M", R="R")},
       {"Id": ax(["s"]), "It": ax(["s"], point=("R", "0", "0"), d=(0, 0, 1))}, {"x": U("")},
       ["It = x*u*(Id*w)"], "x", ["tangent parallel to the rotation diameter"]), None, "numerical: x")

FORMALS["1lgvr89zh"] = E({
    "kind": "statement_set", "format": "assertion_reason",
    "statements": {"A": C(True, "a fan keeps turning after switch-off"),
                   "R": C(True, "it keeps turning because of its (rotational) inertia")},
    "explains": C(True, "inertia of motion is the reason it keeps turning")},
    {"A": "4", "B": "1", "C": "3", "D": "2"}, "curated; codes 3 explains, 2 both true, 1 A only, 4 R only")

FORMALS["1lgvs5aid"] = E(
    es({"P": S("N"), "rx": K("-2", "m"), "ry": K("3", "m")},
       {"tx": U("N*m"), "ty": U("N*m"), "a": U("m"), "b": U("m"), "x": U("")},
       ["tx = ry*(-P)", "ty = -rx*(-P)", "tx = P*a", "ty = P*b", "a/b = x/2"], "x",
       ["r = (0,0,0) - (2,-3,0); F = -P k; tau = r x F"]), None, "numerical: x")

FORMALS["1lh02pimk"] = E(
    rb({"M": S("kg"), "R": S("m")}, {"w": body("semi_ring", "M", R="R")}, {"I": ax(["w"])},
       {"x": U("", "positive")}, ["I*x = M*R**2"], "x", ["normal axis through the centre"]), None, "numerical: x")

FORMALS["1lh25v73h"] = E(
    rb({"m": K("2", "kg"), "r": K("10", "cm"), "d": K("40", "cm"), "u": K("10**-3", "kg*m^2")},
       {"s1": body("solid_sphere", "m", center=("d/2", "0", "0"), R="r"),
        "s2": body("solid_sphere", "m", center=("-d/2", "0", "0"), R="r")},
       {"I": ax(["s1", "s2"])}, {"x": U("")}, ["I = x*u"], "x", ["light rod, axis perpendicular at the midpoint"]),
    None, "numerical: x")

FORMALS["1lh31p7nb"] = E(
    rb({"M": S("kg"), "m": S("kg"), "Rs": S("m")},
       {"g": body("ring", "M", R="Rr"), "s": body("solid_sphere", "m", R="Rs")}, {"Ir": ax(["g"]), "Is": ax(["s"])},
       {"Rr": U("m", "positive"), "k": U("m", "positive"), "x": U("", "positive")},
       ["Ir = M*k**2", "Is = m*k**2", "(Rr/Rs)**2 = 2/x"], "x", ["same radius of gyration k"]), None, "numerical: x")

FORMALS["lsanle50"] = E(
    rb({"M": K("2", "kg"), "L": K("30", "cm"), "J": K("0.2", "N*s")}, {"r": body("rod", "M", u=(1, 0, 0), L="L")},
       {"I": ax(["r"])}, {"w": U("1/s", "positive"), "t": U("s", "positive"), "x": U("1/s", "positive")},
       ["J*L/2 = I*w", "pi/2 = w*t", "t = pi/x"], "x",
       ["impulse perpendicular to the rod at B; free rod: rotation about the CM with w = J (L/2)/I_cm"]),
    None, "numerical: x")

FORMALS["jaoe38c1lscp2nwn"] = E(
    es({"W": K("12", "kg"), "th": K("60", "degree"), "L": S("m")}, {"N": U("kg", "positive")},
       ["N*L = W*(L/2)*cos(th)"], "N",
       ["smooth shoulder: its reaction is normal to the bar; torques about the ground end",
        "AMBIGUOUS STEM: a vertical shoulder force would give W/2 = 6 kg (option B)"]),
    {"A": "3", "B": "6", "C": "6*sqrt(3)", "D": "12"}, "force in kg-wt; model choice flagged (see model)")

FORMALS["jaoe38c1lscpwe1j"] = E(
    rb({"m": S("kg"), "R": S("m"), "g": S("m/s^2"), "h": S("m")},
       {"ring": body("ring", "m", R="R"), "sph": body("solid_sphere", "m", R="R")}, {"I1": ax(["ring"]), "I2": ax(["sph"])},
       {"v1": U("m/s", "positive"), "v2": U("m/s", "positive"), "x": U("", "positive")},
       ["m*g*h = m*v1**2/2 + I1*(v1/R)**2/2", "m*g*h = m*v2**2/2 + I2*(v2/R)**2/2",
        "(m*v1**2/2 + I1*(v1/R)**2/2)*x = 7*(m*v2**2/2 + I2*(v2/R)**2/2)"], "x",
       ["ASSUMPTION (not in stem): equal masses; total KE compared after the same descent"]),
    None, "numerical: x; equal masses assumed")

FORMALS["jaoe38c1lsd8digo"] = E(
    es({"m": S("kg"), "u": S("m/s"), "g": S("m/s^2"), "th": K("45", "degree")},
       {"H": U("m", "positive"), "Lz": U("kg*m^2/s"), "X": U("", "positive")},
       ["H = u**2*sin(th)**2/(2*g)", "Lz = m*u*cos(th)*H", "Lz*X*g = sqrt(2)*m*u**3"], "X",
       ["at the top velocity is horizontal (u cos th) at height H: L = m v_x H"]), None, "numerical: X")

FORMALS["jaoe38c1lsd8itby"] = E(
    rb({"m": K("2", "kg"), "r": K("50", "cm"), "d": K("150", "cm"), "u": K("1/20", "kg*m^2")},
       {"s1": body("solid_sphere", "m", center=("d/2", "0", "0"), R="r"),
        "s2": body("solid_sphere", "m", center=("-d/2", "0", "0"), R="r")},
       {"I": ax(["s1", "s2"])}, {"x": U("")}, ["I = x*u"], "x", ["light rod; axis perpendicular at the midpoint"]),
    None, "numerical: x")

FORMALS["jaoe38c1lsf22kej"] = E(
    rb({"M": S("kg"), "R": S("m"), "g": K("10", "m/s^2"), "th": K("60", "degree"), "u": K("1", "m/s^2")},
       {"c": body("solid_cylinder", "M", R="R", L="R")}, {"I": ax(["c"])}, {"a": U("m/s^2"), "x": U("")},
       ["a = x*u/sqrt(3)"], "x", ["solid cylinder rolling without slipping"],
       relations=[{"template": "rolling_incline", "a": "a", "M": "M", "I": "I", "R": "R", "g": "g", "th": "th"}]),
    None, "numerical: x")

FORMALS["jaoe38c1lsfm7qam"] = E(
    es({"m": K("5", "kg"), "v": K("3*sqrt(2)", "m/s"), "c": K("4", "m")},
       {"d": U("m", "positive"), "L": U("kg*m^2/s", "positive")},
       ["d**2*2 = c**2", "L = m*v*d"], "L", ["line y = x + c: perpendicular distance from origin c/sqrt(2)"]),
    None, "numerical: L")

FORMALS["1lsg70wif"] = E(
    es({"I1": K("4", "kg*m^2"), "I2": K("2", "kg*m^2"), "w1": K("10", "1/s"), "w2": K("4", "1/s")},
       {"w": U("1/s"), "dK": U("J")},
       ["I1*w1 + I2*w2 = (I1 + I2)*w", "dK = I1*w1**2/2 + I2*w2**2/2 - (I1 + I2)*w**2/2"], "dK",
       ["rotating in the same sense; L conserved"]), None, "numerical: J")

FORMALS["1lsgd0f2p"] = E(
    es({"m": S("kg"), "u": S("m/s"), "g": S("m/s^2"), "th": K("30", "degree")},
       {"H": U("m", "positive"), "Lz": U("kg*m^2/s"), "x": U("")},
       ["H = u**2*sin(th)**2/(2*g)", "Lz = m*u*cos(th)*H", "x = Lz*g/(m*u**3)"], "x",
       ["L about the launch point at the top = m v_x H"]),
    {"A": "1/sqrt(2)", "B": "0", "C": "-1", "D": "sqrt(3)/16"},
    "ratio L g/(m u^3); option C (m u^2/g, not an angular momentum) -> -1")

FORMALS["luxwdn7o"] = E(
    rb({"M": S("kg"), "R": S("m"), "g": S("m/s^2"), "th": K("30", "degree"), "l": S("m")},
       {"d": body("disc", "M", R="R")}, {"I": ax(["d"])},
       {"a2": U("m/s^2"), "a1": U("m/s^2"), "t1": U("s", "positive"), "t2": U("s", "positive"),
        "al": U("", "positive")},
       ["M*a1 = M*g*sin(th)", "l = a1*t1**2/2", "l = a2*t2**2/2", "2*t2**2 = al*t1**2"], "al",
       ["slipping = frictionless; rolling via template; from rest; angle instance 30 deg"],
       relations=[{"template": "rolling_incline", "a": "a2", "M": "M", "I": "I", "R": "R", "g": "g", "th": "th"}]),
    None, "numerical: alpha")

FORMALS["luz2uzm2"] = E(
    es({"I": K("0.40", "kg*m^2"), "R": K("10", "cm"), "F": K("40", "N"), "t": K("10", "s")},
       {"al": U("1/s^2"), "w": U("1/s")}, ["F*R = I*al", "w = al*t"], "w", ["fixed axis, from rest"]),
    None, "numerical: rad/s")

FORMALS["lv0vy02i"] = E(
    rb({"m1": S("kg"), "m2": S("kg"), "R1": S("m"), "R2": S("m"), "v": S("m/s"), "g": S("m/s^2")},
       {"s": body("solid_sphere", "m1", R="R1"), "c": body("hollow_cylinder", "m2", R="R2", L="R2")},
       {"I1": ax(["s"]), "I2": ax(["c"])}, {"h1": U("m", "positive"), "h2": U("m", "positive"), "n": U("")},
       ["m1*g*h1 = m1*v**2/2 + I1*(v/R1)**2/2", "m2*g*h2 = m2*v**2/2 + I2*(v/R2)**2/2", "h1/h2 = n/10"], "n",
       ["rolling up without slipping; hollow cylinder = thin-walled"]), None, "numerical: n")

FORMALS["lv3vefxa"] = E(
    rb({"M": S("kg"), "R": S("m"), "w": S("1/s")},
       {"d1": body("disc", "M", R="R"), "d2": body("disc", "M/2", R="R")}, {"I1": ax(["d1"]), "I2": ax(["d2"])},
       {"w2": U("1/s"), "x": U("")}, ["I1*w = (I1 + I2)*w2", "x = w2/w"], "x", ["placed gently: L conserved"]),
    {"A": "4/5", "B": "5/4", "C": "3/2", "D": "2/3"}, "ratio w'/w")

FORMALS["lv9s25k9"] = E(
    rb({"M": S("kg"), "R": S("m"), "v": S("m/s")}, {"b": body("spherical_shell", "M", R="R")}, {"I": ax(["b"])},
       {"KE": U("J"), "KEr": U("J"), "x": U("")}, ["KEr/KE = x/5"], "x", ["hollow sphere = thin shell; rolling"],
       relations=[{"template": "rolling_ke", "KE": "KE", "KEr": "KEr", "M": "M", "I": "I", "R": "R", "v": "v"}]),
    None, "numerical: x")

FORMALS["lvb29eoa"] = E(
    rb({"a": K("2", "m"), "m1": K("2", "kg"), "m2": K("4", "kg"), "m3": K("6", "kg")},
       {"p1": body("point", "m1", center=("0", "-a/(2*sqrt(3))", "0")),
        "p2": body("point", "m2", center=("a/4", "a/(4*sqrt(3))", "0")),
        "p3": body("point", "m3", center=("-a/4", "a/(4*sqrt(3))", "0"))},
       {"I": ax(["p1", "p2", "p3"])}, {}, [], "I",
       ["vertices (0, a/sqrt3), (+-a/2, -a/(2 sqrt3)); side midpoints at distance a/(2 sqrt3) from the centroid"]),
    None, "numerical: kg m^2")
