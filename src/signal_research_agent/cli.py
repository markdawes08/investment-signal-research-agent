"""Offline defaults; provider access requires explicit LLM mode."""

import argparse
import json
import sys

from .coordinator import Coordinator
from .models import SAFETY_NOTICES, scope_notices
from .retrieval import LiteratureRetriever


def main(argv=None):
    parser = argparse.ArgumentParser(description="Investment Signal Research Agent — offline synthetic research")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Run a gated synthetic research workflow")
    run.add_argument("--topic", required=True)
    run.add_argument("--output-dir", default="artifacts/run")
    run.add_argument("--mode", choices=("offline", "llm"), default="offline")
    run.add_argument("--journal-dir")
    run.add_argument("--model", help="Optional model identifier; defaults to OPENAI_MODEL or the documented snapshot")
    run.add_argument("--replication-rationale", help="Explicit public research reason for an intentional duplicate")
    run.add_argument("--lookback-months", type=int, choices=(6, 12))
    run.add_argument("--selection-count", type=int, choices=(3, 4))
    replay_parser = subparsers.add_parser("replay", help="Verify and replay a saved completed specification without a provider")
    replay_parser.add_argument("--result", required=True)
    replay_parser.add_argument("--output-dir", required=True)
    evaluation = subparsers.add_parser("evaluate", help="Run deterministic acceptance scenarios")
    evaluation.add_argument("--output-dir", default="artifacts/evaluation")
    evaluation.add_argument("--suite", choices=("offline", "agentic"), default="offline")
    subparsers.add_parser("corpus", help="Print curated public-source metadata as JSON")
    args = parser.parse_args(argv)
    try:
        if args.command == "corpus":
            print(json.dumps({"safety_notices": list(SAFETY_NOTICES),
                              "sources": LiteratureRetriever().sources}, indent=2, ensure_ascii=False))
            return 0
        mode = (args.mode if args.command == "run" else "replay" if args.command == "replay" else
                "llm" if args.command == "evaluate" and args.suite == "agentic" else "offline")
        print(" | ".join(scope_notices(mode)))
        if args.command == "evaluate":
            if args.suite == "agentic":
                from .agentic_evaluation import evaluate_agentic
                result = evaluate_agentic(args.output_dir)
                print(f"Mocked agentic evaluation: {result['passed']}/{result['total']} passed; real provider calls: 0")
                return 0 if result["failed"] == 0 else 1
            from .evaluation import evaluate, console_summary
            result = evaluate(args.output_dir)
            print(console_summary(result))
            return 0 if result["failed"] == 0 else 1
        if args.command == "replay":
            from .llm_workflow import replay
            result = replay(Coordinator(), args.result, args.output_dir)
        elif args.mode == "llm":
            constraints = {key: value for key, value in {
                "lookback_months": args.lookback_months, "selection_count": args.selection_count}.items() if value is not None}
            result = Coordinator().run(args.topic, args.output_dir, mode="llm", journal_dir=args.journal_dir,
                                       model=args.model, replication_rationale=args.replication_rationale,
                                       constraints=constraints or None)
        else:
            if any(value is not None for value in (args.journal_dir, args.model, args.replication_rationale,
                                                   args.lookback_months, args.selection_count)):
                parser.error("Provider, shared-journal, and parameter options require --mode llm")
            result = Coordinator().run(args.topic, args.output_dir)
        print(f"Status: {result['status']}")
        print(f"Verdict: {result['verdict']}")
        print(f"Human intervention required: {result['requires_human_intervention']}")
        if "provider_execution" in result:
            print(f"Actual provider calls: {result['provider_execution']['actual_provider_calls']}")
            print(f"Provider status: {result['status']}")
        for objection in result["review"]["objections"]:
            print(f"Objection: {objection}")
        if result["backtest"]:
            metrics = result["backtest"]["metrics"]
            print(f"Synthetic observations: {metrics['observation_count']}")
            for label in ("strategy", "benchmark"):
                portfolio = metrics[label]
                sharpe = portfolio["sharpe_ratio"]
                print(f"Synthetic {label}: annualized return={portfolio['annualized_return']:.4%}, "
                      f"volatility={portfolio['annualized_volatility']:.4%}, "
                      f"Sharpe={sharpe:.6f}" if sharpe is not None else f"Synthetic {label}: Sharpe undefined")
        print(f"Artifacts: {args.output_dir}")
        return 2 if result["requires_human_intervention"] else 0
    except (ValueError, OSError) as exc:
        print(f"Research stopped ({type(exc).__name__}). Human intervention required. "
              "Check output permissions, journal integrity, and stale writer locks.", file=sys.stderr)
        return 2
