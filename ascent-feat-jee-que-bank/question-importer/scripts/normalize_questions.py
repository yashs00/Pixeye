"""
Normalization layer for extracted questions.
Converts raw external questions into canonical Ascent Question schema.
"""

import os
import re
import sys
import json
import logging

log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QuestionNormalizer")

SUBJECT_MAP = {
    "physics": "PHYSICS",
    "chem": "CHEMISTRY",
    "chemistry": "CHEMISTRY",
    "math": "MATHEMATICS",
    "maths": "MATHEMATICS",
    "mathematics": "MATHEMATICS",
    "biology": "BIOLOGY"
}

DIFFICULTY_MAP = {
    "easy": "EASY",
    "medium": "MEDIUM",
    "hard": "HARD",
    "unknown": "UNKNOWN"
}

TYPE_MAP = {
    "mcq": "MCQ_SINGLE",
    "mcqm": "MCQ_MULTIPLE",
    "integer": "NUMERICAL",
    "numerical": "NUMERICAL",
    "single": "MCQ_SINGLE",
    "multiple": "MCQ_MULTIPLE"
}

EXAM_MAP = {
    "jee-main": "JEE_MAIN",
    "jee_main": "JEE_MAIN",
    "jee": "JEE_MAIN",
    "jee-advanced": "JEE_ADVANCED",
    "jee_advanced": "JEE_ADVANCED",
    "neet": "NEET"
}

def humanize_slug(slug):
    """Convert 'trigonometric-ratio-and-identites' to title case 'Trigonometric Ratio And Identites'"""
    if not slug:
        return "General"
    words = str(slug).replace("_", "-").split("-")
    return " ".join(word.capitalize() for word in words if word)

def normalize_single_question(raw_q):
    """
    Transform raw question dictionary into normalized canonical question.
    """
    raw_subject = str(raw_q.get("subject") or "").strip().lower()
    subject = SUBJECT_MAP.get(raw_subject, raw_subject.upper() if raw_subject else "GENERAL")

    raw_exam = str(raw_q.get("exam") or "").strip().lower()
    exam = EXAM_MAP.get(raw_exam, "JEE_MAIN")

    raw_difficulty = str(raw_q.get("difficulty") or "").strip().lower()
    difficulty = DIFFICULTY_MAP.get(raw_difficulty, "UNKNOWN")

    raw_type = str(raw_q.get("type") or "").strip().lower()
    q_type = TYPE_MAP.get(raw_type, "MCQ_SINGLE")

    raw_chapter = raw_q.get("chapter") or "General"
    chapter = humanize_slug(raw_chapter)

    raw_topic = raw_q.get("topic") or "General"
    topic = humanize_slug(raw_topic)

    # Normalize options
    raw_options = raw_q.get("options") or []
    normalized_options = []
    if isinstance(raw_options, list):
        for idx, opt in enumerate(raw_options):
            if isinstance(opt, dict):
                opt_id = opt.get("identifier") or opt.get("id") or chr(65 + idx)
                opt_content = opt.get("content") or ""
                normalized_options.append({
                    "id": str(opt_id).strip(),
                    "content": str(opt_content).strip()
                })
            elif isinstance(opt, str):
                normalized_options.append({
                    "id": chr(65 + idx),
                    "content": opt.strip()
                })

    # Normalize correct answers
    raw_correct = raw_q.get("correct_options") or []
    if isinstance(raw_correct, list):
        correct_answers = [str(ans).strip() for ans in raw_correct if ans is not None]
    elif raw_correct:
        correct_answers = [str(raw_correct).strip()]
    else:
        correct_answers = []

    year_val = raw_q.get("year")
    try:
        year_num = int(year_val) if year_val else 0
    except (ValueError, TypeError):
        year_num = 0

    question_content = raw_q.get("question") or ""

    normalized_record = {
        "external_id": str(raw_q.get("question_id") or "").strip(),
        "exam": exam,
        "subject": subject,
        "chapter": chapter,
        "topic": topic,
        "year": year_num,
        "paper_title": raw_q.get("paperTitle"),
        "difficulty": difficulty,
        "type": q_type,
        "question": {
            "format": "html",
            "content": question_content
        },
        "options": normalized_options,
        "correct_answers": correct_answers,
        "answer": raw_q.get("answer"),
        "explanation": raw_q.get("explanation") or "",
        "media": raw_q.get("media") or [],
        "review_status": "PENDING_REVIEW",  # Legal compliance: unverified by default
        "source": {
            "name": "HostServer001 JEE Database",
            "year": year_num,
            "original_subject": raw_q.get("subject"),
            "original_chapter": raw_q.get("chapter"),
            "original_topic": raw_q.get("topic"),
            "original_type": raw_q.get("type"),
            "original_difficulty": raw_q.get("difficulty"),
            "chapter_group": raw_q.get("chapterGroup"),
            "is_out_of_syllabus": raw_q.get("isOutOfSyllabus", False),
            "is_bonus": raw_q.get("isBonus", False)
        }
    }

    return normalized_record

def normalize_questions_file(input_file=None, output_file=None):
    base_dir = os.path.dirname(__file__)
    if not input_file:
        input_file = os.path.join(base_dir, "..", "exports", "raw_questions.json")
    if not output_file:
        output_file = os.path.join(base_dir, "..", "exports", "normalized_questions.json")

    logger.info("Reading raw questions from %s", input_file)
    with open(input_file, "r", encoding="utf-8") as f:
        raw_list = json.load(f)

    logger.info("Normalizing %d questions...", len(raw_list))
    normalized_list = []
    for raw_q in raw_list:
        norm_q = normalize_single_question(raw_q)
        normalized_list.append(norm_q)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(normalized_list, f, indent=2, default=str)

    logger.info("Successfully normalized %d questions to %s", len(normalized_list), output_file)
    return normalized_list

if __name__ == "__main__":
    normalize_questions_file()

