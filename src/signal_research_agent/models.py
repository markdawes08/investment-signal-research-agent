"""Shared serialization and explicit research boundaries."""

import hashlib
import json

SAFETY_NOTICES = (
    "Offline MVP",
    "Deterministic synthetic data",
    "Historical research only",
    "Not investment advice",
    "No trade execution",
    "Not evidence of future performance",
)


def scope_notices(mode="offline"):
    """Keep the legacy offline label, while accurately naming network/replay modes."""
    if mode == "offline":
        return SAFETY_NOTICES
    labels = {"llm": "LLM-assisted research MVP", "replay": "Deterministic saved-specification replay"}
    if mode not in labels:
        raise ResearchError("Unknown execution mode")
    return (labels[mode], *SAFETY_NOTICES[1:], "Not evidence about real markets")


class ResearchError(ValueError):
    """An expected research gate or unsupported specification failure."""


def canonical_json(value):
    """Canonical local JSON: finite numbers, sorted keys, compact UTF-8."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def content_hash(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
