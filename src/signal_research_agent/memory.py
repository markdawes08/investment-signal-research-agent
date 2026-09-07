"""Verified, outcome-free persistent research memory.

This journal stores a narrow scientific specification and provenance references,
never prior performance. A whole-run lease makes duplicate checking and recording
atomic for cooperating processes. Local chains cannot authenticate a fully
rewritten journal or detect a deleted valid tail without an external checkpoint.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import math
import os
from pathlib import Path
import re

from .hypothesis import verify_lock
from .journal import HashChainJournal, JournalIntegrityError
from .models import ResearchError, canonical_json, content_hash


SUBSTANTIVE_FIELDS = (
    "signal", "universe", "lookback_months", "holding_months", "selection_count",
    "benchmark", "cost_bps", "risk_free_rate", "as_of_date", "min_observations",
    "success_rule", "seed", "generator_version", "start_date", "n_months",
)

# Messages are application-owned, never copied from a model or journal prose.
METHODOLOGICAL_OBJECTIONS = {
    "synthetic_data_only": "The experiment uses synthetic observations and establishes no real-market evidence.",
    "single_fixture": "A single fixed fixture does not establish statistical significance or causality.",
    "fixed_universe": "The fixed universe excludes changing constituents, delistings, and corporate actions.",
    "monthly_close_assumption": "Month-end observation and rebalancing assume zero execution latency.",
    "zero_risk_free_rate": "The comparison fixes the risk-free rate at zero.",
    "monthly_literature_adaptation": "Monthly signal parameters are design choices rather than a replication of daily-return studies.",
}

_PAYLOAD_FIELDS = {
    "memory_schema_version", "record_type", "execution_mode", "run_id",
    "experiment_fingerprint", "hypothesis_id", "hypothesis_content_hash",
    "specification", "methodological_objection_codes", "replication_rationale_hash",
    "safety_notices",
}


class MemoryGateError(ResearchError):
    """A fail-closed memory gate with a stable application status."""

    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


def _project_specification(specification: dict) -> dict:
    """Normalize substantive fields; topics, prose, source ordering and mode vanish."""
    if not isinstance(specification, dict) or any(key not in specification for key in SUBSTANTIVE_FIELDS):
        raise MemoryGateError("memory_invalid_record", "A complete scientific specification is required.")
    projected = {key: deepcopy(specification[key]) for key in SUBSTANTIVE_FIELDS}
    universe = projected["universe"]
    if (not isinstance(universe, list) or not universe
            or any(not isinstance(asset, str) for asset in universe)
            or len(set(universe)) != len(universe)):
        raise MemoryGateError("memory_invalid_record", "The scientific universe must contain distinct asset identifiers.")
    projected["universe"] = sorted(universe)
    for key in ("cost_bps", "risk_free_rate"):
        value = projected[key]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise MemoryGateError("memory_invalid_record", "Scientific numeric parameters must be finite numbers.")
        projected[key] = float(value)
    for key in ("lookback_months", "holding_months", "selection_count", "min_observations", "seed", "n_months"):
        if type(projected[key]) is not int:
            raise MemoryGateError("memory_invalid_record", "Scientific integer parameters must be integers.")
    try:
        content_hash(projected)
    except (TypeError, ValueError, OverflowError) as exc:
        raise MemoryGateError("memory_invalid_record", "The scientific specification is not canonical JSON.") from exc
    return projected


def experiment_fingerprint(specification: dict) -> str:
    """Identify the experiment independently of paraphrases and incidental metadata."""
    return content_hash(_project_specification(specification))


def _supported_projection(specification: dict) -> bool:
    """Check all fixed fixture choices as well as the two permitted design axes."""
    # The supported contract is imported at use time to avoid a memory/coordinator
    # import cycle. The projected record intentionally has no execution mode.
    from .experiment import specification_issues

    try:
        return (set(specification) == set(SUBSTANTIVE_FIELDS)
                and not specification_issues({"version": "1.0", "design_mode": "llm", **specification}))
    except (TypeError, ValueError):
        return False


def _scope_notices(mode: str) -> list[str]:
    from .models import scope_notices

    return list(scope_notices(mode))


class ResearchMemory:
    """Separate system-owned prior designs from the public literature corpus."""

    MAX_FILE_BYTES = 5 * 1024 * 1024
    MAX_RECORDS = 1000

    def __init__(self, journal_dir: str | Path):
        self.directory = Path(journal_dir)
        self.path = self.directory / "experiments.jsonl"
        self._leased = False
        self._check_size()
        try:
            self.journal = HashChainJournal(self.path)
        except (JournalIntegrityError, OSError, RecursionError) as exc:
            raise MemoryGateError("memory_integrity_error", "Shared research journal cannot be verified; human intervention required.") from exc
        self.records()

    def _check_size(self) -> None:
        try:
            if self.path.exists() and self.path.stat().st_size > self.MAX_FILE_BYTES:
                raise MemoryGateError("memory_limit", "Shared research journal exceeds the configured size limit.")
        except OSError as exc:
            raise MemoryGateError("memory_integrity_error", "Shared research journal cannot be inspected.") from exc

    def _verified_entries(self) -> list[dict]:
        self._check_size()
        try:
            entries = self.journal.entries()
        except (JournalIntegrityError, OSError, RecursionError) as exc:
            raise MemoryGateError("memory_integrity_error", "Shared research journal integrity verification failed; human intervention required.") from exc
        if len(entries) > self.MAX_RECORDS:
            raise MemoryGateError("memory_limit", "Shared research journal exceeds the configured record limit.")
        for entry in entries:
            if not self._valid_payload(entry["payload"]):
                raise MemoryGateError("memory_invalid_record", "Shared research journal has an unsupported record; human intervention required.")
        return entries

    @staticmethod
    def _valid_payload(payload: dict) -> bool:
        try:
            digest = payload["hypothesis_content_hash"]
            mode = payload["execution_mode"]
            codes = payload["methodological_objection_codes"]
            rationale_hash = payload["replication_rationale_hash"]
            return (
                set(payload) == _PAYLOAD_FIELDS
                and payload["memory_schema_version"] == "1.0"
                and payload["record_type"] == "completed_synthetic_experiment"
                and mode in ("offline", "llm")
                and isinstance(payload["run_id"], str)
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", payload["run_id"]) is not None
                and isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
                and payload["hypothesis_id"] == "hyp-v1-" + digest[:16]
                and _supported_projection(payload["specification"])
                and payload["experiment_fingerprint"] == experiment_fingerprint(payload["specification"])
                and isinstance(codes, list) and codes == sorted(set(codes))
                and all(code in METHODOLOGICAL_OBJECTIONS for code in codes)
                and (rationale_hash is None or (isinstance(rationale_hash, str)
                     and re.fullmatch(r"[0-9a-f]{64}", rationale_hash) is not None))
                and payload["safety_notices"] == _scope_notices(mode)
            )
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
            return False

    def records(self) -> list[dict]:
        """Read only verified completed records, including stable chain references."""
        return [{**deepcopy(entry["payload"]), "journal_record_id": entry["entry_hash"]}
                for entry in self._verified_entries()]

    def planning_context(self, topic: str, limit: int = 4) -> list[dict]:
        """Retrieve a bounded allowlist projection without any prior outcomes.

        Relevance is token overlap with application-owned scientific parameter
        labels, not free text from prior requests or performance rankings.
        """
        if not isinstance(topic, str) or type(limit) is not int or not 0 <= limit <= 4:
            raise MemoryGateError("memory_invalid_request", "Memory retrieval requires text and a limit from zero through four.")
        query = set(re.findall(r"[a-z0-9]+", topic.lower()))
        ranked = []
        for record in self.records():
            specification = record["specification"]
            description = (
                "low lower total volatility risk adjusted monthly stocks research "
                "trailing sample standard deviation equal weight benchmark "
                f"{specification['lookback_months']} months {specification['selection_count']} assets"
            )
            tokens = set(re.findall(r"[a-z0-9]+", description))
            score = len(query & tokens) / math.sqrt(len(query) * len(tokens)) if query else 0.0
            ranked.append({
                "journal_record_id": record["journal_record_id"],
                "experiment_fingerprint": record["experiment_fingerprint"],
                "hypothesis_id": record["hypothesis_id"],
                "specification": deepcopy(specification),
                "methodological_objections": [{"code": code, "message": METHODOLOGICAL_OBJECTIONS[code]}
                                              for code in record["methodological_objection_codes"]],
                "similarity_score": round(score, 8),
            })
        return sorted(ranked, key=lambda item: (-item["similarity_score"], item["journal_record_id"]))[:limit]

    def find_duplicate(self, specification: dict) -> dict | None:
        """Search every verified record, independently of the retrieval beam."""
        fingerprint = experiment_fingerprint(specification)
        for record in self.records():
            if record["experiment_fingerprint"] == fingerprint:
                return {key: record[key] for key in (
                    "journal_record_id", "experiment_fingerprint", "hypothesis_id", "run_id"
                )}
        return None

    @contextmanager
    def lease(self):
        """Hold an exclusive cross-process design-through-record lease.

        A stale lease is never automatically removed: after a crash, a human must
        check for active research processes before deleting this one sidecar.
        """
        if self._leased:
            raise MemoryGateError("memory_busy", "This research memory lease is already held.")
        lock_path = self.directory / ".research.lock"
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise MemoryGateError("memory_busy", "A shared research lease exists; inspect active runs before retrying.") from exc
        except OSError as exc:
            raise MemoryGateError("memory_integrity_error", "A shared research lease could not be created.") from exc
        try:
            os.close(descriptor)
            self._leased = True
            self.records()
            yield self
        finally:
            self._leased = False
            lock_path.unlink()

    def record_completed(self, lock: dict, run_id: str, review: dict,
                         replication_rationale: str | None = None) -> dict:
        """Append a safely projected completed experiment; never store outcomes."""
        if not self._leased:
            with self.lease():
                return self.record_completed(lock, run_id, review, replication_rationale)
        if not verify_lock(lock):
            raise MemoryGateError("memory_invalid_record", "An altered or unlocked hypothesis cannot enter research memory.")
        from .experiment import specification_issues

        if specification_issues(lock["specification"]):
            raise MemoryGateError("memory_invalid_record", "The locked experiment violates its execution-mode specification contract.")
        if (not isinstance(review, dict)
                or review.get("verdict") not in ("supported_in_synthetic_fixture_only", "unsupported_in_synthetic_fixture")
                or review.get("requires_human_intervention") is not False
                or not isinstance(review.get("checks"), dict) or not review["checks"]
                or any(value is not True for value in review["checks"].values())
                or review.get("objections") != []):
            raise MemoryGateError("memory_invalid_record", "Only completed independently reviewed experiments enter shared memory.")
        if replication_rationale is not None and (not isinstance(replication_rationale, str)
                or not replication_rationale.strip() or len(replication_rationale) > 2000):
            raise MemoryGateError("memory_invalid_record", "Replication requires a bounded nonempty user rationale.")
        specification = _project_specification(lock["specification"])
        mode = lock["specification"].get("design_mode", "offline")
        payload = {
            "memory_schema_version": "1.0",
            "record_type": "completed_synthetic_experiment",
            "execution_mode": mode,
            "run_id": run_id,
            "experiment_fingerprint": experiment_fingerprint(specification),
            "hypothesis_id": lock["hypothesis_id"],
            "hypothesis_content_hash": lock["content_hash"],
            "specification": specification,
            "methodological_objection_codes": sorted(METHODOLOGICAL_OBJECTIONS),
            "replication_rationale_hash": content_hash(replication_rationale.strip()) if replication_rationale else None,
            "safety_notices": _scope_notices(mode),
        }
        if not self._valid_payload(payload):
            raise MemoryGateError("memory_invalid_record", "The completed experiment does not satisfy the memory contract.")
        entries = self._verified_entries()
        if len(entries) >= self.MAX_RECORDS:
            raise MemoryGateError("memory_limit", "Shared research journal is at its configured record limit.")
        if self.find_duplicate(specification) is not None and replication_rationale is None:
            raise MemoryGateError("duplicate_experiment", "An identical experiment already exists; an explicit user replication rationale is required.")
        prospective = {"sequence": len(entries) + 1,
                       "previous_hash": entries[-1]["entry_hash"] if entries else "0" * 64,
                       "payload": payload, "entry_hash": "0" * 64}
        existing_bytes = self.path.stat().st_size if self.path.exists() else 0
        if existing_bytes + len((canonical_json(prospective) + "\n").encode("utf-8")) > self.MAX_FILE_BYTES:
            raise MemoryGateError("memory_limit", "The new record would exceed the shared journal size limit.")
        try:
            entry = self.journal.append(payload)
        except (JournalIntegrityError, OSError) as exc:
            raise MemoryGateError("memory_integrity_error", "The completed research record could not be appended safely.") from exc
        self._check_size()
        return {**deepcopy(entry["payload"]), "journal_record_id": entry["entry_hash"]}
