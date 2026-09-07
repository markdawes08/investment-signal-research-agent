"""Deterministic local TF-IDF retrieval over original literature summaries.

This is lexical retrieval with a small, explicit domain synonym map, not an
embedding service or an LLM. Numeric data never enters the document index.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from importlib.resources import files
import json
import math
from pathlib import Path
import re


_STOP_WORDS = frozenset(
    "a an and are as at be by for from has have in is it of on or that the their "
    "these this to uses using was were whether which with would".split()
)
_SYNONYMS = {
    "stocks": "stock", "equities": "stock", "equity": "stock",
    "returns": "return", "risks": "risk", "lower": "low",
    "vol": "volatility", "volatile": "volatility", "variance": "volatility",
    "backtest": "backtesting", "backtests": "backtesting",
    "hypotheses": "hypothesis", "factors": "factor",
}


def _tokens(value: str) -> list[str]:
    return [
        _SYNONYMS.get(token, token)
        for token in re.findall(r"[a-z]+", value.lower())
        if token not in _STOP_WORDS
    ]


class LiteratureRetriever:
    """Index prose metadata and return stable, scored source copies."""

    def __init__(self, corpus_path: str | Path | None = None) -> None:
        location = Path(corpus_path) if corpus_path else files(__package__).joinpath(
            "data/literature.json"
        )
        sources = json.loads(location.read_text(encoding="utf-8"))
        if not isinstance(sources, list):
            raise ValueError("Literature corpus must be a JSON list.")
        seen = set()
        for source in sources:
            required = {"id", "title", "authors", "year", "url", "summary", "topics", "kind", "stance"}
            if not isinstance(source, dict) or not required.issubset(source):
                raise ValueError("Each literature source must contain complete metadata.")
            if source["id"] in seen:
                raise ValueError("Literature source identifiers must be unique.")
            seen.add(source["id"])
            if source["kind"] not in {"research_summary", "methodology_summary"} or source.get(
                "contains_numerical_dataset"
            ) is not False:
                raise ValueError("Numerical datasets must remain structured data outside retrieval.")
        self.sources = sorted(deepcopy(sources), key=lambda item: item["id"])
        counts = [Counter(_tokens(" ".join([
            source["title"], source["summary"], " ".join(source["topics"])
        ]))) for source in self.sources]
        document_frequency: Counter[str] = Counter()
        for count in counts:
            document_frequency.update(count.keys())
        self._idf = {
            term: math.log((1 + len(counts)) / (1 + frequency)) + 1
            for term, frequency in document_frequency.items()
        }
        self._vectors = [self._vector(count) for count in counts]

    def _vector(self, count: Counter[str]) -> dict[str, float]:
        weighted = {
            term: (1 + math.log(frequency)) * self._idf[term]
            for term, frequency in count.items() if term in self._idf
        }
        length = math.sqrt(sum(value * value for value in weighted.values()))
        return {term: value / length for term, value in weighted.items()} if length else {}

    def search(self, query: str, limit: int = 6) -> list[dict]:
        """Return positive cosine matches, breaking ties by stable source ID."""
        if not isinstance(query, str) or not query.strip() or limit <= 0:
            return []
        query_vector = self._vector(Counter(_tokens(query)))
        matches = []
        for source, vector in zip(self.sources, self._vectors):
            score = sum(query_vector.get(term, 0.0) * weight for term, weight in vector.items())
            if score > 0:
                matches.append({**deepcopy(source), "score": round(score, 12)})
        return sorted(matches, key=lambda source: (-source["score"], source["id"]))[:limit]
