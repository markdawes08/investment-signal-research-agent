"""Small command-line interface; runtime never contacts a network service."""

import argparse
import json
import sys

from .coordinator import Coordinator
from .models import SAFETY_NOTICES
from .retrieval import LiteratureRetriever


def main(argv=None):
    parser = argparse.ArgumentParser(description="Investment Signal Research Agent — offline synthetic research")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Run a gated synthetic research workflow")
    run.add_argument("--topic", required=True)
    run.add_argument("--output-dir", default="artifacts/run")
    evaluation = subparsers.add_parser("evaluate", help="Run deterministic acceptance scenarios")
    evaluation.add_argument("--output-dir", default="artifacts/evaluation")
    subparsers.add_parser("corpus", help="Print curated public-source metadata as JSON")
    args = parser.parse_args(argv)
    try:
        if args.command == "corpus":
            print(json.dumps({"safety_notices": list(SAFETY_NOTICES),
                              "sources": LiteratureRetriever().sources}, indent=2, ensure_ascii=False))
            return 0
        print(" | ".join(SAFETY_NOTICES))
        if args.command == "evaluate":
            from .evaluation import evaluate, console_summary
            result = evaluate(args.output_dir)
            print(console_summary(result))
            return 0 if result["failed"] == 0 else 1
        result = Coordinator().run(args.topic, args.output_dir)
        print(f"Status: {result['status']}")
        print(f"Verdict: {result['verdict']}")
        print(f"Human intervention required: {result['requires_human_intervention']}")
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
