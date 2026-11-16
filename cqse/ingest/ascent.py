"""Importer for the 'ascent' question-bank JSON export (HostServer001 / ExamGoal-style records).

Converts each record to the CQSE PYQRecord JSONL format WITHOUT inventing anything:
  * HTML -> plain text; LaTeX kept as written; <sub>/<sup> kept as _ / ^.
  * Any image in the question or options -> flagged; the text alone is not the full question.
  * correctAnswers -> answer_key (key_source "provisional": a third-party database, not the official key).
  * NUMERICAL records with no stored answer -> answer_key null (the value inside the explanation is
    NOT extracted automatically: explanations in this export are sometimes wrong).
  * rights_status UNKNOWN unless the caller clears it with a recorded basis (--rights/--basis).
Also tags each question's STYLE, used for coverage planning.
"""
from __future__ import annotations

import html as htmllib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

FORMAT = {"MCQ_SINGLE": "single_correct_mcq", "MCQ_MULTIPLE": "multiple_correct_mcq",
          "NUMERICAL": "numerical_integer", "INTEGER": "numerical_integer"}


def html_to_text(s: str) -> tuple[str, int]:
    """Return (text, number_of_images)."""
    if not s:
        return "", 0
    n_img = len(re.findall(r"<img\b", s, re.I))
    # Protect LaTeX first: "x<-1 ... >" inside $...$ must not be mistaken for an HTML tag.
    maths: list[str] = []

    def _keep(m: re.Match) -> str:
        inner = re.sub(r"<br\s*/?>|</?(?:b|i|p|span|strong|em|sub|sup)\b[^>]*>", " ", m.group(0), flags=re.I)
        maths.append(htmllib.unescape(inner))
        return f"\x00{len(maths) - 1}\x00"
    s = re.sub(r"\$\$.*?\$\$|\$[^$]*\$", _keep, s, flags=re.S)
    s = re.sub(r"<style\b.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<img\b[^>]*>", " [IMAGE] ", s, flags=re.I)
    s = re.sub(r"<sub>(.*?)</sub>", r"_\1", s, flags=re.S | re.I)
    s = re.sub(r"<sup>(.*?)</sup>", r"^\1", s, flags=re.S | re.I)
    s = re.sub(r"</(p|tr|li|h\d)>|<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</t[dh]>", " | ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: maths[int(m.group(1))], s)
    return s.strip(), n_img


def question_style(text: str, fmt: str) -> str:
    t = text.lower()
    if "statement (i)" in t or "statement i" in t or "two statements" in t:
        return "statement_pair"
    if "match list" in t or "match the list" in t or "list - i" in t or "list-i" in t:
        return "match_list"
    if re.search(r"choose the correct answer from the options", t) and re.search(r"\(a\)|\ba\.", t):
        return "select_combination"
    if "order" in t or "arrange" in t:
        return "ordering"
    if fmt.startswith("numerical") or re.search(r"\d", t) and re.search(r"calculate|mass of|molar|emf|ph\b|current", t):
        return "calculation"
    return "concept_mcq"


ALL_USES = ["storage", "search", "derive", "display", "export", "training", "llm"]


def normalize_export(rec: dict[str, Any]) -> dict[str, Any]:
    """Accept both the Prisma-row export (camelCase) and the snake_case bulk export (all_questions.json)."""
    if "questionContent" in rec:
        return rec
    src = rec.get("source") or {}
    expl = rec.get("explanation")
    return {
        "id": rec.get("id") or rec.get("external_id"), "externalId": rec.get("external_id"),
        "sourceName": src.get("name", "ascent") if isinstance(src, dict) else str(src),
        "exam": rec.get("exam"), "subject": rec.get("subject"), "chapter": rec.get("chapter"),
        "topic": rec.get("topic"), "year": rec.get("year"), "paperTitle": rec.get("paper_title"),
        "difficulty": rec.get("difficulty"), "questionType": rec.get("type"),
        "questionContent": rec.get("question") or {}, "options": rec.get("options") or [],
        "correctAnswers": rec.get("correct_answers") or [], "answer": rec.get("answer"),
        "explanation": {"format": "html", "content": expl} if isinstance(expl, str) else expl,
        "media": rec.get("media") or [], "sourceMetadata": src if isinstance(src, dict) else {},
        "reviewStatus": rec.get("review_status"),
    }


def convert(rec: dict[str, Any], rights: str = "UNKNOWN", uses: list[str] | None = None,
            basis: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    rec = normalize_export(rec)
    stem, n_q = html_to_text((rec.get("questionContent") or {}).get("content", ""))
    opts, n_o = [], 0
    for o in rec.get("options") or []:
        txt, k = html_to_text(o.get("content", ""))
        n_o += k
        opts.append({"id": o["id"], "text": txt})
    fmt = FORMAT.get(rec.get("questionType", ""), "single_correct_mcq")
    keys = rec.get("correctAnswers") or []
    key = (keys[0] if len(keys) == 1 else keys) if keys else (rec.get("answer") or None)
    unresolved = []
    if n_q:
        unresolved.append(f"{n_q} image(s) in the question")
    if n_o:
        unresolved.append(f"{n_o} image(s) in the options")
    out = {
        "pyq_id": f"ASCENT-{rec.get('externalId') or rec['id']}",
        "exam": rec.get("exam", "UNKNOWN"), "year": int(rec.get("year") or 0),
        "shift": rec.get("paperTitle"), "subject": rec.get("subject", "CHEMISTRY"),
        "chapter": rec.get("chapter", ""), "topic": rec.get("topic", ""),
        "question_format": fmt, "stem": stem, "options": opts,
        "answer_key": key, "key_source": "provisional",
        "numerical_rounding": "nearest_integer" if fmt == "numerical_integer" else None,
        "solution": html_to_text((rec.get("explanation") or {}).get("content", ""))[0] or None,
        "source": {"document": f"{rec.get('sourceName', 'ascent')} / {rec.get('paperTitle', '')}",
                   "rights_status": rights, "permitted_uses": uses or ["storage", "search"],
                   "rights_basis": basis},
        "extraction": {"method": "digital_text", "visual_review_done": not unresolved,
                       "unresolved_fragments": unresolved},
        "diagram_files": [m["url"] for m in rec.get("media") or [] if m.get("location") != "explanation"],
    }
    meta = {"style": question_style(stem, fmt), "images": n_q + n_o, "key_missing": key is None,
            "difficulty": rec.get("difficulty"), "chapter": rec.get("chapter", "")}
    return out, meta


def import_file(src: Path, dst: Path, rights: str = "UNKNOWN", uses: list[str] | None = None,
                basis: str | None = None) -> dict[str, Any]:
    if rights in ("CLEARED", "TEACHER_OWNED") and not basis:
        raise ValueError("clearing rights needs a basis (who confirmed it, and when)")
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    metas = []
    with open(dst, "w", encoding="utf-8") as fh:
        for rec in data:
            out, meta = convert(rec, rights, uses, basis)
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
            metas.append(meta)
    return {
        "records": len(metas),
        "image_dependent": sum(1 for m in metas if m["images"]),
        "numerical_without_key": sum(1 for m in metas if m["key_missing"]),
        "by_style": dict(Counter(m["style"] for m in metas).most_common()),
        "by_chapter": dict(Counter(m["chapter"] for m in metas).most_common()),
        "by_difficulty": dict(Counter(m["difficulty"] for m in metas).most_common()),
    }
