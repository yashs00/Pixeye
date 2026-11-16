# CQSE — Conceptual Question Search Engine (verifier-first core)

This is an implementation of the *PCM Chess-Engine Question Generation Blueprint v2*. It covers Phases 0–3 plus the release controls from Part XIV, with one bounded pilot topic per subject.

> **Status: not production-certified.** No generated item is student-facing until a qualified teacher approves it (blueprint §33, §40). The system **fails closed**: a timeout, a solver error, solvers that disagree, or a check that cannot be decided all block release.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                       # verifier regression suite
.venv/bin/python -m cqse profiles                   # exam profiles and their governance status
.venv/bin/python -m cqse ingest data/samples/pyq_sample.jsonl --out ingest_report.json
.venv/bin/python -m cqse search --subject MATHEMATICS \
  --formal '{"kind":"equation","lhs":"x**2-x-6","rhs":"0","var":"x","domain":"reals","target":"sum"}'
```

## What is implemented

| Blueprint part | Module | What it does |
|---|---|---|
| §3 formal state, §11 distractors | `cqse/core/problem.py` | Typed `ProblemState`, `Distractor` with derivation trace, student view vs teacher view |
| §34 typed evidence | `cqse/core/evidence.py` | `PROVED / EXACT_CHECKED / NUMERICALLY_CHECKED / RULE_CHECKED / EXPERT_REVIEWED / NOT_APPLICABLE / UNRESOLVED / FAILED`; empty report never passes; timeouts/exceptions → UNRESOLVED |
| §6, §37.1 Mathematics | `cqse/math/` | Whitelisted parser (no code execution); definedness conditions extracted from the **unevaluated** tree (so `x/x` keeps x≠0); solver A = `solveset`, solver B = cleared-numerator `real_roots` (or a bracketed numeric scan, flagged for second review); exact back-substitution into the original equation; disagreement → UNRESOLVED |
| §7, §37.2 Physics | `cqse/physics/engine.py` | Level-ground projectile; block on a rough incline. Two independent derivations each (EOM vs closed form; regime formulas vs Newton with static-first bound check); friction regime decided first, exact threshold → FAILED; Pint dimensional check; limiting cases |
| §8, §37.3 Chemistry | `cqse/chemistry/engine.py` | Formula parser (brackets, hydrates, charges); exact nullspace balancer that **refuses non-unique balancings**; atom + charge recount; limiting reagent by two methods; mass conservation; atomic masses only as stated in the stem; **reaction feasibility is always UNRESOLVED until a chemist attests with a source** |
| §36 option/key contract | `cqse/verification/options.py` | Every option evaluated individually; equivalent forms detected (`1/2` = `0.5`, `sqrt(8)` = `2*sqrt(2)`); cardinality; declared key vs derived key; numerical-integer answers must be exact integers |
| §11, §38 misconception distractors | `cqse/math/misconceptions.py`, `physics`, `chemistry` | Executable error operations with traces. A distractor is kept only if it is provably wrong and distinct from the other options. **Assembly refuses to pad with random values** |
| §16–17 exam profiles | `cqse/exam/` | Versioned YAML with source URL and status. Only `OFFICIAL` profiles are usable; `HISTORICAL_BASELINE` needs an explicit override; `PROVISIONAL` (JEE Adv 2027) is blocked |
| §4 search, §2 move catalogue | `cqse/search/` | Typed operators (parameter, domain, target, rational/radical extraneous-root traps, friction-regime flip, reagent rescale), beam search, transposition table, diverse top-k. **Every child is re-verified from scratch** |
| §9, §35 PYQ ingestion | `cqse/ingest/pyq.py` | Source key treated as a claim; routing to NEEDS_SOURCE / NEEDS_VISUAL_REVIEW / NEEDS_FORMALIZATION / QUARANTINED_KEY_DISAGREEMENT / duplicate groups |
| §21, §33, §40, §42 release | `cqse/release/workflow.py` | Software verification and teacher approval kept separate; 12-point rubric; subject-qualified reviewers; a second independent reviewer for chemistry, generated or high-stakes items; any edit invalidates approvals; published versions immutable; suspend → corrected new version with a change log; audit trail |
| §41 regression | `tests/` | 140 tests, including 13 defect mutations × 5 item types (wrong key, hidden second correct answer, equivalent duplicate option, edited stem, changed givens, missing trace, wrong units, bad or provisional profile, …). Target: zero false accepts |

## Adding your PYQ dataset

Put one question per line in a JSONL file (see `data/samples/pyq_sample.jsonl`):

```json
{
  "pyq_id": "JEEMAIN-2024-0127-S1-M-12",
  "exam": "JEE_MAIN", "year": 2024, "shift": "27 Jan S1",
  "subject": "MATHEMATICS", "chapter": "Quadratic Equations", "topic": "roots",
  "question_format": "single_correct_mcq",
  "stem": "exact question text as printed",
  "options": [{"id": "A", "text": "as printed", "value": "machine-readable exact value e.g. 2*sqrt(3) or {1, 6}"}],
  "answer_key": "B",
  "official_correction": null,
  "solution": "optional",
  "source": {"document": "file.pdf", "page": 12, "rights_status": "TEACHER_OWNED",
             "permitted_uses": ["storage", "search", "derive", "display"]},
  "extraction": {"method": "manual | digital_text | ocr", "confidence": 0.97, "visual_review_done": true},
  "formal": { "kind": "equation", "lhs": "...", "rhs": "...", "var": "x", "domain": "reals", "target": "sum" },
  "diagram_files": []
}
```

* `formal` is optional. Without it a question is still stored and searchable, but it is marked `NEEDS_FORMALIZATION`. The system never guesses a formal state from the prose.
* Formal kinds supported now: `equation` (math), `projectile_level` and `incline_friction` (physics), `stoichiometry` (chemistry). Other topics are stored and routed to experts until an engine for them exists.
* `rights_status: UNKNOWN` means internal search only. Nothing is derived, displayed or trained from that question.

## Honest limitations (read before using with students)

* **"Zero errors" cannot be guaranteed by software.** The suite shows zero false accepts on known defect types. That does not prove every possible defect is caught. The real safeguard is the full chain: verification, then teacher review, then monitoring, then transparent correction.
* Pilot coverage is narrow: single-variable real equations; two physics models; stoichiometry. Organic and inorganic chemistry, assertion–reason, diagrams, matrix-match and multi-concept physics are **not yet modelled**. Those items are routed to experts.
* The numeric cross-check for non-polynomial equations searches only [-200, 200]. It is marked as evidence, not proof, and flags the item for a second review.
* Exam-profile facts are copied from the blueprint's 14 Nov 2026 research check. An in-house reviewer must re-verify them against the official PDFs.
* Stem rendering uses deterministic templates (English, ASCII math). A human must confirm that any hand-written or source stem matches its formal state.
* Answer-position balancing, paper-level assembly checks, IRT calibration and the teacher UI are later phases (blueprint Phases 5–7).

## Claude API layer (`cqse/llm/`)

Claude is used for one job: **drafting the machine-readable `formal` state** from a question's text. Turning prose into structure is the bottleneck that blocks automatic checking. Claude never decides what is correct. Every draft goes through the same verifier as a hand-written formal state, and a teacher still confirms it.

```bash
export ANTHROPIC_API_KEY=...        # or: ant auth login   (never put the key in code or in chat)
.venv/bin/python -m cqse formalize data/samples/pyq_sample.jsonl --dry-run       # no API use: shows calls and worst-case cost
.venv/bin/python -m cqse formalize data/samples/pyq_sample.jsonl --budget-usd 1  # real run, hard spending cap
.venv/bin/python -m cqse formalize big_dataset.jsonl --batch --budget-usd 20      # bulk: Batches API, 50% cheaper
```

**How tokens are saved** (cheapest first):

| Step | Saving |
|---|---|
| Questions that already have a formal state, lack `"llm"` in `permitted_uses`, have unreviewed OCR text, or match no supported type (free keyword triage) | No call at all |
| Questions with identical text in one run | One call, result shared |
| Local SQLite result cache (`.cqse_cache/`) | The same question is never paid for twice across runs |
| Frozen system prompt with `cache_control` | Every call after the first reads the ~1.5k-token instructions at about 5% of the input price |
| `--batch` | 50% off for bulk jobs |
| Effort `medium`, raised to `high` only for one retry after a structural rejection | No over-thinking on easy items |
| Minimal input (stem and options only) and a strict JSON schema output | No wasted input, no parse-retry loops |
| Budget ledger (`llm_usage.jsonl`) | A call is refused *before* it is sent if its worst-case cost would break `--budget-usd` |

**Safety rules built in:**
- The answer key is never sent. So when the solver's answer to Claude's draft matches the printed key, the two pieces of evidence really are independent.
- A key disagreement is **not retried**. Feeding the disagreement back would push the model to fit the key. Instead the question is quarantined, and a teacher sees both answers.
- Drafts are tagged `LLM_DRAFT_NEEDS_TEACHER_CHECK`.
- The model defaults to Claude Opus 5.5 (`CQSE_LLM_MODEL` overrides it). Server-side fallback is on for live calls when a request is declined; `CQSE_LLM_FALLBACKS=0` turns it off. If you switch to a cheaper model, first measure it on a sample of your own past-paper questions.

## General calculation checker and circuits

| Kind | What the software proves | What a teacher still confirms |
|---|---|---|
| `equation_system` (any calculation question, multi-concept) | Units consistent term by term; exact unit conversion; exactly one admissible answer; exact back-substitution; numeric cross-check | That the equations model the stem (`model.correspondence`), that the generated wrong options are realistic; two reviewers required |
| `circuit_dc` (netlist) | Equations written by the software (exact MNA); network non-singular; **certificate**: KCL at every node + every element law + Tellegen power balance; series/parallel reduction cross-check for Req; diagram drawn from the netlist and re-checked | Nothing beyond normal review (for a scanned source figure: that the netlist matches it) |

Circuit diagrams are generated SVG schematics (`item.diagram_svg`). The renderer picks the node order with the fewest crossings, draws parallel branches as arcs, routes unavoidable crossings (such as a Wheatstone bridge) as outer loops, and uses standard symbols. The diagram is part of the approved content: editing it cancels approval, and a diagram that disagrees with the netlist blocks the question.

## Engines added for the 300-question ascent set (2026-11-15)

| kind | module | covers |
|---|---|---|
| `statement_set` | cqse/verification/formats.py | "A, D and E only", Statement I/II, Assertion–Reason, Match List, ordering; option text parsed automatically |
| `area_region`, `extrema`, `calculus_value` | cqse/math/calculus.py | areas from inequalities, local/absolute extrema, monotonicity, parameter conditions |
| `geometry3d` | cqse/math/geometry3d.py | lines/planes, foot/image, shortest distance, areas, triangle centres, conics |
| `series_sum`, `statistics` | cqse/math/series_stats.py | AP/GP/recurrences/finite & infinite sums, mean/variance/median/MD |
| `chem_property` | cqse/chemistry/rules.py | configurations (with exceptions), unpaired e⁻, spin-only μ, VSEPR, MO diatomics, Lewis counts, molar mass, electrode potentials |

Engines register in `cqse/engines.py`. Each answer needs two independent methods (or a versioned rule set); anything else fails closed.

Run the whole dataset: `python data/pyq/run_formals.py` → `out/ascent300_report.json` (one file: `--only <formals stem>`).
Formalizations: `data/pyq/formals/*.py`. Rights for the ascent set: CLEARED, recorded basis "owner, 2026-11-15".
