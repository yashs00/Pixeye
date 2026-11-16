# First-pass review: ascent 300-question set (chem / maths / phy)

This review was done by hand from the pasted files. The files are not on disk yet, so the engine has not run on them.
"Key OK" means I re-derived the answer and it matches the database key. Each item is identified by its externalId.

## Keys that are wrong or questions that are flawed

| id | subject | problem | action |
|---|---|---|---|
| m9gxgcl8 | phy | Assertion: "O²⁻ has smaller curvature than H⁺" at equal momentum. r = p/(qB), so O²⁻ has the smaller radius, which means the larger curvature. Read literally, the assertion is false. The reason (a proton bends more than an electron at equal momentum) is false too: equal charge magnitude gives equal radius. "Both false" is not an option. The key C only works if "curvature" is read as "radius of curvature". | Quarantine; needs official key |
| m9ghxmzt | phy | v_ring/v_sphere = √(7/10) = √(3.5/5), so x = 3.5. That is not an integer, and the stem has no "nearest integer" instruction. The explanation rounds it to 4 on its own. | Quarantine; needs official key |
| m9e5j1on | maths | Key B (4) is correct, but the explanation writes a+(2n+1)d where it should be a+(2n−1)d. | Fix explanation |

## Key correct, explanation wrong (do not show these explanations to students)

- m9fnut39 (phy): the explanation computes λ = 2 m, but 2·3.14·300/628 = 3 m. The key C (3 m) is correct.
- m6ulvixl (maths): the explanation says S₆ = 15p and p = 3, then "5×5 = 25". The correct working is S₆ = 9p, p = 5, giving 25.
- m9fnuqsf (maths): the explanation finds a second solution (λ = −1/3, μ = 1). That solution is spurious, because λμ = −3 is forced. The unique answer is 8.
- m9dr3ju6 (maths): the explanation writes L₁'s direction as (1,1,2); it is actually (1,1,1). The answer 147 is still correct.
- m9gxgc3j (maths): the factorisation in the explanation is wrong. The correct equation is c²(2c²−1) = 0, which gives β = π/2 or π/4. The answer 3π/4 is still correct.
- m6rp6kg1 (phy): the explanation uses 0.01 m for wire X; it should be 0.10 m. The answer 1 is still correct.
- m9dunojt (phy): the explanation calls the wheel a "solid disk" but uses I = MR², which is a ring. The answer 20 is still correct.
- m9ghxn8x (chem): the explanation writes V³⁺ where it means V²⁺ (found earlier).
- m9dmr7qo (maths): the explanation writes f′ = (x²−3)/3x² where it should be (x²−9)/3x².

## Missing answers (no key and no value stated in the text)

- m9ghxn2p (phy, capacitor figure)
- m6t9yk0p (chem, sp³ count, image only)

All other numerical items have an empty key field. The value has to be read from the explanation and treated as provisional.

## Ambiguities to note in the teacher review

- m9ghxnaj (chem): the electrode naming during charging follows a convention.
- m9e5jawj (chem): assumes inert electrodes.
- m6w9ofqf (chem): the explanation invents numbers that are not in the graph.
- m6srn9ar (phy): the sign of dI/dt depends on the figure (R increasing, so dI/dt = −8).
- m9e8b438 (phy): "minimum distance with the same speed" is λ/2 only if "same speed" means at all times.
- m9e5j9ov (chem): SO₂ fits "4:1" only if π bond pairs are counted.
- m6ulvdu9 (chem): the stem says ribose, but DNA contains deoxyribose.
- m9do8yt4 (phy): the answer is a 40 m disc. The algebra is correct but the scenario is unphysical.

## Re-derived: key OK

- **Maths:** all calculation items checked (calculus, area, AP/GP/series, statistics, 3D, conics). The only exceptions are the explanation issues listed above.
- **Physics:** all text-only items checked.
- **Chemistry:** the configuration, magnetic-moment, VSEPR and electrochemistry items checked.

## Machine re-check (data/pyq/verify_ascent300_calcs.py)

18 items were written as equations and solved by the general checker. 17 of them match the database key or the value stated in the explanation.
The one that does not match, m9ghxmzt, solves to exactly x = 3.5, which is ambiguous because there is no rounding rule.

- m9fnuqsf: the checker proves λ = −1, μ = 3 is the only solution, which confirms the explanation's second root is spurious.
- m9dunp3y: E°(Q/QH₂) = 0.70 V was read from the stem image, so a teacher must confirm it.

## Import summary (after files saved to project root)

| subject | records | image-dependent | numericals without a key | chapters |
|---|---|---|---|---|
| chem | 100 | 28 | 16 | Electrochemistry 21, Bonding 20, Biomolecules 20, N-compounds 20, d/f-block 19 |
| maths | 100 | 0 | 16 | Sequences & Series 27, 3D 27, Area 18, AOD 14, Statistics 8, Hyperbola 4, Triangle 2 |
| phy | 100 | 28 | 29 | Rotation 26, Magnetics 22, Capacitor 15, Waves 11, Wave Optics 11, EMI 8, Laws of Motion 7 |

On import, every record is still NEEDS_FORMALIZATION and NEEDS_SOURCE (rights unknown); none has been formalized automatically.

## Full engine run (data/pyq/run_formals.py, 27 s for all 300)

| subject | verified (fully computed) | verified (teacher confirm) | flagged | left out (image-only) |
|---|---|---|---|---|
| chem | 26 | 47 | 1 (m9ghxnaj: no option correct under the standard convention) | 26 |
| maths | 32 | 68 | 0 | 0 |
| phy | 0 | 76 | 2 (m9gxgcl8: no option correct; m9ghxmzt: answer 3.5, no rounding rule) | 22 |

"Teacher confirm" means the key agrees with the engine, but a curated fact or the write-up of the equations still needs a teacher's sign-off.
