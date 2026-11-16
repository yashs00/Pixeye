"""
Extract raw questions from jee_data_base into JSON format.
Preserves all original fields and extracts media references.
"""

import os
import re
import sys
import json
import logging
from datetime import datetime

# Setup logging
log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "extraction.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("QuestionExtractor")

def extract_image_urls(text):
    """Extract all image URLs from HTML and markdown format within a text block."""
    if not text or not isinstance(text, str):
        return []
    urls = []
    # HTML <img ... src="...">
    html_matches = re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', text, re.IGNORECASE)
    urls.extend(html_matches)
    # Markdown ![...](...)
    md_matches = re.findall(r'!\[.*?\]\((https?://[^\s)]+)\)', text)
    urls.extend(md_matches)
    return list(dict.fromkeys(urls))  # unique preserving order

def extract_all_questions(limit=None):
    """
    Extract questions from jee_data_base DataBase instance.
    :param limit: Optional integer to limit questions for testing.
    """
    logger.info("Initializing jee_data_base DataBase...")
    from jee_data_base import DataBase

    db = DataBase()
    total_chapters = len(db.chapters_dict)
    logger.info("Loaded DataBase with %d chapters", total_chapters)

    discovered_count = 0
    extracted_questions = []
    failed_questions = []

    for chap_idx, (chap_key, chapter_obj) in enumerate(db.chapters_dict.items(), start=1):
        subject_name = getattr(chapter_obj, "parent_subject", "Unknown")
        chapter_name = getattr(chapter_obj, "name", chap_key)
        q_dict = getattr(chapter_obj, "question_dict", {})
        
        logger.info(
            "[%d/%d] Processing chapter '%s' (%s) with %d questions",
            chap_idx, total_chapters, chapter_name, subject_name, len(q_dict)
        )

        for q_key, q in q_dict.items():
            discovered_count += 1
            try:
                # Raw attributes
                qid = getattr(q, "question_id", None) or f"{chap_key}_{q_key}"
                exam = getattr(q, "exam", "jee-main")
                subject = getattr(q, "subject", subject_name)
                chapter_val = getattr(q, "chapter", chapter_name)
                chapter_group = getattr(q, "chpaterGroup", None) or getattr(q, "chapterGroup", None) or ""
                topic = getattr(q, "topic", "")
                year = getattr(q, "year", None)
                exam_date = getattr(q, "examDate", None)
                paper_title = getattr(q, "paperTitle", None)
                difficulty = getattr(q, "difficulty", None)
                q_type = getattr(q, "type", "mcq")
                answer = getattr(q, "answer", None)
                q_content = getattr(q, "question", "")
                options = getattr(q, "options", [])
                correct_options = getattr(q, "correct_options", [])
                explanation = getattr(q, "explanation", "")
                is_out_of_syllabus = getattr(q, "isOutOfSyllabus", False)
                is_bonus = getattr(q, "isBonus", False)
                is_img_q = getattr(q, "isImgQuestion", False)
                is_img_exp = getattr(q, "isImgExplanation", False)
                is_img_opt = getattr(q, "isImgOption", [])

                # Extract media references
                media_list = []
                q_imgs = extract_image_urls(q_content)
                for img_url in q_imgs:
                    media_list.append({"url": img_url, "location": "question", "optionId": None})

                if isinstance(options, list):
                    for opt in options:
                        opt_id = opt.get("identifier") or opt.get("id")
                        opt_content = opt.get("content", "")
                        for img_url in extract_image_urls(opt_content):
                            media_list.append({"url": img_url, "location": "option", "optionId": opt_id})

                exp_imgs = extract_image_urls(explanation)
                for img_url in exp_imgs:
                    media_list.append({"url": img_url, "location": "explanation", "optionId": None})

                raw_record = {
                    "question_id": qid,
                    "exam": exam,
                    "subject": subject,
                    "chapter": chapter_val,
                    "chapterGroup": chapter_group,
                    "topic": topic,
                    "year": int(year) if year and str(year).isdigit() else 0,
                    "examDate": exam_date,
                    "paperTitle": paper_title,
                    "difficulty": difficulty,
                    "type": q_type,
                    "question": q_content,
                    "options": options,
                    "correct_options": correct_options,
                    "answer": answer,
                    "explanation": explanation,
                    "isOutOfSyllabus": bool(is_out_of_syllabus),
                    "isBonus": bool(is_bonus),
                    "isImgQuestion": bool(is_img_q),
                    "isImgExplanation": bool(is_img_exp),
                    "isImgOption": is_img_opt,
                    "media": media_list,
                    "extracted_at": datetime.utcnow().isoformat()
                }

                extracted_questions.append(raw_record)

                if limit and len(extracted_questions) >= limit:
                    logger.info("Reached limit of %d questions. Stopping extraction.", limit)
                    break

            except Exception as ex:
                logger.error("Failed to extract question %s: %s", getattr(q, "question_id", "unknown"), str(ex))
                failed_questions.append({
                    "question_id": getattr(q, "question_id", "unknown"),
                    "chapter": chapter_name,
                    "error": str(ex)
                })

        if limit and len(extracted_questions) >= limit:
            break

    logger.info(
        "Extraction finished. Discovered: %d, Successfully Extracted: %d, Failed: %d",
        discovered_count, len(extracted_questions), len(failed_questions)
    )

    exports_dir = os.path.join(os.path.dirname(__file__), "..", "exports")
    os.makedirs(exports_dir, exist_ok=True)
    raw_path = os.path.join(exports_dir, "raw_questions.json")
    failed_path = os.path.join(exports_dir, "failed_questions.json")

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(extracted_questions, f, indent=2, default=str)
    logger.info("Saved raw questions to %s", raw_path)

    if failed_questions:
        with open(failed_path, "w", encoding="utf-8") as f:
            json.dump(failed_questions, f, indent=2)
        logger.info("Saved %d failed question errors to %s", len(failed_questions), failed_path)

    return extracted_questions, failed_questions, discovered_count

if __name__ == "__main__":
    limit_val = int(sys.argv[1]) if len(sys.argv) > 1 else None
    extract_all_questions(limit=limit_val)

