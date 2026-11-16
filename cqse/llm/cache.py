"""Local result cache (SQLite): the same question is never paid for twice.

Key = sha256(task, prompt version, model, effort, normalised input). Changing
the prompt version or model naturally invalidates old entries.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

DEFAULT_PATH = Path(".cqse_cache") / "llm_results.sqlite"


def cache_key(task: str, prompt_version: str, model: str, effort: str, payload: dict) -> str:
    blob = json.dumps({"t": task, "v": prompt_version, "m": model, "e": effort, "p": payload},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ResultCache:
    def __init__(self, path: Optional[Path] = DEFAULT_PATH):
        self.path = path
        if path is None:
            self._mem: dict[str, Any] = {}
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS results (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

    def get(self, key: str) -> Optional[Any]:
        if self.path is None:
            return self._mem.get(key)
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT value FROM results WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, value: Any) -> None:
        if self.path is None:
            self._mem[key] = value
            return
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO results (key, value) VALUES (?, ?)", (key, json.dumps(value)))
