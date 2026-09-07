"""Coordinator-owned decision/action/observation loop for explicit LLM mode.

The provider proposes research designs only. This module owns every action,
gate, call budget, duplicate decision, and transition to locked execution.
"""

from contextlib import contextmanager
from copy import deepcopy
import json
import math
import os
from pathlib import Path

from .coordinator import render_report, write_json
from .hypothesis import grounding_issues, verify_lock
from .journal import HashChainJournal
from .models import ResearchError, canonical_json, content_hash, scope_notices
from .safety import check_request


def planning_gate(search, mode="llm"):
    """Enforce tree shape and actual observations before execution, fail closed."""
    try:
        if mode == "replay":
            return (search["method"] == "saved_specification_replay"
                    and search["outcome_access"] is False and search["provider_calls"] == 0
                    and len(search["original_search_hash"]) == 64 and len(search["saved_lock_hash"]) == 64)
        if (search["method"] != "llm_bounded_candidate_search" or search["mode"] != "llm"
                or search["outcome_access"] is not False
                or search["max_initial_candidates"] != 3 or search["beam_width"] != 2
                or search["max_depth"] != 2 or search["max_revisions"] != 1
                or search["max_provider_calls"] != 4
                or type(search["provider_calls"]) is not int or not 1 <= search["provider_calls"] <= 4
                or not 1 <= len(search["rounds"]) <= 2
                or len(search["feedback"]) != len(search["rounds"]) - 1):
            return False
        parents = set()
        visited = set()
        for depth, round_ in enumerate(search["rounds"], 1):
            if round_["depth"] != depth or not 1 <= len(round_["candidates"]) <= (3 if depth == 1 else 2):
                return False
            ids = {item["candidate"]["id"] for item in round_["candidates"]}
            if len(ids) != len(round_["candidates"]) or ids & visited:
                return False
            if not 1 <= len(round_["retained"]) <= 2 or not set(round_["retained"]) <= ids:
                return False
            for item in round_["candidates"]:
                parent = item["candidate"]["parent_id"]
                if (depth == 1 and parent is not None) or (depth == 2 and parent not in parents):
                    return False
            visited |= ids
            parents = set(round_["retained"])
        last = search["rounds"][-1]
        selected = search["selected_candidate_id"]
        matches = [item for item in last["candidates"] if item["candidate"]["id"] == selected]
        return (selected in last["retained"] and len(matches) == 1
                and matches[0]["valid"] is True and not matches[0]["errors"]
                and matches[0]["candidate"] == search["selected_candidate"])
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


@contextmanager
def output_lease(output):
    output.mkdir(parents=True, exist_ok=True)
    path = output / ".run.lock"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ResearchError("Output directory has an active or stale run lock.") from exc
    try:
        os.close(descriptor)
        yield
    finally:
        path.unlink(missing_ok=True)


class RunArtifacts:
    """Append-only evidence and atomic latest-run views for LLM/replay paths."""

    def __init__(self, output, topic, mode):
        self.output = output
        self.audit = HashChainJournal(output / "audit.jsonl")
        self.journal = HashChainJournal(output / "research_journal.jsonl")
        self.notices = list(scope_notices(mode))
        self.run_id = "run-" + content_hash({"topic_hash": content_hash(topic), "mode": mode,
                                            "index": len(self.audit.entries())})[:16]
        self.result = {
            "schema_version": "2.0", "execution_mode": mode, "run_id": self.run_id,
            "safety_notices": self.notices, "topic": None, "status": "rejected", "verdict": "rejected",
            "requires_human_intervention": True, "evidence": [], "memory_context": [],
            "hypothesis_search": None, "hypothesis_lock": None, "data_validation": None,
            "backtest": None, "duplicate_reference": None, "replication_rationale": None,
            "planning_contexts": [], "provider_execution": {
                "calls_attempted": 0, "actual_provider_calls": 0, "calls": [],
                "token_usage": None, "cost_usd": None, "live_execution_verified": False},
        }

    def event(self, role, event, details):
        return self.audit.append({"run_id": self.run_id, "role": role, "event": event,
                                  "details": deepcopy(details), "safety_notices": self.notices})

    def stop(self, status, reason):
        self.result.update(status=status, verdict="rejected", requires_human_intervention=True)
        self.result["review"] = {"verdict": "rejected", "requires_human_intervention": True,
                                 "confidence": "none", "checks": {"workflow_gates": False},
                                 "objections": [reason], "limitations": [
                                     "No new research conclusion is supported by this stopped run."]}
        self.event("Coordinator", "workflow_stopped", {"status": status, "reason": reason})
        return self.finish()

    def finish(self):
        digest = content_hash(self.result)
        self.event("Coordinator", "workflow_completed", {
            "status": self.result["status"], "verdict": self.result["verdict"],
            "requires_human_intervention": self.result["requires_human_intervention"], "result_hash": digest})
        self.journal.append({"event": "research_concluded", "run_id": self.run_id,
                             "execution_mode": self.result["execution_mode"], "result_hash": digest,
                             "safety_notices": self.notices, "status": self.result["status"],
                             "hypothesis_lock": self.result["hypothesis_lock"],
                             "review": self.result["review"], "duplicate_reference": self.result["duplicate_reference"]})
        self.result["integrity"] = {"audit_head": self.audit.entries()[-1]["entry_hash"],
                                     "research_journal_head": self.journal.entries()[-1]["entry_hash"]}
        write_json(self.output / "result.json", self.result)
        temporary = self.output / "research_report.md.tmp"
        temporary.write_text(render_report(self.result), encoding="utf-8")
        os.replace(temporary, self.output / "research_report.md")
        return self.result


def _execute(coordinator, artifacts, lock):
    """All numerical work follows an already journaled immutable lock."""
    from .experiment import specification_issues
    if not verify_lock(lock) or specification_issues(lock["specification"]):
        raise ResearchError("Accepted specification does not pass the fixed execution contract.")
    artifacts.result["hypothesis_lock"] = deepcopy(lock)
    artifacts.event("Hypothesis Generator", "hypothesis_locked", lock)
    artifacts.journal.append({"event": "hypothesis_locked", "run_id": artifacts.run_id,
                              "lock": lock, "safety_notices": artifacts.notices})
    rows = coordinator.data_engineer.generate(deepcopy(lock["specification"]))
    validation = coordinator.data_engineer.validate(rows, deepcopy(lock["specification"]))
    artifacts.event("Data Engineer", "data_generated", {"row_count": len(rows), "data_hash": validation.get("data_hash")})
    artifacts.result["data_validation"] = validation
    artifacts.event("Data Engineer", "data_validated", validation)
    if not validation["passed"]:
        return artifacts.stop("data_validation_failed", "Data validation failed; no backtest was run.")
    if not verify_lock(lock) or lock != artifacts.result["hypothesis_lock"]:
        return artifacts.stop("hypothesis_tampered", "The locked hypothesis changed before execution.")
    artifacts.event("Backtester", "backtest_started", {"hypothesis_hash": lock["content_hash"]})
    backtest = coordinator.backtester.run(lock, rows, validation)
    artifacts.result["backtest"] = backtest
    artifacts.event("Backtester", "backtest_completed", backtest)
    review = coordinator.skeptic.review(lock, artifacts.result["evidence"], validation,
                                        backtest, artifacts.audit.entries(), rows=rows)
    artifacts.result["review"] = review
    artifacts.event("Skeptic", "review_completed", review)
    artifacts.result.update(status="completed" if review["verdict"] != "rejected" else "rejected",
                            verdict=review["verdict"], requires_human_intervention=review["requires_human_intervention"])
    return None


def run_llm(coordinator, topic, output_dir, *, journal_dir=None, provider=None, model=None,
            replication_rationale=None, constraints=None, max_provider_calls=4,
            controlled_validation=None):
    """No fallbacks: absent credentials/errors produce their own explicit status."""
    output = Path(output_dir)
    with output_lease(output):
        artifacts = RunArtifacts(output, topic, "llm")
        guard = check_request(topic)
        artifacts.result["input_guardrail"] = guard
        if not guard["allowed"]:
            artifacts.event("Coordinator", "request_refused", {"guardrail": guard})
            return artifacts.stop("request_refused", guard["reason"])
        if replication_rationale is not None:
            guard_rationale = check_request("Explore lower volatility stock returns " + replication_rationale)
            if not replication_rationale.strip() or not guard_rationale["allowed"] or len(replication_rationale) > 800:
                return artifacts.stop("request_refused", "Replication rationale must be concise public research text without sensitive information.")
        artifacts.result["topic"] = topic
        artifacts.result["replication_rationale"] = replication_rationale
        artifacts.result["controlled_validation"] = controlled_validation
        artifacts.event("Coordinator", "request_accepted", {"topic": topic, "mode": "llm", "guardrail": guard,
                                                            "constraints": constraints or {},
                                                            "replication_rationale": replication_rationale,
                                                            "controlled_validation": controlled_validation})
        if type(max_provider_calls) is not int or not 0 <= max_provider_calls <= 4:
            return artifacts.stop("invalid_configuration", "Provider call budget must be an integer from zero through four.")
        if max_provider_calls == 0:
            return artifacts.stop("budget_exhausted", "No provider calls remain in the explicit budget.")
        try:
            from .llm_design import build_context, injection_issues
            from .memory import ResearchMemory
            # Reading metadata is not permission to alter policy; refuse modified corpus text.
            evidence = coordinator.retriever.search(topic, limit=6)
            for item in coordinator.retriever.search("backtesting research protocol overfitting", limit=6):
                if item["id"] not in {source["id"] for source in evidence}:
                    evidence.append(item)
            issues = grounding_issues(evidence)
            if issues or injection_issues(evidence) or injection_issues(topic):
                return artifacts.stop("grounding_failed", "Eligible public grounding is insufficient, altered, or contains instruction-like content.")
            artifacts.result["evidence"] = deepcopy(evidence)
            artifacts.event("Hypothesis Generator", "evidence_retrieved", {"evidence": evidence})
            shared = ResearchMemory(journal_dir or output / "shared_journal")
            with shared.lease():
                memory = shared.planning_context(topic)
                artifacts.result["memory_context"] = memory
                artifacts.event("Coordinator", "memory_retrieved", {
                    "records": memory, "record_ids": [record["journal_record_id"] for record in memory],
                    "journal_head": shared.journal.entries()[-1]["entry_hash"] if shared.journal.entries() else None})
                # build_context applies strict allowlists and bounded context size before adapter use.
                context = build_context(topic, evidence, memory, constraints=constraints,
                                        replication_rationale=replication_rationale)
                if provider is None:
                    from .provider import OpenAIProvider
                    provider = OpenAIProvider(model=model)
                return _planning_loop(coordinator, artifacts, provider, context, evidence, memory, shared,
                                      constraints, replication_rationale, max_provider_calls, controlled_validation)
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
            status = getattr(exc, "status", "planning_error")
            return artifacts.stop(status, "Planning stopped at an integrity, context, or configuration gate; human inspection is required.")


def _planning_loop(coordinator, artifacts, provider, context, evidence, memory, shared,
                   constraints, replication_rationale, budget, controlled_validation):
    from .experiment import build_llm_lock
    from .llm_design import CANDIDATE_SCHEMA, PROMPT_VERSION, SCHEMA_VERSION, build_context, injection_issues, schema_issues, validate_proposal
    search = {"method": "llm_bounded_candidate_search", "mode": "llm", "max_initial_candidates": 3,
              "beam_width": 2, "max_depth": 2, "max_revisions": 1, "max_provider_calls": 4,
              "provider_calls": 0, "outcome_access": False, "rounds": [], "feedback": [],
              "selected_candidate_id": None, "selected_candidate": None,
              "replication_rationale": replication_rationale}
    artifacts.result["hypothesis_search"] = search
    parent_ids = None
    for depth in (1, 2):
        response = None
        # At most one transport retry per round; every attempt consumes a budget slot.
        for retry in range(2):
            if search["provider_calls"] >= budget:
                return artifacts.stop("budget_exhausted", "Provider call budget exhausted before a valid hypothesis was locked.")
            search["provider_calls"] += 1
            try:
                response = provider.generate(deepcopy(context))
            except Exception:
                response = {"status": "provider_error", "output": None, "metadata": {
                    "provider": "unknown", "actual_provider_call": False, "actual_model": None,
                    "response_id": None, "usage": None, "cost_usd": None}}
            metadata = response["metadata"]
            execution = artifacts.result["provider_execution"]
            execution["calls_attempted"] += 1
            execution["actual_provider_calls"] += int(metadata.get("actual_provider_call") is True)
            execution["calls"].append(deepcopy(metadata))
            actual = [item for item in execution["calls"] if item.get("actual_provider_call") is True]
            execution["token_usage"] = ({key: sum(item["usage"][key] for item in actual)
                                          for key in ("input_tokens", "output_tokens", "total_tokens")}
                                         if actual and all(item.get("usage") and all(type(item["usage"].get(key)) is int
                                             for key in ("input_tokens", "output_tokens", "total_tokens")) for item in actual) else None)
            raw_output = response.get("output")
            quarantined = bool(raw_output is not None and injection_issues(raw_output))
            safe_output = None if quarantined else raw_output
            call = {"call_index": search["provider_calls"], "round": depth,
                    "metadata": metadata, "status": response["status"], "output": safe_output,
                    "context_hash": content_hash(context), "prompt_version": PROMPT_VERSION,
                    "schema_version": SCHEMA_VERSION, "quarantined": quarantined}
            artifacts.result["planning_contexts"].append({"call_index": search["provider_calls"], "context": deepcopy(context),
                                                         "context_hash": content_hash(context)})
            artifacts.event("Hypothesis Generator", "provider_call_completed", call)
            if quarantined:
                return artifacts.stop("unsafe_provider_output", "Provider output contained prohibited instruction-like content and was not retained.")
            if response["status"] not in ("provider_timeout", "provider_error"):
                break
        if response["status"] != "completed":
            return artifacts.stop(response["status"], "The provider did not return a completed structured design; no offline fallback was used.")
        proposal = response.get("output")
        assessment = validate_proposal(proposal, evidence, artifacts.result["topic"],
                                       constraints=constraints, parent_ids=parent_ids)
        candidates = deepcopy(assessment["candidates"])
        if (isinstance(proposal, dict) and proposal.get("action") == "defer" and not schema_issues(proposal)
                and not proposal["candidates"] and proposal["selected_candidate_id"] is None and proposal["deferral_reason"]):
            if memory:
                artifacts.result["duplicate_reference"] = {key: memory[0][key] for key in (
                    "journal_record_id", "experiment_fingerprint", "hypothesis_id")}
            artifacts.event("Coordinator", "candidates_assessed", {
                "depth": depth, "proposal": proposal, "candidates": candidates, "retained": []})
            return artifacts.stop("model_deferred", "The generator deferred after reviewing evidence and methodological constraints.")
        if not candidates or len(candidates) > (3 if depth == 1 else 2):
            return artifacts.stop("malformed_output", "No inspectable candidate tree satisfied the strict structured-output contract.")
        if any(schema_issues(item["candidate"], CANDIDATE_SCHEMA) for item in candidates):
            return artifacts.stop("malformed_output", "Candidate fields failed the strict schema before any executable design was accepted.")
        for item in candidates:
            if item["valid"]:
                candidate_lock = build_llm_lock(artifacts.result["topic"], item["candidate"], evidence)
                duplicate = shared.find_duplicate(candidate_lock["specification"])
                item["duplicate_reference"] = duplicate
                if duplicate and not replication_rationale:
                    item["valid"] = False
                    item["errors"].append("Identical scientific experiment already exists; defer or provide an explicit replication rationale.")
            if controlled_validation == "require_same_close_limitation" and not any(
                    "same-close" in text.lower() and "zero latency" in text.lower()
                    for text in item["candidate"].get("limitations", [])):
                item["valid"] = False
                item["errors"].append("Controlled validation condition: limitations must explicitly mention same-close execution and zero latency.")
        ranked = sorted(candidates, key=lambda item: (not item["valid"], -item["score"], item["candidate"]["id"]))
        retained = [item["candidate"]["id"] for item in ranked[:2]]
        round_ = {"depth": depth, "proposal": proposal, "candidates": candidates, "retained": retained}
        search["rounds"].append(round_)
        artifacts.event("Coordinator", "candidates_assessed", round_)
        selected_id = assessment.get("selected_candidate_id")
        selected = next((item for item in candidates if item["candidate"]["id"] == selected_id), None)
        if selected and selected.get("duplicate_reference") and not replication_rationale:
            artifacts.result["duplicate_reference"] = selected["duplicate_reference"]
            return artifacts.stop("duplicate_deferred", "The same scientific experiment is already recorded. No redundant backtest was executed.")
        if proposal.get("action") == "defer":
            return artifacts.stop("model_deferred", "The generator deferred after reviewing evidence and methodological constraints.")
        if assessment["valid"] and selected and selected["valid"] and selected_id in retained:
            if replication_rationale and not selected.get("duplicate_reference"):
                return artifacts.stop("replication_target_missing", "An intentional replication must match an existing substantive experiment.")
            axes = ("lookback_months", "selection_count")
            explicitly_directed = any(all(
                selected["candidate"][field] == prior["specification"][field]
                or (constraints or {}).get(field) == selected["candidate"][field]
                for field in axes) for prior in memory)
            if memory and not replication_rationale and not explicitly_directed:
                artifacts.result["duplicate_reference"] = {key: memory[0][key] for key in (
                    "journal_record_id", "experiment_fingerprint", "hypothesis_id")}
                return artifacts.stop("new_design_requires_direction", "Prior experiments exist. Each changed design parameter needs an explicit user constraint; the agent may not vary parameters to escape duplication.")
            search["selected_candidate_id"] = selected_id
            search["selected_candidate"] = deepcopy(selected["candidate"])
            if not planning_gate(search):
                return artifacts.stop("search_gate_failed", "The candidate tree failed the pre-lock isolation or budget contract.")
            artifacts.event("Hypothesis Generator", "search_completed", search)
            lock = build_llm_lock(artifacts.result["topic"], selected["candidate"], evidence)
            result = _execute(coordinator, artifacts, lock)
            if result is not None:
                return result
            if artifacts.result["status"] == "completed":
                record = shared.record_completed(lock, artifacts.run_id, artifacts.result["review"], replication_rationale)
                artifacts.result["shared_record_reference"] = record
                artifacts.result["provider_execution"]["live_execution_verified"] = bool(
                    artifacts.result["provider_execution"]["actual_provider_calls"] > 0
                    and all(item.get("provider") == "openai" for item in artifacts.result["provider_execution"]["calls"]))
            return artifacts.finish()
        if depth == 2:
            return artifacts.stop("revision_budget_exhausted", "No selected valid candidate survived the single permitted feedback/revision round.")
        objections = list(assessment.get("errors", []))
        for item in candidates:
            objections.extend(f"{item['candidate']['id']}: {error}" for error in item["errors"])
        if selected_id not in retained:
            objections.append("Select a candidate within the deterministic beam of at most two retained designs.")
        if not objections:
            objections.append("A selected valid executable candidate is required; otherwise defer.")
        feedback = {"round": 2, "objections": objections, "parent_ids": retained,
                    "candidates": [item["candidate"] for item in ranked[:2]]}
        search["feedback"].append(feedback)
        artifacts.event("Coordinator", "feedback_issued", feedback)
        parent_ids = retained
        context = build_context(artifacts.result["topic"], evidence, memory, feedback=feedback,
                                constraints=constraints, replication_rationale=replication_rationale)
    return artifacts.stop("revision_budget_exhausted", "The bounded planning loop stopped without a lock.")


def replay(coordinator, result_path, output_dir):
    """Replay only a saved completed, chain-verified experiment; never call a model."""
    output = Path(output_dir)
    with output_lease(output):
        artifacts = RunArtifacts(output, "saved-specification-replay", "replay")
        try:
            source = Path(result_path)
            if source.stat().st_size > 2_000_000:
                raise ResearchError("Saved result exceeds replay limit")
            saved = json.loads(source.read_text(encoding="utf-8"))
            integrity = saved.pop("integrity")
            audit = HashChainJournal(source.parent / "audit.jsonl")
            if not audit.entries() or audit.entries()[-1]["entry_hash"] != integrity["audit_head"]:
                raise ResearchError("Saved result does not match its current audit head")
            digest = content_hash(saved)
            if audit.entries()[-1]["payload"]["details"]["result_hash"] != digest:
                raise ResearchError("Saved result was altered")
            memory = HashChainJournal(source.parent / "research_journal.jsonl")
            if not memory.entries() or memory.entries()[-1]["entry_hash"] != integrity["research_journal_head"]:
                raise ResearchError("Saved research journal does not match")
            lock = saved["hypothesis_lock"]
            if (saved["status"] != "completed" or saved.get("execution_mode", "offline") not in ("offline", "llm")
                    or not verify_lock(lock) or grounding_issues(saved["evidence"])):
                raise ResearchError("Only valid completed grounded specifications are replayable")
            guard = check_request(saved["topic"])
            if not guard["allowed"]:
                raise ResearchError("Saved direction is outside the research boundary")
            artifacts.result["topic"] = saved["topic"]
            artifacts.result["evidence"] = saved["evidence"]
            artifacts.result["input_guardrail"] = guard
            provenance = {"saved_lock_hash": lock["content_hash"], "original_search": saved["hypothesis_search"],
                          "original_search_hash": content_hash(saved["hypothesis_search"]),
                          "source_result_hash": digest, "original_audit_head": integrity["audit_head"]}
            artifacts.result["replay_provenance"] = provenance
            artifacts.event("Coordinator", "request_accepted", {"topic": saved["topic"], "mode": "replay", "guardrail": guard})
            artifacts.event("Hypothesis Generator", "evidence_retrieved", {"evidence": saved["evidence"]})
            artifacts.event("Coordinator", "replay_loaded", provenance)
            search = {"method": "saved_specification_replay", "outcome_access": False, "provider_calls": 0,
                      "original_search_hash": provenance["original_search_hash"], "saved_lock_hash": lock["content_hash"]}
            artifacts.result["hypothesis_search"] = search
            if not planning_gate(search, "replay"):
                raise ResearchError("Replay contract failed")
            artifacts.event("Hypothesis Generator", "search_completed", search)
            result = _execute(coordinator, artifacts, deepcopy(lock))
            if result is not None:
                return result
            artifacts.result["replay_metrics_identical"] = artifacts.result["backtest"] == saved["backtest"]
            artifacts.result["replay_within_tolerance"] = _replay_equivalent(artifacts.result["backtest"], saved["backtest"])
            if not artifacts.result["replay_within_tolerance"]:
                return artifacts.stop("replay_mismatch", "Recomputed experiment differs from the saved execution beyond floating-point tolerance.")
            return artifacts.finish()
        except (ValueError, TypeError, KeyError, AttributeError, OSError):
            return artifacts.stop("replay_integrity_error", "Saved result, journals, specification, or grounding failed replay verification.")


def _replay_equivalent(left, right):
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_replay_equivalent(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_replay_equivalent(a, b) for a, b in zip(left, right))
    if type(left) in (int, float) and type(right) in (int, float):
        return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)
    return left == right
