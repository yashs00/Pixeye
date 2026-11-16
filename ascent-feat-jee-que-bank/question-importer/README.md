# Ascent - JEE Question Bank Extraction Pipeline

This utility extracts, normalizes, and validates Previous Year Questions (PYQs) from the `jee_data_base` package for Ascent's Question Bank.

## Overview
- **Source**: HostServer001 `jee_mains_pyqs_data_base`
- **Output**: Canonical JSON schema (`questions.json`, `import_summary.json`, `failed_questions.json`)
- **Traceability**: Original fields are preserved in `source` metadata.
- **Content Review Status**: All questions are imported with `PENDING_REVIEW` by default in compliance with redistribution and licensing requirements.

## Directory Structure
```
question-importer/
├── scripts/
│   ├── inspect_database.py     # Inspects package API and sample records
│   ├── extract_questions.py    # Extracts raw questions into raw_questions.json
│   ├── normalize_questions.py  # Converts raw data into canonical Ascent schema
│   ├── validate_questions.py   # Validates structure, IDs, media, and outputs summary
│   └── run_pipeline.py         # Unified runner
├── exports/
│   ├── questions.json          # Valid canonical questions ready for PostgreSQL ingestion
│   ├── import_summary.json     # Statistics (subject, year, type, images)
│   ├── failed_questions.json   # Dropped or invalid items with error logs
│   └── raw_questions.json      # Complete raw records
├── logs/
│   └── extraction.log          # Detailed extraction logs
├── requirements.txt
└── README.md
```

## Setup & Running
1. Set up virtual environment and install requirements:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run database inspection:
   ```bash
   python scripts/inspect_database.py
   ```
3. Run extraction pipeline:
   ```bash
   # Extract sample (e.g. 100 questions)
   python scripts/run_pipeline.py --limit 100

   # Extract all accessible questions (~14,973)
   python scripts/run_pipeline.py
   ```

