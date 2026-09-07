"""Append-only JSONL journals with independently verifiable SHA-256 chains.

Integrity checks detect edits against the present chain. Without an external
checkpoint, they cannot detect deletion of a valid tail or a rewritten chain.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import canonical_json, content_hash


GENESIS_HASH = "0" * 64


def verify_entries(entries: list[dict]) -> bool:
    """Validate exact entry shape, sequence numbers, links, and payload hashes."""
    previous = GENESIS_HASH
    try:
        for sequence, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict) or set(entry) != {
                "sequence", "previous_hash", "payload", "entry_hash"
            }:
                return False
            if type(entry["sequence"]) is not int or entry["sequence"] != sequence:
                return False
            if entry["previous_hash"] != previous or not isinstance(entry["payload"], dict):
                return False
            unsigned = {key: entry[key] for key in ("sequence", "previous_hash", "payload")}
            if entry["entry_hash"] != content_hash(unsigned):
                return False
            previous = entry["entry_hash"]
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
    return True


class JournalIntegrityError(ValueError):
    """Raised instead of appending to a malformed or altered journal."""


class HashChainJournal:
    """An append-only journal; exclusive sidecar locks reject concurrent writers.

    A process crash can leave the small ``.lock`` sidecar. Its removal requires
    checking that no writer is running; it never permits journal truncation.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.verify():
            raise JournalIntegrityError("Existing journal has an invalid integrity chain.")

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            text = self.path.read_bytes().decode("utf-8")
            if text and not text.endswith("\n"):
                raise JournalIntegrityError("Journal contains an incomplete final line.")
            entries = [json.loads(line) for line in text.splitlines()]
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise JournalIntegrityError("Journal is not valid UTF-8 JSONL.") from exc
        if not verify_entries(entries):
            raise JournalIntegrityError("Journal integrity verification failed.")
        return entries

    def verify(self) -> bool:
        try:
            self.entries()
        except (JournalIntegrityError, OSError):
            return False
        return True

    def append(self, event: dict) -> dict:
        if not isinstance(event, dict):
            raise TypeError("Journal payload must be a JSON object.")
        lock_path = self.path.with_name(self.path.name + ".lock")
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise JournalIntegrityError("Journal writer lock exists; inspect before retrying.") from exc
        try:
            os.close(lock_fd)
            existing = self.entries()
            # Round-tripping detaches nested objects from the caller's mutable input.
            payload = json.loads(canonical_json(event))
            unsigned = {
                "sequence": len(existing) + 1,
                "previous_hash": existing[-1]["entry_hash"] if existing else GENESIS_HASH,
                "payload": payload,
            }
            entry = {**unsigned, "entry_hash": content_hash(unsigned)}
            data = (canonical_json(entry) + "\n").encode("utf-8")
            descriptor = os.open(self.path, os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, "O_BINARY", 0), 0o600)
            try:
                remaining = memoryview(data)
                while remaining:
                    written = os.write(descriptor, remaining)
                    if written <= 0:
                        raise OSError("Journal append made no progress.")
                    remaining = remaining[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return entry
        finally:
            lock_path.unlink()
