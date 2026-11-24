"""Shared Foundation Model API client for the enrichment engine.

Uses the OpenAI-compatible interface exposed by Databricks Model Serving
(`<host>/serving-endpoints`). Works both locally (token from the CLI) and inside
Databricks Apps / notebooks (token from the runtime).

Exposes:
    chat_json(system, user, ...)  -> dict   (JSON-mode chat, parsed + validated)
    chat(messages, ...)           -> str
    embed(texts)                  -> list[list[float]]

The client is lazily created so importing this module never triggers auth.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Any

from common.config import CFG


def _host() -> str:
    return os.environ.get("DATABRICKS_HOST", CFG.host).rstrip("/")


@lru_cache(maxsize=1)
def _client():
    """OpenAI-compatible client for Databricks FMAPI.

    Order of preference: explicit DATABRICKS_TOKEN env -> Databricks SDK
    (service principal inside an App) -> local CLI token.
    """
    from openai import OpenAI
    tok = os.environ.get("DATABRICKS_TOKEN")
    if tok:
        return OpenAI(api_key=tok, base_url=f"{_host()}/serving-endpoints")
    try:  # Databricks App / notebook runtime
        from databricks.sdk import WorkspaceClient
        return WorkspaceClient().serving_endpoints.get_open_ai_client()
    except Exception:
        pass
    from common.dbx import workspace_token  # local CLI fallback
    return OpenAI(api_key=workspace_token(), base_url=f"{_host()}/serving-endpoints")


def chat(messages: list[dict], *, model: str | None = None, temperature: float | None = None,
         max_tokens: int = 1024, **kw) -> str:
    model = model or CFG.models["chat_endpoint"]
    # Some Databricks-hosted Anthropic endpoints reject `temperature`; only send
    # it when explicitly requested.
    if temperature is not None:
        kw["temperature"] = temperature
    resp = _client().chat.completions.create(
        model=model, messages=messages, max_tokens=max_tokens, **kw,
    )
    return resp.choices[0].message.content or ""


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction from an LLM response (handles code fences / prose)."""
    text = text.strip()
    # strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # grab the first balanced {...} block
        start = text.find("{")
        if start >= 0:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return json.loads(text[start:i + 1])
        raise


_JSON_GUARD = ("\n\nIMPORTANT: Respond with a SINGLE valid JSON object and nothing else "
               "— no markdown, no code fences, no commentary.")


def chat_json(system: str, user: str, *, model: str | None = None,
              temperature: float | None = None, max_tokens: int = 1024,
              retries: int = 2) -> dict:
    """Prompt-driven JSON chat. Returns a parsed dict. Retries on malformed JSON.

    Databricks' newer Anthropic endpoints reject forced `response_format`, so we
    rely on a strict instruction plus best-effort JSON extraction/validation.
    """
    messages = [{"role": "system", "content": system + _JSON_GUARD},
                {"role": "user", "content": user}]
    last_err: Exception | None = None
    for _ in range(retries + 1):
        try:
            raw = chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
            return _extract_json(raw)
        except Exception as e:  # noqa: BLE001 - robustness is the point
            last_err = e
            messages.append({"role": "assistant", "content": "(invalid)"})
            messages.append({"role": "user",
                             "content": "That was not valid JSON. Return ONLY one JSON object."})
    raise RuntimeError(f"chat_json failed after {retries + 1} attempts: {last_err}")


def embed(texts: list[str], *, model: str | None = None) -> list[list[float]]:
    model = model or CFG.models["embedding_endpoint"]
    resp = _client().embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]
