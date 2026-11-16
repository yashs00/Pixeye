# PIXEYE — JEE/NEET Question Bank

**PIXEYE** is an enterprise-grade full-stack Question Bank Management System built for JEE and NEET coaching institutes and test-series platforms.

It features an independent Python ingestion pipeline that extracts Previous Year Questions (PYQs) from `jee_data_base`, normalizes and validates them into a canonical structure, stores them in PostgreSQL with Prisma ORM, and serves them to teachers via a fast, reactive dashboard with KaTeX mathematical rendering and multi-question selection.

It also includes **Variant Studio**: a teacher picks a question and gets new, verified variants of it, each with the answer, a worked solution, and tricky options where every wrong option is the answer a student gets from one specific, named mistake.

---

## Architecture Overview

```
GitHub Repository (jee_mains_pyqs_data_base)
               |
               v
    Python Question Importer
  (inspect -> extract -> normalize -> validate)
               |
               v
      Canonical JSON Export
 (questions.json, import_summary.json)
               |
               v
   PostgreSQL 16 Database (Prisma ORM)
               |
               v
    Node.js Express REST APIs
               |
               v
    React Vite Teacher Dashboard  <---->  Variant Studio
                                             |
                          Node /api/variants (proxy)
                                             |
                                             v
                          CQSE engine service (Python, port 8765)
                     (find pattern -> generate -> solve two ways -> verify)
```

> **Key Design Decision:** The Python question importer is completely independent. The production Node.js backend does not depend on the Python runtime or any external library at runtime. Questions are imported into PostgreSQL once and fetched directly from our own database. The only Python service at runtime is the optional CQSE engine used by Variant Studio. If it isn't running, the rest of the app works normally and Variant Studio shows how to start it.

---

## Technology Stack

- **Frontend**: React 18, Vite, Tailwind CSS, React Router v6, Axios, Lucide React, TanStack Query (React Query v5), KaTeX, DOMPurify
- **Backend**: Node.js, Express.js, Prisma ORM 5.22, Morgan, CORS, Dotenv
- **Database**: PostgreSQL 16 (running via Docker or local service)
- **Question Extraction**: Python 3.14, `jee_data_base` (v0.2.2), Beautiful Soup 4, Requests
- **Variant engine (CQSE)**: Python 3, SymPy. Exact symbolic solving; the HTTP service uses only the standard library
- **Design**: dark neon theme (cyan `#22E4FF` → violet `#8257FF` → magenta `#FF3EC9` on `#0B0D14`), Inter + Plus Jakarta Sans, KaTeX for maths

---

## Design System

- **Dark everywhere.** The whole app is dark. Rather than rewriting every component, `tailwind.config.js` *inverts* the Tailwind colour scales (`50 ↔ 950`, `100 ↔ 900`, …) and remaps `bg-white` to the card surface. So `bg-white text-slate-900 border-slate-200` renders as a dark card with light text, unchanged in the source. When adding colour classes, remember the scale is inverted: use the **low** end (`emerald-50`, `amber-100`) for backgrounds and the **high** end (`emerald-700`) for text, exactly as you would on a light theme.
- **Accent.** `brand-*` is electric violet; `neon-btn`, `neon-text`, `neon-border`, `neon-tile` utilities in `index.css` give gradient buttons, gradient text, a gradient border and the logo tile. Green always means *correct*; amber always means *trap*.
- **Logo.** `components/common/PixeyeLogo.jsx` is a pure SVG eye with a pixel iris. The iris tracks the cursor (one shared `mousemove` listener, `requestAnimationFrame`-throttled), the eye blinks every ~6 s and the glow breathes. All motion is disabled under `prefers-reduced-motion`. The same mark is `public/favicon.svg`.
- **Motion.** Short, purposeful transitions (150–320 ms) defined as `vs-*` keyframes in `index.css`; variant cards rise in with a stagger, the verified badge pops, accepted cards fly into the tray.

---

## Dataset Statistics

From our real ingestion of the `jee_data_base` repository:
- **Total Questions Discovered & Imported:** `14,973`
- **Mathematics:** `4,788` questions
- **Physics:** `5,097` questions
- **Chemistry:** `5,088` questions
- **Question Types:**
  - Single Correct (MCQ): `11,687`
  - Numerical / Integer: `3,263`
  - Multiple Correct (MCQM): `23`
- **Questions Containing Images / Diagrams:** `4,590`
- **Exam Years:** `2002` through `2025`
- **Duplicate Prevention:** Enforced via `@@unique([sourceName, externalId])` (re-running imports produces 0 duplicates).

---

## Legal & Content Licensing Compliance

In accordance with redistribution and licensing governance:
1. **Provenance Metadata**: Every question records its origin (`HostServer001 JEE Database`), original chapter group, syllabus status, and source identifiers.
2. **Review Workflow Lifecycle**:
   - `PENDING_REVIEW`: Default status upon import for unverified third-party content.
   - `VERIFIED`: Explicitly authorized by teachers / administrators.
   - `REJECTED`: Removed from public question sets.
   - `UNPUBLISHED`: Kept in database but hidden from teacher-facing listings.
3. **Admin Verification**: Administrators can approve and publish questions individually or in bulk via the **Import History** dashboard or `POST /api/admin/imports/verify-all`.

---

## Variant Studio

Teachers generate new practice questions from an existing one, and every question shown has already been verified.

### Teacher flow
1. In the **Question Bank**, click **Make variants** on a question. The button appears on supported chapters.
2. The studio opens as a full-screen dark workspace. It shows the original on the left, with the matching **pattern** labelled honestly:
   - *Made from this question*
   - *Same kind of question*
   - *Related pattern*
   - If no pattern is close, a notice says so and the teacher picks one from the chapter.
3. Variants stream in on the right as they pass verification. Each card shows:
   - the correct option in green;
   - a **Trap** chip on every wrong option, which expands to *why students pick it* and *why it's wrong*;
   - a collapsible **worked solution**;
   - an originality score: how different its wording is from every question already in the bank.
4. **Accept / Reject / More like this.** Accepted variants collect in a tray, and **Save to bank** stores them as `PENDING_REVIEW`.

Keyboard: `J`/`K` move · `A` accept · `R` reject · `S` solution · `M` 3 more · `G` new batch · `?` help.

### How a variant is made
| Step | What happens |
|---|---|
| Pattern | A question type with fixed logic and variable parts (numbers, body/compound, wording), plus rules for valid values |
| New values | Random valid values are drawn; repeats and invalid combinations are skipped |
| Solve twice | The question becomes an exact model, solved by two independent methods (e.g. formula vs. listing every case, table vs. integration, rules vs. bond structure). Any disagreement means the variant is discarded |
| Tricky options | Each wrong option is the engine-computed answer of a named student mistake (e.g. "at most" read as "fewer than", sin/cos swapped). Options must be distinct, exactly one must be correct, and they are shuffled |
| Checks | Answer re-derived from the stored model, stem re-rendered from the model, near-copies of bank questions (≥ 85% word overlap) rejected |

**Guarantees**
- A variant that fails any check is never shown.
- On save, the backend ignores what the browser sends. It rebuilds and re-verifies each variant in the engine from its `(pattern, parameters, seed)` and stores the engine's copy.
- Nothing is published automatically: saved variants are `PENDING_REVIEW`. For some patterns a teacher also signs off once that the pattern's wording matches its model, shown as *Verified · sign-off pending*.

### Coverage
| Chapter | Patterns |
|---|---|
| Physics — Rotational Motion | 12 |
| Mathematics — Permutations And Combinations | 11 |
| Chemistry — Redox Reactions | 10 |

More chapters are added by writing new patterns in the engine. No frontend or backend change is needed.

### Running it
The engine is the separate **CQSE** Python project (not in this repository). From its directory:
```bash
python -m venv .venv && .venv/bin/pip install sympy
.venv/bin/python -m cqse.service            # http://127.0.0.1:8765
```
The backend finds it at `CQSE_URL` (default `http://127.0.0.1:8765`). If the backend runs in Docker, set `CQSE_URL=http://host.docker.internal:8765`.

---

## Directory Structure

```
pixeye/
├── frontend/                          # React + Vite Teacher Dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/                # Badges, Navbar, Sidebar, PixeyeLogo (animated SVG mark)
│   │   │   ├── dashboard/             # Real-time Stats Cards
│   │   │   ├── filters/               # Interactive Multi-filter Bar
│   │   │   └── questions/             # QuestionCard, PreviewModal, Drawer, Pagination
│   │   ├── context/                   # SelectionContext (persistent multi-question selection)
│   │   ├── pages/                     # QuestionBankPage, SelectedPage, ImportPage, Overview, Settings, VariantStudioPage
│   │   ├── services/                  # Axios API client
│   │   ├── utils/                     # KaTeX math parser & DOMPurify sanitizer
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── public/favicon.svg             # PIXEYE mark
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
│
├── backend/                           # Express.js REST APIs
│   ├── prisma/
│   │   └── schema.prisma              # Question, Subject, Chapter, Topic, ImportJob, Selection
│   ├── src/
│   │   ├── controllers/               # Questions, Filters, Stats, Selections, Admin Imports
│   │   ├── routes/                    # API routes (incl. variantRoutes.js -> CQSE engine)
│   │   ├── services/                  # Prisma service layer & Ingestion runner
│   │   ├── middleware/                # Error handler & validation
│   │   └── app.js                     # Express app setup
│   ├── scripts/import_generated.js    # Import a file of generated questions as PENDING_REVIEW
│   ├── .env                           # local only, git-ignored
│   ├── .env.example
│   └── package.json
│
├── question-importer/                 # Python Extraction & Normalization
│   ├── scripts/
│   │   ├── inspect_database.py        # Inspects jee_data_base methods & cache
│   │   ├── extract_questions.py       # Extracts raw questions into JSON
│   │   ├── normalize_questions.py     # Converts raw questions into canonical schema
│   │   ├── validate_questions.py      # Structural validation & summary report
│   │   └── run_pipeline.py            # Unified CLI runner
│   ├── exports/                       # questions.json, import_summary.json, failed_questions.json
│   ├── logs/                          # extraction.log
│   ├── requirements.txt
│   └── README.md
│
├── docker-compose.yml
└── README.md
```

---

## Quick Start & Setup Instructions

### 1. Database Setup
Start PostgreSQL container:
```bash
docker run -d --name que-bank -e POSTGRES_PASSWORD=admin123 -e POSTGRES_DB=que_bank -p 5432:5432 postgres:16
```
Or start via `docker-compose up -d postgres`.

### 2. Python Question Importer
```bash
cd question-importer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run complete extraction and normalization pipeline
python scripts/run_pipeline.py
```
This generates `question-importer/exports/questions.json` with all 14,973 validated questions.

### 3. Backend Setup & Ingestion
```bash
cd backend
npm install

# Push Prisma schema to PostgreSQL
npx prisma db push

# Ingest canonical questions into PostgreSQL
npm run import:data

# Start backend development server (Runs on port 5001)
npm run dev
```

### 4. Frontend Setup
```bash
cd frontend
npm install

# Start Vite dev server (Runs on port 5173 with proxy to backend)
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser.

### 5. Variant Studio (optional)
Start the CQSE engine service (see [Variant Studio → Running it](#running-it)), then click **Make variants** on any Rotational Motion, Permutations And Combinations or Redox Reactions question.

### Environment variables (backend)
| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `PORT` | `5000` | API port (docker-compose uses `5001`) |
| `CQSE_URL` | `http://127.0.0.1:8765` | Variant engine service |

Copy `backend/.env.example` to `backend/.env`. Never commit `.env`; it is git-ignored.

---

## REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check & total question count |
| `GET` | `/api/questions` | Paginated questions (`search`, `exam`, `subject`, `chapter`, `topic`, `year`, `difficulty`, `questionType`, `page`, `limit`, `sortBy`, `sortOrder`) |
| `GET` | `/api/questions/:id` | Full question details with options, solution & explanation |
| `GET` | `/api/questions/statistics` | Real-time question counts by subject, year, type, difficulty & top chapters |
| `GET` | `/api/filters/subjects` | Distinct subjects with question counts |
| `GET` | `/api/filters/chapters?subject=PHYSICS` | Dynamic chapters for selected subject |
| `GET` | `/api/filters/topics?chapter=...` | Dynamic topics for selected chapter |
| `GET` | `/api/filters/years` | Available exam years (2002–2025) |
| `GET` | `/api/filters/difficulties` | Available difficulty levels |
| `GET` | `/api/filters/types` | Available question types |
| `GET` | `/api/selections?sessionId=...` | Retrieve selected question session & distribution stats |
| `POST` | `/api/selections` | Add question(s) to selection |
| `DELETE`| `/api/selections/:questionId` | Remove question from selection |
| `DELETE`| `/api/selections` | Clear selection |
| `GET` | `/api/admin/imports` | List import job logs |
| `POST` | `/api/admin/imports` | Trigger new incremental import |
| `POST` | `/api/admin/imports/verify-all` | Verify & publish all pending review questions |
| `GET` | `/api/variants/health` | Variant engine status and number of patterns |
| `POST` | `/api/variants/match` | `{ questionId }` → patterns for this question, best first, with match tier |
| `POST` | `/api/variants/generate` | `{ family, n, seed, exclude }` → NDJSON stream, one verified variant per line |
| `POST` | `/api/variants/accept` | `{ parentId, items: [{ family, params, seed }] }` → re-verifies and saves as `PENDING_REVIEW` |

---

## Known Limitations
- Variant Studio covers three chapters so far. Other chapters show no **Make variants** button.
- Pattern matching for a selected question is based on word overlap. The teacher can always choose another pattern from the chapter.
- The main app's sidebar does not collapse on phone-width screens yet. Variant Studio is full-screen and unaffected.
- The theme is dark only; there is no light-mode toggle.
- Question diagrams come from a light-background source and are shown on a small white tile so they stay legible.
