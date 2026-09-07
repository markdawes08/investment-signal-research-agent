"""Gate-driven orchestration; no agent receives outcomes before the lock."""

from copy import deepcopy
import json
import os
import re
from pathlib import Path

from .backtester import Backtester
from .data_engineer import DataEngineer
from .hypothesis import HypothesisGenerator, grounding_issues, verify_lock
from .journal import HashChainJournal
from .models import ResearchError, SAFETY_NOTICES, content_hash
from .retrieval import LiteratureRetriever
from .safety import check_request
from .skeptic import Skeptic

DEFAULT_TOPIC = "Explore whether lower-volatility stocks have better risk-adjusted returns"


def search_gate(search, mode="offline"):
    """Check the recorded tree and limits before any data or backtest access."""
    if mode in ("llm", "replay"):
        from .llm_workflow import planning_gate
        return planning_gate(search, mode)
    if mode != "offline":
        return False
    try:
        return (
            search["method"] == "bounded_deterministic_beam_search"
            and search["outcome_access"] is False
            and search["max_depth"] == 2 and search["beam_width"] == 2
            and search["max_nodes"] == 5 and search["max_revisions"] == 1
            and type(search["nodes_visited"]) is int and 3 <= search["nodes_visited"] <= 5
            and search["selected"] == "total_volatility"
            and search["scoring_inputs"] == ["source_topic_coverage", "offline_harness_feasibility"]
            and len(search["alternatives"]) == 3
            and {node["definition"] for node in search["alternatives"]} == {
                "total_volatility", "beta", "idiosyncratic_volatility"}
            and len(search["trace"]) == 2
            and [node["depth"] for node in search["trace"]] == [1, 2]
            and all(0 < len(node["retained"]) <= 2 for node in search["trace"])
            and sum(len(node["expanded"]) for node in search["trace"]) == search["nodes_visited"]
            and isinstance(search["revisions"], list) and len(search["revisions"]) <= 1
            and all(revision["before_lock"] is True for revision in search["revisions"])
        )
    except (KeyError, TypeError, ValueError):
        return False


def write_json(path, value):
    """Replace a derived summary atomically; journal files use append only."""
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                    allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def render_report(result):
    lines = ["# Investment Signal Research Agent", "",
             "**" + " | ".join(result.get("safety_notices", SAFETY_NOTICES)) + "**", "",
             f"Run: `{result['run_id']}`", "",
             f"Status: **{result['status']}**", "",
             f"Verdict: **{result['verdict']}**", "",
             f"Human intervention required: **{result['requires_human_intervention']}**", "",
             "Synthetic results describe this fixture only; they provide no evidence about real markets.", ""]
    if result.get("topic"):
        lines += ["## Research direction", "", result["topic"], ""]
    lock = result.get("hypothesis_lock")
    if lock:
        lines += ["## Preregistered hypothesis", "",
                  f"ID: `{lock['hypothesis_id']}`", "",
                  f"SHA-256: `{lock['content_hash']}`", "",
                  "```json", json.dumps(lock["specification"], indent=2), "```", ""]
    search = result.get("hypothesis_search")
    if search:
        explanation = ("Candidates: total volatility, beta, and idiosyncratic volatility. "
                       "Ranking uses literature coverage and fixed-harness feasibility only."
                       if result.get("execution_mode", "offline") == "offline" else
                       "Structured proposals, deterministic observations, and any actual feedback "
                       "are recorded below. No calculated outcomes are used for planning.")
        lines += ["## Bounded pre-outcome search", "", explanation, "",
                  "```json", json.dumps(search, indent=2), "```", ""]
    if result.get("evidence"):
        lines += ["## Public grounding", ""]
        for source in result["evidence"]:
            lines += [f"- [{source['title']}]({source['url']}) (`{source['id']}`): {source['summary']}"]
        lines += [""]
    validation = result.get("data_validation")
    if validation:
        lines += ["## Synthetic data validation", "", "```json",
                  json.dumps(validation, indent=2), "```", ""]
    backtest = result.get("backtest")
    if backtest:
        lines += ["## Synthetic fixture metrics", "",
                  "All returns are fractions; costs apply to both portfolios. "
                  "This is a pipeline exercise, not an investment performance claim.", "",
                  "| Metric | Strategy | Equal-weight benchmark |", "|---|---:|---:|"]
        metrics = backtest["metrics"]
        for key, value in metrics["strategy"].items():
            other = metrics["benchmark"].get(key)
            left = f"{value:.8f}" if isinstance(value, float) else str(value)
            right = f"{other:.8f}" if isinstance(other, float) else str(other)
            lines += [f"| {key} | {left} | {right} |"]
        lines += ["", "Methodology:", "", "```json",
                  json.dumps(backtest.get("methodology", {}), indent=2), "```", ""]
    review = result["review"]
    if result.get("execution_mode") in ("llm", "replay"):
        lines += ["## Execution provenance and persistent memory", "", "```json",
                  json.dumps({key: result.get(key) for key in (
                      "execution_mode", "provider_execution", "memory_context", "duplicate_reference",
                      "replication_rationale", "replay_provenance", "controlled_validation")}, indent=2),
                  "```", "",
                  "Citation checks verify eligible IDs, exact summary excerpts, and limited lexical support. "
                  "They are not a proof of entailment; human review of the source-to-claim relationship remains necessary.", ""]
    lines += ["## Independent skeptical review", "",
              f"Confidence: {review.get('confidence', 'none')}", ""]
    for label in ("objections", "limitations"):
        lines += [f"### {label.title()}", ""]
        lines += [f"- {item}" for item in review.get(label, [])] or ["- None recorded."]
        lines += [""]
    lines += ["## Audit and memory", "",
              "`audit.jsonl` records role events and gates. `research_journal.jsonl` "
              "retains locks and conclusions across runs. Both use append-only SHA-256 chains. "
              "They are local integrity checks, not externally authenticated evidence.", ""]
    return "\n".join(lines)


class Coordinator:
    """Owns routing and stopping rules; dependencies are injectable for evaluation."""

    role = "Coordinator"

    def __init__(self, retriever=None, generator=None, data_engineer=None,
                 backtester=None, skeptic=None):
        self.retriever = retriever or LiteratureRetriever()
        self.generator = generator or HypothesisGenerator()
        self.data_engineer = data_engineer or DataEngineer()
        self.backtester = backtester or Backtester()
        self.skeptic = skeptic or Skeptic()

    def run(self, topic, output_dir, *, mode="offline", journal_dir=None, provider=None,
            model=None, replication_rationale=None, constraints=None,
            max_provider_calls=4, controlled_validation=None):
        if mode == "llm":
            from .llm_workflow import run_llm
            return run_llm(self, topic, output_dir, journal_dir=journal_dir, provider=provider,
                           model=model, replication_rationale=replication_rationale,
                           constraints=constraints, max_provider_calls=max_provider_calls,
                           controlled_validation=controlled_validation)
        if mode != "offline":
            raise ResearchError("Use the replay command for saved specifications; unknown run mode.")
        if journal_dir is not None or replication_rationale or constraints:
            raise ResearchError("Shared planning memory and parameter choices require explicit LLM mode.")
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        lease = output / ".run.lock"
        try:
            handle = os.open(lease, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise ResearchError("Output directory has an active or stale run lock; inspect it before retrying.") from exc
        try:
            os.close(handle)
            return self._run(topic, output)
        finally:
            lease.unlink(missing_ok=True)

    def _run(self, topic, output):
        audit = HashChainJournal(output / "audit.jsonl")
        memory = HashChainJournal(output / "research_journal.jsonl")
        if not audit.verify() or not memory.verify():
            raise ResearchError("Journal integrity failed; human intervention required.")
        run_id = "run-" + content_hash({"request_hash": content_hash(topic),
                                        "index": len(audit.entries())})[:16]

        def event(role, name, details):
            return audit.append({"run_id": run_id, "role": role,
                                 "event": name, "details": deepcopy(details),
                                 "safety_notices": list(SAFETY_NOTICES)})

        result = {"schema_version": "1.0", "run_id": run_id, "execution_mode": "offline",
                  "safety_notices": list(SAFETY_NOTICES),
                  "status": "rejected", "verdict": "rejected",
                  "requires_human_intervention": True, "topic": None,
                  "evidence": [], "hypothesis_search": None,
                  "hypothesis_lock": None, "data_validation": None, "backtest": None}

        def reject(reason):
            result["review"] = {
                "verdict": "rejected", "requires_human_intervention": True,
                "confidence": "none", "objections": [reason],
                "limitations": ["No reliable research conclusion is available."],
                "checks": {"workflow_gates": False}}
            event("Coordinator", "workflow_stopped", {"reason": reason})

        def finish():
            event("Coordinator", "workflow_completed", {
                "status": result["status"], "verdict": result["verdict"],
                "requires_human_intervention": result["requires_human_intervention"],
                "result_hash": content_hash(result)})
            memory.append({"run_id": run_id, "event": "research_concluded",
                           "safety_notices": list(SAFETY_NOTICES),
                           "result_hash": content_hash(result),
                           "hypothesis_id": (result.get("hypothesis_lock") or {}).get("hypothesis_id"),
                           "verdict": result["verdict"], "review": result["review"],
                           "metrics": (result.get("backtest") or {}).get("metrics"),
                           "data_hash": (result.get("data_validation") or {}).get("data_hash"),
                           "source_ids": [source["id"] for source in result["evidence"]]})
            result["integrity"] = {"audit_head": audit.entries()[-1]["entry_hash"],
                                   "research_journal_head": memory.entries()[-1]["entry_hash"]}
            write_json(output / "result.json", result)
            report_path = output / "research_report.md"
            temporary = report_path.with_suffix(".md.tmp")
            temporary.write_text(render_report(result), encoding="utf-8")
            os.replace(temporary, report_path)
            return result

        guard = check_request(topic)
        result["input_guardrail"] = guard
        if not guard["allowed"]:
            event("Coordinator", "request_refused", {"guardrail": guard})
            reject(guard["reason"])
            return finish()
        result["topic"] = topic
        event("Coordinator", "request_accepted", {"topic": topic, "guardrail": guard})
        if re.search(r"\bbeta\b|idiosyncratic|residual.volatility", topic, re.I):
            reject("The offline harness supports total volatility only. Factor-based research needs an explicitly explained adaptation in LLM mode or human intervention.")
            return finish()
        try:
            evidence = self.retriever.search(topic, limit=6)
            for source in self.retriever.search("backtesting research protocol overfitting", limit=6):
                if source["id"] not in {entry["id"] for entry in evidence}:
                    evidence.append(source)
            issues = grounding_issues(evidence)
            if issues:
                reject("Grounding gate failed: " + "; ".join(issues))
                return finish()
            result["evidence"] = deepcopy(evidence)
            event("Hypothesis Generator", "evidence_retrieved", {"evidence": evidence})
            proposal = self.generator.generate(topic, deepcopy(evidence))
            if not isinstance(proposal, dict):
                raise ResearchError("Malformed hypothesis proposal")
        except (ResearchError, ValueError, TypeError, KeyError, AttributeError):
            reject("Retrieval or hypothesis generation failed; human inspection is required.")
            return finish()
        result["hypothesis_search"] = proposal.get("search")
        event("Hypothesis Generator", "search_completed", proposal.get("search"))
        if proposal.get("requires_human_intervention") or not proposal.get("lock"):
            reject("Grounding or specification gate failed: " + "; ".join(proposal.get("objections", [])))
            return finish()
        revisions = (proposal.get("search") or {}).get("revisions", [])
        search = proposal.get("search") or {}
        # Enforce the exact fixed search budget before market data or outcomes exist.
        if not search_gate(search):
            reject("Pre-outcome search isolation or budget gate failed.")
            return finish()
        if len(revisions) > 1:
            reject("Pre-lock revision budget exceeded.")
            return finish()
        for revision in revisions:
            event("Hypothesis Generator", "hypothesis_revised", revision)
        lock = deepcopy(proposal["lock"])
        if not verify_lock(lock):
            reject("Hypothesis lock integrity failed before data generation.")
            return finish()
        result["hypothesis_lock"] = deepcopy(lock)
        event("Hypothesis Generator", "hypothesis_locked", lock)
        memory.append({"run_id": run_id, "event": "hypothesis_locked", "lock": lock,
                       "safety_notices": list(SAFETY_NOTICES)})
        try:
            rows = self.data_engineer.generate(deepcopy(lock["specification"]))
            # Generation never exposes outcomes to the hypothesis generator.
            validation = self.data_engineer.validate(rows, lock["specification"])
            event("Data Engineer", "data_generated", {
                "row_count": len(rows), "data_hash": validation.get("data_hash")})
            result["data_validation"] = validation
            event("Data Engineer", "data_validated", validation)
            if not validation["passed"]:
                reject("Data validation failed: " + "; ".join(validation["errors"]))
                return finish()
            if not verify_lock(lock) or lock != result["hypothesis_lock"]:
                reject("A locked hypothesis was altered.")
                return finish()
            event("Backtester", "backtest_started", {"hypothesis_hash": lock["content_hash"]})
            backtest = self.backtester.run(lock, rows, validation)
            result["backtest"] = backtest
            event("Backtester", "backtest_completed", backtest)
            review = self.skeptic.review(lock, evidence, validation, backtest,
                                         audit.entries(), rows=rows)
            result["review"] = review
            event("Skeptic", "review_completed", review)
            result["verdict"] = review["verdict"]
            result["requires_human_intervention"] = review["requires_human_intervention"]
            result["status"] = "completed" if review["verdict"] != "rejected" else "rejected"
        except (ResearchError, ValueError, TypeError, KeyError) as exc:
            # Avoid writing injected data or potentially sensitive exception text.
            reject(f"Execution gate failed ({type(exc).__name__}); inspect the local implementation.")
        return finish()
