"""
Validation layer and summary generator for normalized questions.
Validates structural integrity, generates questions.json and import_summary.json.
"""

import os
import sys
import json
import logging
from collections import Counter, defaultdict

log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QuestionValidator")

VALID_TYPES = {"MCQ_SINGLE", "MCQ_MULTIPLE", "NUMERICAL", "INTEGER", "OTHER"}
VALID_SUBJECTS = {"PHYSICS", "CHEMISTRY", "MATHEMATICS", "BIOLOGY", "GENERAL"}
VALID_DIFFICULTIES = {"EASY", "MEDIUM", "HARD", "UNKNOWN"}

def validate_question(q, seen_ids):
    """
    Validates a canonical normalized question dict.
    Returns (is_valid: bool, issues: list[str])
    """
    issues = []
    ext_id = q.get("external_id")
    if not ext_id:
        issues.append("Missing external_id")
    elif ext_id in seen_ids:
        issues.append(f"Duplicate external_id: {ext_id}")

    # Content check
    q_obj = q.get("question") or {}
    q_content = q_obj.get("content", "").strip() if isinstance(q_obj, dict) else str(q_obj).strip()
    if not q_content:
        issues.append("Question statement content is empty")

    # Subject check
    subj = q.get("subject")
    if not subj or subj not in VALID_SUBJECTS:
        issues.append(f"Invalid or missing subject: {subj}")

    # Type check
    q_type = q.get("type")
    if not q_type or q_type not in VALID_TYPES:
        issues.append(f"Invalid or unrecognized question type: {q_type}")

    # Difficulty check
    diff = q.get("difficulty")
    if not diff or diff not in VALID_DIFFICULTIES:
        issues.append(f"Invalid difficulty: {diff}")

    # Options & correct answers check
    options = q.get("options") or []
    correct_answers = q.get("correct_answers") or []
    if q_type in {"MCQ_SINGLE", "MCQ_MULTIPLE"}:
        if not options:
            issues.append(f"MCQ has empty options list")
        else:
            opt_ids = {opt.get("id") for opt in options if isinstance(opt, dict)}
            for ca in correct_answers:
                if ca not in opt_ids:
                    issues.append(f"Correct answer '{ca}' not found in option IDs: {opt_ids}")

    return len(issues) == 0, issues

def run_validation(input_file=None):
    base_dir = os.path.dirname(__file__)
    exports_dir = os.path.join(base_dir, "..", "exports")
    if not input_file:
        input_file = os.path.join(exports_dir, "normalized_questions.json")

    logger.info("Loading normalized questions from %s", input_file)
    with open(input_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    seen_ids = set()
    valid_questions = []
    failed_questions = []
    missing_metadata_count = 0
    with_images_count = 0

    subject_counts = Counter()
    year_counts = Counter()
    type_counts = Counter()
    difficulty_counts = Counter()

    for idx, q in enumerate(questions):
        ext_id = q.get("external_id")
        is_valid, issues = validate_question(q, seen_ids)
        
        # Check metadata
        if not q.get("topic") or not q.get("chapter") or not q.get("year"):
            missing_metadata_count += 1

        media_count = len(q.get("media") or [])
        if media_count > 0:
            with_images_count += 1

        if is_valid:
            seen_ids.add(ext_id)
            valid_questions.append(q)
            subject_counts[q.get("subject")] += 1
            year_counts[str(q.get("year"))] += 1
            type_counts[q.get("type")] += 1
            difficulty_counts[q.get("difficulty")] += 1
        else:
            failed_questions.append({
                "external_id": ext_id,
                "index": idx,
                "issues": issues,
                "raw_snippet": str(q)[:200]
            })

    # Generate summary
    summary = {
        "total_questions_discovered": len(questions),
        "total_questions_successfully_extracted": len(valid_questions),
        "total_questions_skipped": len(failed_questions),
        "total_questions_with_missing_metadata": missing_metadata_count,
        "total_questions_containing_images": with_images_count,
        "questions_grouped_by_subject": dict(subject_counts),
        "questions_grouped_by_year": dict(sorted(year_counts.items(), key=lambda x: str(x[0]))),
        "questions_grouped_by_question_type": dict(type_counts),
        "questions_grouped_by_difficulty": dict(difficulty_counts)
    }

    # Write files
    final_questions_path = os.path.join(exports_dir, "questions.json")
    summary_path = os.path.join(exports_dir, "import_summary.json")
    failed_path = os.path.join(exports_dir, "failed_questions.json")

    with open(final_questions_path, "w", encoding="utf-8") as f:
        json.dump(valid_questions, f, indent=2, default=str)
    logger.info("Wrote %d valid canonical questions to %s", len(valid_questions), final_questions_path)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    logger.info("Wrote import summary to %s", summary_path)

    with open(failed_path, "w", encoding="utf-8") as f:
        json.dump(failed_questions, f, indent=2)
    logger.info("Wrote %d failed question logs to %s", len(failed_questions), failed_path)

    print("\n================ IMPORT SUMMARY ================")
    print(f"Total Discovered: {summary['total_questions_discovered']}")
    print(f"Total Successfully Validated: {summary['total_questions_successfully_extracted']}")
    print(f"Total Skipped/Failed: {summary['total_questions_skipped']}")
    print(f"Questions with Images: {summary['total_questions_containing_images']}")
    print(f"Subject Distribution: {summary['questions_grouped_by_subject']}")
    print(f"Type Distribution: {summary['questions_grouped_by_question_type']}")
    print(f"Difficulty Distribution: {summary['questions_grouped_by_difficulty']}")
    print("================================================\n")

    return summary, valid_questions, failed_questions

if __name__ == "__main__":
    run_validation()

