"""The single doorway to the Claude API.

call() order:  local cache  ->  budget check (worst-case estimate)  ->  API call
               (cached frozen system prompt, structured JSON output, per-task effort)
               ->  usage recorded  ->  result cached.
batch() does the same for many items through the Message Batches API (50% off).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Optional

from cqse.llm.cache import ResultCache, cache_key
from cqse.llm.config import FALLBACK_BETA, PRICES, TASKS, USE_FALLBACKS
from cqse.llm.ledger import Ledger
from cqse.llm.prompts import OUTPUT_SCHEMA, PROMPT_VERSION, SYSTEM_FORMALIZE

SYSTEMS = {"formalize": SYSTEM_FORMALIZE}
SCHEMAS = {"formalize": OUTPUT_SCHEMA}


@dataclass
class LLMResult:
    ok: bool
    data: Optional[dict]
    error: str = ""
    from_cache: bool = False


def _rough_tokens(text: str) -> int:
    return len(text) // 3 + 1  # deliberately pessimistic (real ratio is closer to 4 chars/token)


class Gateway:
    def __init__(self, client: Any = None, ledger: Optional[Ledger] = None, cache: Optional[ResultCache] = None):
        if client is None:
            import anthropic  # resolves ANTHROPIC_API_KEY / ant auth profile; never hard-code a key
            client = anthropic.Anthropic()
        self.client = client
        self.ledger = ledger or Ledger()
        self.cache = cache or ResultCache()

    # ------------------------------------------------------------------ helpers
    def _params(self, task: str, user: str, effort: Optional[str]) -> dict:
        prof = TASKS[task]
        return dict(
            model=prof.model,
            max_tokens=prof.max_tokens,
            # Frozen system prompt marked for caching: every call after the first reads it at ~5% price.
            system=[{"type": "text", "text": SYSTEMS[task], "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={"effort": effort or prof.effort,
                           "format": {"type": "json_schema", "schema": SCHEMAS[task]}},
        )

    def _estimate(self, task: str, user: str) -> float:
        prof = TASKS[task]
        p = PRICES[prof.model]
        sys_t, user_t = _rough_tokens(SYSTEMS[task]), _rough_tokens(user)
        # worst case: system prompt is a cache WRITE and the full max_tokens is used
        return (sys_t * p["cache_write"] + user_t * p["in"] + prof.max_tokens * p["out"]) / 1e6

    @staticmethod
    def _parse(msg) -> LLMResult:
        if msg.stop_reason == "refusal":
            return LLMResult(False, None, "model declined the request (refusal)")
        if msg.stop_reason == "max_tokens":
            return LLMResult(False, None, "output truncated at max_tokens")
        text = next((b.text for b in msg.content if getattr(b, "type", "") == "text"), None)
        if text is None:
            return LLMResult(False, None, "no text block in response")
        try:
            return LLMResult(True, json.loads(text))
        except json.JSONDecodeError as e:
            return LLMResult(False, None, f"invalid JSON: {e}")

    # ------------------------------------------------------------------ single call
    def call(self, task: str, payload: dict, user: str, effort: Optional[str] = None) -> LLMResult:
        prof = TASKS[task]
        eff = effort or prof.effort
        key = cache_key(task, PROMPT_VERSION, prof.model, eff, {"payload": payload, "user": user})
        hit = self.cache.get(key)
        if hit is not None:
            self.ledger.saved_by_cache += 1
            return LLMResult(True, hit, from_cache=True)
        self.ledger.check(self._estimate(task, user))
        params = self._params(task, user, eff)
        if USE_FALLBACKS:
            msg = self.client.beta.messages.create(**params, betas=[FALLBACK_BETA], fallbacks="default")
        else:
            msg = self.client.messages.create(**params)
        self.ledger.record(task, getattr(msg, "model", prof.model) or prof.model, key, msg.usage)
        res = self._parse(msg)
        if res.ok:
            self.cache.put(key, res.data)
        return res

    # ------------------------------------------------------------------ batch
    def batch(self, task: str, items: list[tuple[str, dict, str]], poll_seconds: int = 30,
              timeout_s: int = 26 * 3600) -> dict[str, LLMResult]:
        """items: (custom_id, payload, user_message). Cached items never reach the API."""
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
        from anthropic.types.messages.batch_create_params import Request

        prof = TASKS[task]
        out: dict[str, LLMResult] = {}
        pending: list[tuple[str, str, str]] = []  # (custom_id, cache key, user)
        for cid, payload, user in items:
            key = cache_key(task, PROMPT_VERSION, prof.model, prof.effort, {"payload": payload, "user": user})
            hit = self.cache.get(key)
            if hit is not None:
                self.ledger.saved_by_cache += 1
                out[cid] = LLMResult(True, hit, from_cache=True)
            else:
                pending.append((cid, key, user))
        if not pending:
            return out
        self.ledger.check(sum(self._estimate(task, u) for _, _, u in pending) * 0.5)
        reqs = [Request(custom_id=cid, params=MessageCreateParamsNonStreaming(**self._params(task, u, None)))
                for cid, _, u in pending]
        b = self.client.messages.batches.create(requests=reqs)
        start = time.time()
        while True:
            b = self.client.messages.batches.retrieve(b.id)
            if b.processing_status == "ended":
                break
            if time.time() - start > timeout_s:
                raise TimeoutError(f"batch {b.id} not finished; results can be fetched later")
            time.sleep(poll_seconds)
        keys = {cid: key for cid, key, _ in pending}
        for r in self.client.messages.batches.results(b.id):  # results arrive in any order: key by custom_id
            cid = r.custom_id
            if r.result.type == "succeeded":
                msg = r.result.message
                self.ledger.record(task, msg.model or prof.model, keys[cid], msg.usage, batch=True)
                res = self._parse(msg)
                if res.ok:
                    self.cache.put(keys[cid], res.data)
                out[cid] = res
            else:
                out[cid] = LLMResult(False, None, f"batch result {r.result.type}")
        return out
