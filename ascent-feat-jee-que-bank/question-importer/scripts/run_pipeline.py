"""
Master pipeline runner for question-importer.
Executes:
  1. extract_questions.py
  2. normalize_questions.py
  3. validate_questions.py
"""

import sys
import argparse
from extract_questions import extract_all_questions
from normalize_questions import normalize_questions_file
from validate_questions import run_validation

def main():
    parser = argparse.ArgumentParser(description="Ascent JEE Question Bank Ingestion Pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions to extract (default: all)")
    args = parser.parse_args()

    print("\n[STEP 1/3] Extracting raw questions from jee_data_base...")
    extract_all_questions(limit=args.limit)

    print("\n[STEP 2/3] Normalizing extracted questions...")
    normalize_questions_file()

    print("\n[STEP 3/3] Validating and summarizing canonical questions...")
    summary, valid, failed = run_validation()

    print("Pipeline run completed successfully!")

if __name__ == "__main__":
    main()

