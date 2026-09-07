"""Convenience wrapper; install the package before running this script."""

import sys

from signal_research_agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["evaluate", *sys.argv[1:]]))
