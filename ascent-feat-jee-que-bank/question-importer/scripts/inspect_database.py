"""
Inspect the jee_data_base package, initialize the database, print metadata,
and extract sample questions.
"""
import sys
import os
import json

def inspect_db():
    print("Python version:", sys.version)
    print("Importing jee_data_base...")
    from jee_data_base import DataBase

    print("Initializing DataBase()...")
    db = DataBase()
    print("DataBase successfully initialized!")
    print("DB Representation:")
    print(db)
    print("Attributes in db:", dir(db))
    print("Total chapters in db.chapters_dict:", len(db.chapters_dict))

    # Examine subjects
    subjects = set()
    total_questions = 0
    chapter_info = []

    for chap_name, chap_obj in db.chapters_dict.items():
        subjects.add(chap_obj.parent_subject)
        q_count = len(chap_obj.question_dict)
        total_questions += q_count
        chapter_info.append({
            "chapter_key": chap_name,
            "chapter_name": chap_obj.name,
            "subject": chap_obj.parent_subject,
            "question_count": q_count
        })

    print(f"Distinct Subjects ({len(subjects)}):", subjects)
    print(f"Total Accessible Questions across all chapters: {total_questions}")
    print(f"Sample chapters (first 5): {chapter_info[:5]}")

    # Inspect 5 sample questions in detail
    sample_questions = []
    count = 0
    for chap_name, chap_obj in db.chapters_dict.items():
        for q_idx, q in chap_obj.question_dict.items():
            q_dict = {k: v for k, v in q.__dict__.items() if not k.startswith('_')}
            sample_questions.append(q_dict)
            count += 1
            if count >= 10:
                break
        if count >= 10:
            break

    print("\n--- SAMPLE QUESTION 1 RAW ATTRIBUTES ---")
    if sample_questions:
        q1 = sample_questions[0]
        for k, v in q1.items():
            v_str = str(v)
            if len(v_str) > 200:
                v_str = v_str[:200] + "... [truncated]"
            print(f"  {k}: {v_str}")

    # Write sample questions to JSON for Phase 1 inspection
    os.makedirs("question-importer/exports", exist_ok=True)
    with open("question-importer/exports/sample_10_raw_questions.json", "w", encoding="utf-8") as f:
        json.dump(sample_questions, f, indent=2, default=str)
    print("\nSaved 10 sample raw questions to question-importer/exports/sample_10_raw_questions.json")

if __name__ == "__main__":
    inspect_db()

