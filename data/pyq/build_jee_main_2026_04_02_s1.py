"""Transcription of JEE Main 2026, 2 April, Shift 1 (Paper 1) - questions that fit the current engines.

Source: PDF supplied by the user (eSaral reproduction). Stems transcribed from the page images.
answer_key = independent hand solution (key_source "unofficial_reference") - NOT the official key.
Rights status UNKNOWN until confirmed: searchable internally; no derivation/display/LLM use.
Run:  python data/pyq/build_jee_main_2026_04_02_s1.py  -> writes jee_main_2026_04_02_s1.jsonl
"""
import json
from pathlib import Path

SRC = {"document": "JEE Main 2026 02-Apr Shift-1 (eSaral reproduction).pdf", "rights_status": "UNKNOWN",
       "permitted_uses": ["storage", "search"]}
K = lambda v, u="": {"value": v, "unit": u}  # noqa: E731
U = lambda u="", d="real": {"unit": u, "domain": d}  # noqa: E731
OPT = lambda *pairs: [{"id": i, "text": t, "value": v} for i, t, v in pairs]  # noqa: E731


def rec(qno, subject, chapter, topic, fmt, stem, options, key, formal, page):
    r = {"pyq_id": f"JEEM-2026-04-02-S1-Q{qno:02d}", "exam": "JEE_MAIN", "year": 2026, "shift": "02 Apr S1",
         "subject": subject, "chapter": chapter, "topic": topic, "question_format": fmt, "stem": stem,
         "options": options, "answer_key": key, "key_source": "unofficial_reference",
         "source": {**SRC, "page": page}, "extraction": {"method": "manual", "visual_review_done": True},
         "formal": formal}
    if fmt == "numerical_integer":
        r["numerical_rounding"] = "nearest_integer"
    return r


ES = "equation_system"
R = []

# ------------------------------------------------------------------ Mathematics
R.append(rec(1, "MATHEMATICS", "Quadratic Equations", "roots of a summed quadratic", "single_correct_mcq",
    "Let α, α+2, α ∈ Z, be the roots of the quadratic equation x(x+2) + (x+1)(x+3) + (x+2)(x+4) + .... + "
    "(x+n−1)(x+n+1) = 4n for some n ∈ N. Then n + α is equal to:",
    OPT(("A", "0", "0"), ("B", "1", "1"), ("C", "2", "2"), ("D", "3", "3")), "C",
    {"kind": ES, "stem": "see record stem",
     "knowns": {}, "unknowns": {"n": U("", "natural"), "a": U("", "integer"), "t": U()},
     "equations": ["2*a + 2 = -(n + 1)", "a*(a + 2) = (n - 1)*(2*n - 1)/6 + (n - 1) - 4", "t = n + a"],
     "target": "t",
     "model": ["sum = n x^2 + n(n+1) x + (n-1)n(2n-1)/6 + n(n-1); equation divided by n",
               "monic quadratic x^2 + (n+1)x + [(n-1)(2n-1)/6 + (n-1) - 4] = 0 with roots a, a+2"]}, 1))

# ------------------------------------------------------------------ Physics
R.append(rec(27, "PHYSICS", "Units and Measurements", "errors", "single_correct_mcq",
    "The diameter of a wire measured by a screw gauge of least count 0.001 cm is 0.08 cm. The length measured "
    "by a scale of least count 0.1 cm is 150 cm. When a weight of 100 N is applied to the wire, the extension "
    "in length is 0.5 cm, measured by a micrometer of least count 0.001 cm. The error in the measured Young's "
    "modulus is α × 10^9 N/m^2. The value of α is ____. (Ignore the contribution of the load to Young's "
    "modulus error calculation)",
    OPT(("A", "1.3", "1.3"), ("B", "1.65", "1.65"), ("C", "0.13", "0.13"), ("D", "0.25", "0.25")), "B",
    {"kind": ES, "options_rounded": {"rel_tol": "0.01"},
     "knowns": {"F": K("100", "N"), "L": K("150", "cm"), "d": K("0.08", "cm"), "x": K("0.5", "cm"),
                "dd": K("0.001", "cm"), "dL": K("0.1", "cm"), "dx": K("0.001", "cm"), "u": K("1", "GPa")},
     "unknowns": {"Y": U("Pa", "positive"), "dY": U("Pa", "positive"), "al": U("", "positive")},
     "equations": ["Y*pi*d**2*x = 4*F*L", "dY/Y = 2*dd/d + dL/L + dx/x", "dY = al*u"], "target": "al",
     "model": ["Y = 4FL/(pi d^2 x)", "maximum relative error adds; d enters squared"]}, 2))

R.append(rec(30, "PHYSICS", "Gravitation", "Kepler's third law", "single_correct_mcq",
    "A planet (P1) is moving around the star of mass 2M in the orbit of radius R. Another planet (P2) is "
    "moving around another star of mass 4M in a orbit of radius 2R. Ratio of time periods of revolution of "
    "P2 and P1 is ____.",
    OPT(("A", "1/2", "1/2"), ("B", "2", "2"), ("C", "4", "4"), ("D", "1/4", "1/4")), "B",
    {"kind": ES, "knowns": {"G": K("symbolic", "N*m^2/kg^2"), "M": K("symbolic", "kg"), "R": K("symbolic", "m")},
     "unknowns": {"T1": U("s", "positive"), "T2": U("s", "positive"), "q": U("", "positive")},
     "equations": ["T1**2*G*(2*M) = 4*pi**2*R**3", "T2**2*G*(4*M) = 4*pi**2*(2*R)**3", "q = T2/T1"],
     "target": "q", "model": ["circular orbits; planet mass negligible: T^2 = 4 pi^2 r^3/(G M_star)"]}, 2))

R.append(rec(31, "PHYSICS", "Rotational Motion", "angular kinematics", "single_correct_mcq",
    "A particle is rotating in a circular path and at any instant its motion can be described as "
    "θ = 5t^4/40 − t^3/3. The angular acceleration of the particle after 10 seconds is ____ rad/s^2.",
    OPT(("A", "150", "150"), ("B", "120", "120"), ("C", "130", "130"), ("D", "170", "170")), "C",
    {"kind": ES, "knowns": {"t": K("10")}, "unknowns": {"al": U()},
     "equations": ["al = 3*t**2/2 - 2*t"], "target": "al",
     "model": ["alpha = d^2(theta)/dt^2 = 60 t^2/40 - 2t (derivative taken by hand; t in s as a pure number)"]}, 2))

R.append(rec(32, "PHYSICS", "Capacitance", "dielectric slab", "single_correct_mcq",
    "A parallel plate air capacitor has a capacitance C. When it is half filled as shown in figure with a "
    "dielectric constant K = 5, the percentage increase in the capacitance is ____. [figure: slab of "
    "thickness d/2 parallel to the plates, plate separation d]",
    OPT(("A", "33.34", "33.34"), ("B", "66.67", "66.67"), ("C", "200", "200"), ("D", "400", "400")), "B",
    {"kind": ES, "options_rounded": {"rel_tol": "0.001"},
     "knowns": {"e0": K("symbolic", "F/m"), "A": K("symbolic", "m^2"), "d": K("symbolic", "m"), "Kd": K("5")},
     "unknowns": {"C0": U("F", "positive"), "C1": U("F", "positive"), "p": U("", "positive")},
     "equations": ["C0*d = e0*A", "C1*(d/2 + d/(2*Kd)) = e0*A", "p = 100*(C1 - C0)/C0"], "target": "p",
     "model": ["slab parallel to plates (from figure): air and dielectric layers in series"]}, 3))

R.append(rec(34, "PHYSICS", "Electrostatics", "connected conducting spheres", "single_correct_mcq",
    "Two charged conducting spheres S1 and S2 of radii 8 cm and 18 cm are connected to each other by a wire. "
    "After equilibrium is established, the ratio of electric fields on S1 and S2 spheres are ES1 and ES2 "
    "respectively. The value of ES1/ES2 is ____.",
    OPT(("A", "3/2", "3/2"), ("B", "2/3", "2/3"), ("C", "4/9", "4/9"), ("D", "9/4", "9/4")), "D",
    {"kind": ES, "knowns": {"r1": K("8", "cm"), "r2": K("18", "cm"), "V": K("symbolic", "V")},
     "unknowns": {"E1": U("V/m", "positive"), "E2": U("V/m", "positive"), "q": U("", "positive")},
     "equations": ["E1*r1 = V", "E2*r2 = V", "q = E1/E2"], "target": "q",
     "model": ["connected conductors reach a common potential V; surface field E = V/r"]}, 3))

R.append(rec(35, "PHYSICS", "Waves", "wave speed", "single_correct_mcq",
    "The equation of a plane progressive wave is given by y = 5 cos π(200t − x/150) where x and y are in cm "
    "and t is in second. The velocity of the wave is ____ m/s.",
    OPT(("A", "120", "120"), ("B", "150", "150"), ("C", "200", "200"), ("D", "300", "300")), "D",
    {"kind": ES, "knowns": {"w": K("200*pi", "1/s"), "kk": K("pi/150", "1/cm")},
     "unknowns": {"v": U("m/s", "positive")}, "equations": ["v*kk = w"], "target": "v",
     "model": ["y = A cos(wt - kx): v = w/k"]}, 3))

R.append(rec(40, "PHYSICS", "Ray Optics", "thin prism", "single_correct_mcq",
    "For a thin symmetric prism made of glass (refractive index 1.5), the ratio of incident angle and minimum "
    "deviation will be ____.",
    OPT(("A", "3 : 4", "3/4"), ("B", "3 : 2", "3/2"), ("C", "2 : 1", "2"), ("D", "1 : 2", "1/2")), "B",
    {"kind": ES, "knowns": {"A": K("symbolic", "degree"), "mu": K("1.5")},
     "unknowns": {"dm": U("degree", "positive"), "i": U("degree", "positive"), "q": U("", "positive")},
     "equations": ["dm = (mu - 1)*A", "2*i = A + dm", "q = i/dm"], "target": "q",
     "model": ["thin prism: deviation (mu-1)A", "minimum deviation: i = (A + dm)/2"]}, 3))

R.append(rec(42, "PHYSICS", "Dual Nature", "photoelectric effect", "single_correct_mcq",
    "For a certain metal, when monochromatic light of wavelength λ is incident, the stopping potential for "
    "photoelectrons is 3V0. When the same metal is illuminated by light of wavelength 2λ, then the stopping "
    "potential becomes V0. The threshold wavelength for photoelectric emission for the given metal is αλ. "
    "The value of α is ____.",
    OPT(("A", "1", "1"), ("B", "4", "4"), ("C", "2", "2"), ("D", "3", "3")), "B",
    {"kind": ES, "knowns": {"h": K("symbolic", "J*s"), "c": K("symbolic", "m/s"), "lam": K("symbolic", "m"),
                            "e": K("symbolic", "C")},
     "unknowns": {"V0": U("V", "positive"), "phi": U("J", "positive"), "lam0": U("m", "positive"),
                  "al": U("", "positive")},
     "equations": ["3*e*V0 = h*c/lam - phi", "e*V0 = h*c/(2*lam) - phi", "phi*lam0 = h*c", "lam0 = al*lam"],
     "target": "al", "model": ["Einstein photoelectric equation eV = hc/lambda - phi"]}, 4))

R.append(rec(43, "PHYSICS", "Electromagnetic Waves", "forces on a charge", "single_correct_mcq",
    "An electromagnetic wave travelling in x-direction is described by field equation Ey = 300 sin ω(t − x/c). "
    "If the electron is restricted to move in y-direction only with speed of 1.5 × 10^6 m/s then ratio of "
    "maximum electric and magnetic forces acting on the electron is ____.",
    OPT(("A", "200", "200"), ("B", "150", "150"), ("C", "400", "400"), ("D", "300", "300")), "A",
    {"kind": ES, "knowns": {"E0": K("300", "V/m"), "v": K("1.5*10**6", "m/s"), "c": K("3*10**8", "m/s"),
                            "e": K("symbolic", "C")},
     "unknowns": {"B0": U("T", "positive"), "FE": U("N", "positive"), "FB": U("N", "positive"),
                  "q": U("", "positive")},
     "equations": ["B0*c = E0", "FE = e*E0", "FB = e*v*B0", "q = FE/FB"], "target": "q",
     "model": ["B0 = E0/c, B along z; velocity along y is perpendicular to B"]}, 4))

R.append(rec(44, "PHYSICS", "Atoms", "Bohr model", "single_correct_mcq",
    "Angular momentum of an electron in a hydrogen atom is 3h/π, then the energy of the electron is ____ eV.",
    OPT(("A", "−1.51", "-1.51"), ("B", "−0.85", "-0.85"), ("C", "−0.38", "-0.38"), ("D", "−0.28", "-0.28")), "C",
    {"kind": ES, "options_rounded": {"rel_tol": "0.02"},
     "knowns": {"h": K("symbolic", "J*s"), "E1": K("13.6", "eV")},
     "unknowns": {"n": U("", "natural"), "En": U("eV", "negative")},
     "equations": ["n*h/(2*pi) = 3*h/pi", "En*n**2 = -E1"], "target": "En",
     "model": ["Bohr quantisation L = n h/(2 pi)", "E_n = -13.6/n^2 eV"]}, 4))

R.append(rec(45, "PHYSICS", "Mechanical Properties of Fluids", "surface energy", "single_correct_mcq",
    "A liquid drop of diameter 2 mm breaks into 512 droplets. The change in surface energy is α × 10^−6 J. "
    "The value of α is ____. (Take surface tension of liquid = 0.08 N/m)",
    OPT(("A", "10", "10"), ("B", "7", "7"), ("C", "8", "8"), ("D", "11", "11")), "B",
    {"kind": ES, "options_rounded": {"rel_tol": "0.02"},
     "knowns": {"R": K("1", "mm"), "T": K("0.08", "N/m"), "u": K("1", "uJ"), "N": K("512")},
     "unknowns": {"r": U("m", "positive"), "dE": U("J", "positive"), "al": U("", "positive")},
     "equations": ["N*r**3 = R**3", "dE = T*4*pi*(N*r**2 - R**2)", "dE = al*u"], "target": "al",
     "model": ["volume conserved", "single surface per drop"]}, 4))

R.append(rec(46, "PHYSICS", "Wave Optics", "single-slit diffraction", "numerical_integer",
    "In single slit diffraction pattern, the wavelength of light used is 628 nm and slit width is 0.2 mm, the "
    "angular width of central maximum is α × 10^−2 degrees. The value of α is ____.",
    [], "36",
    {"kind": ES, "knowns": {"lam": K("628", "nm"), "a": K("0.2", "mm")},
     "unknowns": {"al": U("", "positive")},
     "equations": ["al*(pi/180)/100 = 2*lam/a"], "target": "al",
     "model": ["angular width of central maximum 2 lambda/a (small angle)", "alpha x 10^-2 degrees in radians"]}, 4))

R.append(rec(47, "PHYSICS", "Thermodynamics", "adiabatic work", "numerical_integer",
    "A vessel contains 0.15 m^3 of a gas at pressure 8 bar and temperature 140°C with cp = 3R and cv = 2R. It "
    "is expanded adiabatically till pressure falls to 1 bar. The work done during this process is ____ kJ. "
    "(R is gas constant)",
    [], "120",
    {"kind": ES, "knowns": {"P1": K("8", "bar"), "V1": K("0.15", "m^3"), "P2": K("1", "bar")},
     "unknowns": {"V2": U("m^3", "positive"), "W": U("kJ", "positive")},
     "equations": ["P1*V1**(3/2) = P2*V2**(3/2)", "W = (P1*V1 - P2*V2)/(3/2 - 1)"], "target": "W",
     "model": ["gamma = cp/cv = 3/2", "reversible adiabatic PV^gamma = const", "work done BY the gas"]}, 4))

R.append(rec(48, "PHYSICS", "Moving Charges and Magnetism", "Lorentz force", "numerical_integer",
    "1 μC charge moving with velocity v = (î − 2ĵ + 3k̂) m/s in the region of magnetic field "
    "B = (2î + 3ĵ − 5k̂) T. The magnitude of force acting on it is √α × 10^−6 N. The value of α is ____.",
    [], "171",
    {"kind": ES, "knowns": {"q": K("1", "uC"), "vx": K("1", "m/s"), "vy": K("-2", "m/s"), "vz": K("3", "m/s"),
                            "Bx": K("2", "T"), "By": K("3", "T"), "Bz": K("-5", "T"), "u": K("1", "uN")},
     "unknowns": {"Fx": U("N"), "Fy": U("N"), "Fz": U("N"), "F": U("N", "positive"), "al": U("", "positive")},
     "equations": ["Fx = q*(vy*Bz - vz*By)", "Fy = q*(vz*Bx - vx*Bz)", "Fz = q*(vx*By - vy*Bx)",
                   "F**2 = Fx**2 + Fy**2 + Fz**2", "F = sqrt(al)*u"], "target": "al",
     "model": ["F = q v x B, components of the cross product"]}, 4))

R.append(rec(49, "PHYSICS", "Mechanical Properties of Solids", "stress in a hanging wire", "numerical_integer",
    "A uniform wire of length l of weight w is suspended from the roof with a weight of W at the other end. The "
    "stress in the wire at l/3 distance from the top is (W/A + 2w/(γA)), where A is the cross sectional area of "
    "the wire. The value of γ is ____.",
    [], "3",
    {"kind": ES, "knowns": {"W": K("symbolic", "N"), "w": K("symbolic", "N"), "A": K("symbolic", "m^2")},
     "unknowns": {"T": U("N", "positive"), "g": U("", "positive")},
     "equations": ["T = W + w*(2/3)", "T/A = W/A + 2*w/(g*A)"], "target": "g",
     "model": ["tension at l/3 from top supports W and the 2l/3 of wire below"]}, 4))

R.append(rec(50, "PHYSICS", "Mechanical Properties of Fluids", "flotation", "numerical_integer",
    "A tub is filled with water and a wooden cube 10 cm × 10 cm × 10 cm is placed in the water. The wooden cube "
    "is found to float on the water with a part of it submerged in water. When a metal coin is placed on the "
    "wooden cube, the submerged part is increased by 3.87 cm. The mass of the metal coin is ____ gram. (Take "
    "water density as 1 g/cm^3 and density of wood as 0.4 g/cm^3)",
    [], "387",
    {"kind": ES, "knowns": {"rho": K("1", "g/cm^3"), "s": K("10", "cm"), "dh": K("3.87", "cm"),
                            "gr": K("symbolic", "m/s^2")},
     "unknowns": {"mc": U("g", "positive")}, "equations": ["mc*gr = rho*s**2*dh*gr"], "target": "mc",
     "model": ["coin weight = extra buoyancy; cube does not sink fully (4 + 3.87 < 10 cm)"]}, 4))

# ------------------------------------------------------------------ Chemistry
R.append(rec(51, "CHEMISTRY", "Some Basic Concepts", "stoichiometry", "single_correct_mcq",
    "The mass of iron converted into Fe3O4 by the action of 18 g of steam is: (Given: Molar mass of H, O and "
    "Fe are 1, 16 and 56 g mol^−1 respectively) Assume iron is present in excess:",
    OPT(("A", "2.1 g", "2.1"), ("B", "4.2 g", "4.2"), ("C", "21 g", "21"), ("D", "42 g", "42")), "D",
    {"kind": "stoichiometry", "reaction": "3 Fe + 4 H2O -> Fe3O4 + 4 H2",
     "given": {"H2O": {"mass_g": "18"}}, "atomic_masses": {"H": "1", "O": "16", "Fe": "56"},
     "target": {"species": "Fe", "quantity": "mass_g"},
     "reaction_source": "standard: 3Fe + 4H2O(g) -> Fe3O4 + 4H2 (equation not printed in the stem)"}, 4))

R.append(rec(52, "CHEMISTRY", "Structure of Atom", "ionisation energy of H-like ion", "single_correct_mcq",
    "What is the energy (in J atom^−1) required for the following process? Li^2+(g) → Li^3+(g) + e^−. "
    "(Take the ionization energy for the H atom in the ground state as 2.18 × 10^−18 J atom^−1)",
    OPT(("A", "8.72 × 10^−18", "8.72*10**-18"), ("B", "1.962 × 10^−18", "1.962*10**-18"),
        ("C", "1.962 × 10^−17", "1.962*10**-17"), ("D", "6.54 × 10^−17", "6.54*10**-17")), "C",
    {"kind": ES, "knowns": {"EH": K("2.18*10**-18", "J"), "Z": K("3")},
     "unknowns": {"E": U("J", "positive")}, "equations": ["E = Z**2*EH"], "target": "E",
     "model": ["hydrogen-like ion ground state: IE = Z^2 x IE(H)"]}, 4))

R.append(rec(54, "CHEMISTRY", "Thermodynamics", "Hess's law", "single_correct_mcq",
    "Consider the following data. (i) 2Al(s) + 6HCl(aq) → Al2Cl6(aq) + 3H2(g) + 1200 kJ/mol (ii) H2(g) + "
    "Cl2(g) → 2HCl(g) + 164 kJ/mol. (iii) HCl(g) + aq → HCl(aq) + 83 kJ/mol. (iv) Al2Cl6(s) + aq → "
    "Al2Cl6(aq) + 663 kJ/mol. The enthalpy of formation of anhydrous solid Al2Cl6 is:",
    OPT(("A", "−648 kJ mol^−1", "-648"), ("B", "−1350 kJ mol^−1", "-1350"), ("C", "−2002 kJ mol^−1", "-2002"),
        ("D", "−1527 kJ mol^−1", "-1527")), "D",
    {"kind": ES, "knowns": {"H1": K("-1200", "kJ/mol"), "H2": K("-164", "kJ/mol"), "H3": K("-83", "kJ/mol"),
                            "H4": K("-663", "kJ/mol")},
     "unknowns": {"Hf": U("kJ/mol")}, "equations": ["Hf = H1 + 3*H2 + 6*H3 - H4"], "target": "Hf",
     "model": ["heat written on the product side = exothermic (negative dH)",
               "target 2Al + 3Cl2 -> Al2Cl6(s) = (i) + 3(ii) + 6(iii) - (iv)"]}, 5))

R.append(rec(55, "CHEMISTRY", "Solutions", "colligative property and Ka", "single_correct_mcq",
    "19.5 g of fluoro acetic acid (molar mass = 78 g mol^−1) is dissolved in 500 g of water at 298 K. The "
    "depression in the freezing point of water was 1°C. What is Ka of fluoro acetic acid? (For water, Kf = "
    "1.86 K kg mol^−1). Assume molarity and molality to have same values.",
    OPT(("A", "10^−6", "10**-6"), ("B", "4 × 10^−4", "4*10**-4"), ("C", "3 × 10^−5", "3*10**-5"),
        ("D", "3 × 10^−3", "3*10**-3")), "D",
    {"kind": ES, "options_rounded": {"rel_tol": "0.05"},
     "knowns": {"w": K("19.5", "g"), "M": K("78", "g/mol"), "W": K("500", "g"), "Kf": K("1.86", "K*kg/mol"),
                "dT": K("1", "K")},
     "unknowns": {"m": U("mol/kg", "positive"), "i": U("", "positive"), "a": U("", "positive"),
                  "Ka": U("mol/kg", "positive")},
     "equations": ["m*M*W = w", "dT = i*Kf*m", "i = 1 + a", "Ka*(1 - a) = m*a**2"], "target": "Ka",
     "model": ["HA <=> H+ + A-: i = 1 + alpha", "Ka = c alpha^2/(1 - alpha) with c = molality"]}, 5))

R.append(rec(71, "CHEMISTRY", "Coordination Compounds", "ionisation isomer test", "numerical_integer",
    "5.33 g of CrCl3·6H2O, which is a 1 : 3 electrolyte, is dissolved in water and is passed through a cation "
    "exchanger. The chloride ions in the eluted solution, on treatment with AgNO3 results in 8.61 g of AgCl. "
    "The ratio of moles of complex reacted and moles of AgCl formed is ____ × 10^−2. (Nearest integer) "
    "[Molar mass in g mol^−1 Cr : 52, Ag : 108, Cl : 35.5, H : 1, O : 16]",
    [], "33",
    {"kind": ES, "knowns": {"m1": K("5.33", "g"), "m2": K("8.61", "g"), "MCr": K("52", "g/mol"),
                            "MCl": K("35.5", "g/mol"), "MH": K("1", "g/mol"), "MO": K("16", "g/mol"),
                            "MAg": K("108", "g/mol")},
     "unknowns": {"Mc": U("g/mol", "positive"), "Ma": U("g/mol", "positive"), "n1": U("mol", "positive"),
                  "n2": U("mol", "positive"), "x": U("", "positive")},
     "equations": ["Mc = MCr + 3*MCl + 6*(2*MH + MO)", "Ma = MAg + MCl", "n1*Mc = m1", "n2*Ma = m2",
                   "x/100 = n1/n2"], "target": "x",
     "model": ["moles from given masses; the 1:3 information is not needed for the asked ratio"]}, 7))

R.append(rec(73, "CHEMISTRY", "Hydrocarbons", "combustion of alkane", "numerical_integer",
    "One mole of an alkane (x) requires 8 mole oxygen for complete combustion. Sum of number of carbon and "
    "hydrogen atoms in the alkane (x) is ____.",
    [], "17",
    {"kind": ES, "knowns": {}, "unknowns": {"n": U("", "natural"), "s": U("", "natural")},
     "equations": ["(3*n + 1)/2 = 8", "s = n + (2*n + 2)"], "target": "s",
     "model": ["CnH2n+2 + (3n+1)/2 O2 -> n CO2 + (n+1) H2O"]}, 7))

R.append(rec(74, "CHEMISTRY", "Chemical Kinetics", "Arrhenius equation", "numerical_integer",
    "For reaction A → P, rate constant k = 1.5 × 10^3 s^−1 at 27°C. If activation energy for the above reaction "
    "is 60 kJ mol^−1, then the temperature (in °C) at which rate constant, k = 4.5 × 10^3 s^−1 is ____. "
    "(Nearest integer) Given: log 2 = 0.30, log 3 = 0.48, R = 8.3 J K^−1 mol^−1, ln 10 = 2.3",
    [], "41",
    {"kind": ES, "knowns": {"Ea": K("60", "kJ/mol"), "R": K("8.3", "J/(mol*K)"), "T1": K("300", "K"),
                            "L3": K("2.3*0.48"), "K1": K("1", "K")},
     "unknowns": {"T2": U("K", "positive"), "tc": U()},
     "equations": ["L3 = (Ea/R)*(1/T1 - 1/T2)", "tc = T2/K1 - 273"], "target": "tc",
     "model": ["ln(k2/k1) = ln 3 = 2.3 x 0.48 (given values)", "27 C = 300 K; C = K - 273 (as given data implies)"]}, 7))

R.append(rec(75, "CHEMISTRY", "Thermodynamics", "transition temperature", "numerical_integer",
    "At the transition temperature T, A ⇌ B and ΔG° = 105 − 35 log T where A and B are two states of substance "
    "X. The transition temperature in °C when pressure is 1 atm is ____. (Nearest integer)",
    [], "727",
    {"kind": ES, "knowns": {}, "unknowns": {"T": U("", "positive"), "tc": U()},
     "equations": ["105 - 35*log(T, 10) = 0", "tc = T - 273"], "target": "tc",
     "model": ["at transition dG = 0 (equilibrium at 1 atm)", "log = log10; T in K as a pure number"]}, 7))

out = Path(__file__).with_name("jee_main_2026_04_02_s1.jsonl")
with open(out, "w", encoding="utf-8") as fh:
    for r in R:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"wrote {len(R)} records to {out}")
