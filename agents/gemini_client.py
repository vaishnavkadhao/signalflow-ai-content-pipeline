import os
import json
from typing import Optional

# Single source of truth for the default Gemini model.
# Override at any time with the GEMINI_MODEL environment variable.
_DEFAULT_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Safe error categories
# These strings are the ONLY thing that ever reaches logs or reports.
# Raw exception text is inspected privately and then discarded.
# ---------------------------------------------------------------------------
_CATEGORY_AUTH    = "invalid_api_key_or_auth"
_CATEGORY_QUOTA   = "quota_or_rate_limit"
_CATEGORY_MODEL   = "model_unavailable"
_CATEGORY_SCHEMA  = "structured_output_unsupported"
_CATEGORY_NETWORK = "network_or_timeout"
_CATEGORY_UNKNOWN = "unknown_provider_error"


def get_model_name() -> str:
    """Return the active model name (env override or built-in default)."""
    return os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL).strip()


def _classify_exception(exc: Exception) -> str:
    """
    Classify a Gemini / network exception into a safe diagnostic category.

    Inspects class name, numeric status codes, and a keyword allow-list
    against the lowercased exception message INTERNALLY.  The raw exception
    text is never printed or stored -- only the returned category string is
    safe to log.
    """
    type_name = type(exc).__name__.lower()

    # Numeric status code (safe integer attribute, never the key itself)
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    # Convert to int defensively
    try:
        status = int(status) if status is not None else None
    except (TypeError, ValueError):
        status = None

    # Build a lowercase message for keyword matching only -- NEVER logged.
    try:
        msg = str(exc).lower()
    except Exception:
        msg = ""

    # ── Auth / API-key errors ────────────────────────────────────────────
    if (
        status in (401, 403)
        or "permissiondenied" in type_name
        or "unauthenticated" in type_name
        or any(kw in msg for kw in [
            "api key", "api_key", "invalid key", "key not valid",
            "unauthenticated", "permission denied", "invalid credential",
        ])
    ):
        return _CATEGORY_AUTH

    # ── Quota / rate-limit errors ────────────────────────────────────────
    if (
        status == 429
        or "resourceexhausted" in type_name
        or any(kw in msg for kw in [
            "quota", "rate limit", "ratelimit", "resource exhausted",
            "too many requests", "429",
        ])
    ):
        return _CATEGORY_QUOTA

    # ── Structured-output / schema not supported ─────────────────────────
    # Check before model_unavailable because a 400 on schema can look like a
    # generic invalid-argument error.
    if any(kw in msg for kw in [
        "response_mime_type", "response_json_schema",
        "responsemimetype", "responsejsonschema",
        "structured output", "mime type", "schema",
        "invalidargument", "invalid argument",
    ]):
        return _CATEGORY_SCHEMA

    # ── Model not found ──────────────────────────────────────────────────
    if (
        status == 404
        or "notfound" in type_name
        or any(kw in msg for kw in [
            "model not found", "not found", "does not exist",
            "model_not_found", "no model", "404",
        ])
    ):
        return _CATEGORY_MODEL

    # ── Network / timeout / service unavailable ──────────────────────────
    if (
        status in (502, 503, 504)
        or any(t in type_name for t in [
            "timeout", "deadline", "serviceunavailable",
            "connectionerror", "urlerror",
        ])
        or any(kw in msg for kw in [
            "timeout", "timed out", "connection", "network",
            "deadline exceeded", "service unavailable",
            "502", "503", "504",
        ])
    ):
        return _CATEGORY_NETWORK

    return _CATEGORY_UNKNOWN


class GeminiClient:
    """
    Thin wrapper around google-genai SDK.

    Design rules:
    - Reads GEMINI_API_KEY from env only -- never accepted as a constructor arg
      so it cannot appear in stack traces, repr(), or logs.
    - generate() returns None on ANY failure; callers must fall back to templates.
    - Exceptions are caught broadly; only the safe category string is printed --
      raw exception text is classified internally and then discarded.
    - last_error_category exposes the most recently seen safe category so callers
      can surface diagnostics in reports without touching exception details.
    """

    def __init__(self) -> None:
        # Store only the boolean; the key itself stays in os.environ.
        self._has_key = bool(os.environ.get("GEMINI_API_KEY", "").strip())
        # Safe category of the last exception encountered (or None if no error).
        self.last_error_category: Optional[str] = None

    def is_available(self) -> bool:
        return self._has_key

    def generate(self, prompt: str, max_output_tokens: int = 2048) -> Optional[str]:
        """
        Send a plain-text prompt to Gemini and return the response text.
        Returns None on any failure; sets last_error_category.
        """
        if not self._has_key:
            return None

        try:
            from google import genai
            from google.genai import types

            key = os.environ.get("GEMINI_API_KEY", "")
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=get_model_name(),
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_output_tokens,
                    temperature=0.7,
                ),
            )
            return response.text
        except Exception as e:
            category = _classify_exception(e)
            self.last_error_category = category
            # Only the safe category string is printed -- never str(e).
            print(
                f"[Gemini] Provider error category: {category} "
                f"(model: {get_model_name()}) - falling back to template output"
            )
            return None

    def _try_structured(
        self,
        prompt: str,
        json_schema: dict,
        max_output_tokens: int = 2048,
    ) -> Optional[dict]:
        """
        Use Gemini's controlled generation (response_mime_type + response_json_schema)
        to force the model to emit valid JSON matching the given schema.
        Returns None if the API call fails; sets last_error_category.
        """
        if not self._has_key:
            return None

        try:
            from google import genai
            from google.genai import types

            key = os.environ.get("GEMINI_API_KEY", "")
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=get_model_name(),
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=json_schema,
                    max_output_tokens=max_output_tokens,
                    temperature=0.4,
                ),
            )
            text = (response.text or "").strip()
            if not text:
                return None
            return json.loads(text)
        except Exception as e:
            category = _classify_exception(e)
            self.last_error_category = category
            # Only the safe category string is printed -- never str(e).
            print(
                f"[Gemini] Provider error category: {category} "
                f"(model: {get_model_name()}, structured output) "
                "- trying plain text mode"
            )
            return None

    def _generate_json_once(
        self,
        prompt: str,
        max_output_tokens: int,
        json_schema: Optional[dict],
    ) -> Optional[dict]:
        """
        One attempt at JSON generation.

        Order of preference:
          1. Native structured output via response_json_schema (if schema provided).
          2. Plain text call + manual JSON parsing (fence-stripped).

        Returns the parsed dict, or None if both sub-paths fail.
        """
        # ── Sub-path 1: native structured output ─────────────────────────────
        if json_schema is not None:
            result = self._try_structured(prompt, json_schema, max_output_tokens)
            if result is not None:
                return result
            # Structured failed; fall through to plain text

        # ── Sub-path 2: plain text + manual parse ─────────────────────────────
        try:
            raw = self.generate(prompt, max_output_tokens=max_output_tokens)
        except Exception:
            print(
                "[Gemini] generate_json: unexpected error "
                "- falling back to template output"
            )
            return None

        if raw is None:
            return None

        text = raw.strip()

        # Strip ```json ... ``` fences that models sometimes add
        if text.startswith("```"):
            lines = text.split("\n")
            inner = lines[1:] if lines[0].startswith("```") else lines
            if inner and inner[-1].strip() == "```":
                inner = inner[:-1]
            text = "\n".join(inner).strip()

        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            print(
                "[Gemini] Response was not valid JSON "
                "- falling back to template output"
            )
            return None

    def generate_json(
        self,
        prompt: str,
        max_output_tokens: int = 2048,
        json_schema: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Call Gemini and return a parsed JSON dict.

        Makes up to 2 total attempts (structured output preferred, plain text
        fallback within each attempt).  A single retry fires automatically when
        the first attempt returns None to recover from transient API errors.

        last_error_category is updated on each failure so callers can surface
        diagnostics without touching exception details.

        Returns None only if both attempts fail.
        """
        if not self._has_key:
            return None

        for attempt in range(2):
            result = self._generate_json_once(prompt, max_output_tokens, json_schema)
            if result is not None:
                return result
            if attempt == 0:
                print(
                    "[Gemini] First attempt returned no result - retrying once..."
                )

        return None
