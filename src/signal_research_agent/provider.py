"""Optional OpenAI Responses adapter with explicit, sanitized failure statuses.

No SDK import or credential access occurs during offline module import. The
Coordinator owns the four-call budget; SDK retries are explicitly disabled.
"""

from __future__ import annotations

from importlib import import_module
import json
import math
import os
import re

from .llm_design import (MAX_CONTEXT_CHARS, MAX_OUTPUT_CHARS, PROPOSAL_SCHEMA,
                         SCHEMA_VERSION, SYSTEM_INSTRUCTIONS)
from .models import canonical_json

DEFAULT_MODEL = "gpt-4.1-mini-2025-04-14"


def _safe_identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}", value):
        return None
    if value.lower().startswith(("sk-", "ghp_", "gho_", "bearer")):
        return None
    return value


def _usage(value):
    fields = ("input_tokens", "output_tokens", "total_tokens")
    counts = {key: getattr(value, key, None) for key in fields} if value is not None else {}
    return counts if counts and all(type(count) is int and count >= 0 for count in counts.values()) else None


def _strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key.")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("Nonfinite JSON value.")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=reject_constant)


class OpenAIProvider:
    """One bounded provider attempt; only application-observed metadata is saved."""

    def __init__(self, model=None, timeout=30, max_output_tokens=2500):
        requested = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL) if model is None else model
        if _safe_identifier(requested) is None:
            raise ValueError("Model identifier must be a public model name without sensitive characters.")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 1 <= timeout <= 30:
            raise ValueError("Provider timeout must be between 1 and 30 seconds.")
        if type(max_output_tokens) is not int or not 256 <= max_output_tokens <= 4000:
            raise ValueError("Provider output token limit must be between 256 and 4000.")
        self.model = requested
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens

    def generate(self, context: dict) -> dict:
        metadata = {"provider": "openai", "requested_model": self.model,
                    "actual_model": None, "response_id": None, "usage": None,
                    "actual_provider_call": False, "status": None, "cost_usd": None}

        def result(status, output=None):
            metadata["status"] = status
            return {"status": status, "output": output, "metadata": metadata}

        try:
            serialized = canonical_json(context)
        except (TypeError, ValueError, OverflowError, RecursionError):
            return result("invalid_context")
        if not isinstance(context, dict) or len(serialized) > MAX_CONTEXT_CHARS:
            return result("context_limit_exceeded")
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            return result("missing_credentials")
        try:
            sdk = import_module("openai")
        except ImportError:
            return result("provider_unavailable")
        client = None
        try:
            client = sdk.OpenAI(api_key=key, base_url="https://api.openai.com/v1",
                                timeout=self.timeout, max_retries=0)
            metadata["actual_provider_call"] = True
            response = client.responses.create(
                model=self.model, instructions=SYSTEM_INSTRUCTIONS,
                input=[{"role": "user", "content": serialized}],
                text={"format": {"type": "json_schema", "name": SCHEMA_VERSION.replace("-", "_"),
                                 "strict": True, "schema": PROPOSAL_SCHEMA}},
                max_output_tokens=self.max_output_tokens, store=False,
            )
            metadata["actual_model"] = _safe_identifier(getattr(response, "model", None))
            metadata["response_id"] = _safe_identifier(getattr(response, "id", None))
            metadata["usage"] = _usage(getattr(response, "usage", None))
            if getattr(response, "status", None) != "completed":
                return result("provider_incomplete")
            output_text = getattr(response, "output_text", None)
            if not isinstance(output_text, str) or not output_text.strip():
                return result("malformed_output")
            if len(output_text) > MAX_OUTPUT_CHARS:
                return result("output_limit_exceeded")
            try:
                output = _strict_json(output_text)
            except (ValueError, TypeError, OverflowError, RecursionError):
                return result("malformed_output")
            if not isinstance(output, dict):
                return result("malformed_output")
            return result("completed", output)
        except Exception as error:
            # Never retain the exception text, request, authentication headers,
            # credential, refusal payload, or provider's raw response body.
            timeout_class = getattr(sdk, "APITimeoutError", ())
            if isinstance(error, TimeoutError) or (isinstance(timeout_class, type) and isinstance(error, timeout_class)):
                return result("provider_timeout")
            return result("provider_error")
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
