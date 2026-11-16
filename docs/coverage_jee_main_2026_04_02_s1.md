# Coverage map: JEE Main 2026, 2 April Shift 1 (75 questions)

Reference paper supplied by the user (eSaral reproduction; no official key in the PDF).

Legend:
- ✅ **verified**: a dedicated engine proves the answer.
- 🟢 **computed**: the general equation checker proves the maths, units and answer; a teacher confirms the equations model the question.
- 🔶 **next**: an engine extension already planned covers it.
- 🔴 **expert**: depends on facts, mechanisms or figures; needs a curated rule base and a chemist or teacher.

| Q | Topic | Status | Notes / engine needed |
|---|---|---|---|
| **Maths** | | | |
| 1 | Quadratic from a summed series | 🟢 | `equation_system` with integer and natural unknowns → n + α = 2 |
| 2 | Complex numbers | 🔶 | add real/imaginary parts (`re`, `im`) to the general checker |
| 3 | Linear system with no solution | 🔶 | rank/consistency engine (determinant = 0 and inconsistent) |
| 4 | Matrices, statements S1/S2 | 🔶 | matrix engine + statement-pair format |
| 5 | APs, intersection, divisibility | 🔶 | exhaustive finite-enumeration engine (exact counting) |
| 6 | Counting digits, each used once or more | 🔶 | enumeration engine (5!·S(7,5) = 16800) |
| 7 | Binomial coefficient equation, count pairs | 🔶 | enumeration engine |
| 8 | Grouped mean → equation k satisfies | 🔶 | needs "option is an equation" support |
| 9 | Incentre from side midpoints | 🔶 | coordinate-geometry engine |
| 10 | Ellipse, latus rectum | 🔶 | conics engine |
| 11 | Trig product identity | 🔶 | exact trig simplification check |
| 12 | Trig equation, count solutions | 🔶 | equation engine over interval with parameter set |
| 13 | 3D lines intersecting on xy-plane | 🔶 | vectors/3D engine |
| 14 | Max of vector expression | 🔶 | vectors + optimisation |
| 15 | Line ⟂ two vectors, foot of perpendicular | 🔶 | vectors/3D engine |
| 16 | Limit with sin, log | 🔶 | limits (SymPy `limit`) + cross-check |
| 17 | ODE | 🔶 | ODE engine (`dsolve` + substitution check) |
| 18 | Critical points of a piecewise function | 🔶 | calculus engine |
| 19 | Integral with greatest integer function | 🔶 | piecewise integration |
| 20 | ODE through a point | 🔶 | ODE engine |
| 21 | Domain of log/sqrt function | 🔶 | inequality/domain engine |
| 22 | Series from a sum formula | 🔶 | sequences engine |
| 23 | Probability over a finite set | 🔶 | enumeration engine |
| 24 | Circle, chord, intercepts | 🔶 | coordinate geometry |
| 25 | Definite integrals | 🔶 | integration engine |
| **Physics** | | | |
| 26 | Dimensions of ½ε₀E² | 🔶 | dimension-exponent questions (dimension engine exists) |
| 27 | Error in Young's modulus | 🟢 | rounded options (1.651 → 1.65) |
| 28 | Acceleration from a velocity field | 🔶 | vector-calculus support |
| 29 | Momentum/force/torque statements | 🔶 | vectors + multi-statement format |
| 30 | Kepler, ratio of periods | 🟢 | symbolic G, M, R → 2 |
| 31 | Angular acceleration from θ(t) | 🟢 | derivative written by hand in the model; 🔶 derivatives in the checker |
| 32 | Capacitor half-filled with dielectric | 🟢 | figure (slab parallel to plates) encoded in the model |
| 33 | ΔQ : ΔU : ΔW, diatomic gas | 🔶 | needs "ratio triple" option format |
| 34 | Connected spheres, E ratio | 🟢 | symbolic V → 9/4 |
| 35 | Wave speed | 🟢 | exact, cm → m conversion |
| 36 | Two dipoles (figure) | 🔴/🔶 | field-geometry diagram engine |
| 37 | Diode/Zener waveform circuit | 🔴 | nonlinear components; figure-based |
| 38 | Coil power scaling | 🔶 | scaling (proportionality) support |
| 39 | Magnetic field of bent wires (figure) | 🔶 | Biot-Savart geometry engine |
| 40 | Thin prism | 🟢 | symbolic A → 3 : 2 |
| 41 | Refraction at a spherical surface (figure) | 🔶 | optics engine with sign convention |
| 42 | Photoelectric effect | 🟢 | symbolic h, c, λ, e → α = 4 |
| 43 | EM wave force ratio | 🟢 | → 200 |
| 44 | Bohr energy | 🟢 | rounded options (−0.378 → −0.38) |
| 45 | Drop splitting, surface energy | 🟢 | rounded options (7.04 → 7) |
| 46 | Single-slit angular width | 🟢 | nearest integer (35.98 → 36) |
| 47 | Adiabatic work | 🟢 | → 120 kJ |
| 48 | Lorentz force | 🟢 | cross-product components → 171 |
| 49 | Stress in a hanging wire | 🟢 | → γ = 3 |
| 50 | Flotation with a coin | 🟢 | → 387 g |
| **Chemistry** | | | |
| 51 | Fe + steam stoichiometry | ✅ | stoichiometry engine; reaction confirmed by a chemist |
| 52 | Ionisation energy of Li²⁺ | 🟢 | Z²·E(H) |
| 53 | MO bond order statements | 🔴 | MO-theory rule base + statement format |
| 54 | Hess's law | 🟢 | sign convention captured in the model |
| 55 | Freezing point → Ka | 🟢 | rounded options (3.06e−3 → 3e−3) |
| 56 | Ksp → solubility ratio (symbolic options) | 🔶 | needs symbolic-option support |
| 57 | Electrochemical cell statements | 🔶 | electrochemistry engine + statements |
| 58 | t100% vs t½ (zero/first order) | 🔶 | kinetics engine (limits) |
| 59 | Ionisation enthalpy order | 🔴 | periodic-trend rule base |
| 60 | Halogen oxidising power, layer test | 🔴 | qualitative inorganic rule base |
| 61 | Species reducing dichromate | 🔴 | redox rule base |
| 62 | CFSE Δ₀ matching | 🔴 | spectrochemical series rule base |
| 63 | Distillation statements | 🔴 | fact rule base |
| 64 | SN1 reactivity statements | 🔴 | organic mechanism rule base |
| 65 | IUPAC functional-group priority | 🔴 | nomenclature rule base |
| 66 | Electrophilic substitution site (figure) | 🔴 | organic structure (RDKit) + rules |
| 67 | Distinguishing tests matching | 🔴 | qualitative organic rule base |
| 68 | Azo coupling reactivity | 🔴 | organic structure + rules |
| 69 | Vitamins matching | 🔴 | fact rule base |
| 70 | Salt analysis | 🔴 | qualitative inorganic rule base |
| 71 | Complex + AgCl mole ratio | 🟢 | nearest integer (33.3 → 33) |
| 72 | C₅H₁₀ isomers, monochlorination count | 🔶 | structure enumeration (RDKit) |
| 73 | Alkane combustion | 🟢 | natural-number unknown → 17 |
| 74 | Arrhenius with given log values | 🟢 | uses the paper's approximations → 41 |
| 75 | Transition temperature | 🟢 | log₁₀, nearest integer → 727 |

## Summary

| Subject | ✅ + 🟢 today | 🔶 planned engine | 🔴 expert rule base |
|---|---|---|---|
| Maths (25) | 1 | 24 | 0 |
| Physics (25) | 17 | 7 | 1 (+1 partly) |
| Chemistry (25) | 9 | 4 | 12 |
| **Total (75)** | **27** | **35** | **13** |

## What this paper says to build next (by number of questions unlocked)

1. **Maths engines** (24 questions): vectors/3D, coordinate geometry and conics, calculus (limits, derivatives, integrals, ODEs), finite enumeration (counting, probability), matrices. Most are exact-computation problems the software can fully prove.
2. **Question formats** (about 8 questions): statement pairs (S1/S2, Statement I/II), ratio triples, options that are equations or expressions in letters.
3. **Chemistry rule base** (12 questions): periodic trends, qualitative inorganic, MO theory, CFT series, organic mechanisms, nomenclature. These are always teacher-reviewed; the software keeps them consistent and traceable.
4. **Figures**: dipoles, magnetic fields and optics, built like the circuit engine (geometry stored as data, figure drawn from it).
