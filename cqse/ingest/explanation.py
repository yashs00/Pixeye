"""Read the final numerical value stated in a database explanation.

This is NOT an answer key: explanations are sometimes wrong. The value is used only as a reference to compare
the engine's independent result against, and is labelled with how explicitly the explanation stated it:
  high    "Ans. 33", "answer is 6", "\\boxed{23}", "x is equal to 32", "value of x is 15"
  medium  the explanation's last line ends with "= <number>" (or "≃"/"≈")
  None    no clear final number (e.g. "No solution", a symbolic result)
"""
from __future__ import annotations

import re
from typing import Optional

_NUM = r"[-−]?\s*\d+(?:\.\d+)?"
_HIGH = [
    rf"\bans(?:wer)?\b\s*(?:is|=|:|\.)?\s*(?:\$+)?\s*({_NUM})",
    rf"\banswer\s+is\s+(?:\$+)?\s*({_NUM})",
    rf"\\boxed\{{\s*({_NUM})",
    rf"\b(?:is|are)\s+equal\s+to\s+(?:\$+)?\s*({_NUM})",
    rf"\bvalue\s+of\s+\$*\s*[a-zA-Z]\w*\s*\$*\s+is\s+(?:\$+)?\s*({_NUM})",
    rf"\bcorrect\s+answer\s*(?:is|:)?\s*({_NUM})",
    rf"\bnearest\s+integer\s*(?:is|=|:)?\s*({_NUM})",
]


def _plain(html: str) -> str:
    t = re.sub(r"<[^>]+>", " ", html or "")
    t = re.sub(r"\\(?:mathrm|text|mathbf|rm)\s*\{([^{}]*)\}", r"\1", t)
    t = t.replace("&nbsp;", " ").replace("−", "-")
    return re.sub(r"[ \t]+", " ", t)


def _clean(n: str) -> str:
    n = n.replace(" ", "").replace("−", "-")
    return n[:-2] if n.endswith(".0") else n


def final_value(explanation: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """(value, confidence) where confidence is "high", "medium" or None."""
    t = _plain(explanation or "")
    if not t.strip():
        return None, None
    tail = t[-600:]
    for pat in _HIGH:
        hits = list(re.finditer(pat, tail, re.I))
        if hits:
            return _clean(hits[-1].group(1)), "high"
    end = re.sub(r"\\(?:begin|end)\{[a-z*]+\}|\$|&|\\\\|\\quad|\\therefore|\\Rightarrow", " ", tail[-260:])
    end = end.replace("[IMAGE]", " ")
    end = re.sub(r"\^\s*(?:\{\s*\\circ\s*\}|\\circ)", "°", end)
    end = re.sub(r"\{\s*([-\d.]+°?)\s*\}", r"\1", end)          # {57} / {57°} -> 57
    hits = list(re.finditer(rf"(?:=|≃|≈|\\simeq|\\approx)\s*({_NUM})(?![\d.])", end))
    if hits:
        rest = end[hits[-1].end():].replace("\\%", "%").replace("^\\circ", "°")
        # only a unit / short word may follow the final number (no further maths)
        if len(rest.strip()) <= 25 and re.fullmatch(r"[A-Za-z°%/\s.,()]*", rest.replace("\\mathrm", "")):
            return _clean(hits[-1].group(1)), "medium"
    m = re.search(rf"\b(?:is|be|are)\s+({_NUM})\s*(?:%|°|[A-Za-z/]{{0,8}})?\s*\.?\s*$", end.strip())
    if m:  # "... the mass percent of the solute is 22% ."
        return _clean(m.group(1)), "medium"
    return None, None
