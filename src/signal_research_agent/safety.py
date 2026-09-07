"""Transparent, conservative input rules for this narrow offline research MVP.

These deterministic rules are a scope filter, not a semantic safety classifier.
Refusals intentionally contain no copy of the input, which could contain secrets.
"""

from __future__ import annotations

import re


_RULES = (
    (
        "brokerage_access",
        r"\b(brokerage|broker|robinhood|interactive\s+brokers|alpaca|etrade|e-trade|"
        r"trading\s+account|broker\s+api|account\s+credentials|schwab|fidelity|ameritrade)\b",
        "Brokerage connections and account access are outside historical research.",
    ),
    (
        "trade_execution",
        r"\b(buy|sell|short|purchase|trade|trading|liquidate)\b|\b(place|execute|submit|cancel|route)\b.{0,45}"
        r"\b(trade|trades|order|orders|transaction|transactions)\b|"
        r"\b(trade|order)\s+execution\b|\b(limit|market|stop.loss)\s+order\b|\bopen\b.{0,30}\bposition\b",
        "Trade and order actions are outside historical research.",
    ),
    (
        "sensitive_data",
        r"\b(private|confidential|proprietary|sensitive|nonpublic|non-public|insider|internal|restricted|"
        r"password|passwords|secret|secrets|credential|credentials|ssn|"
        r"social\s+security|customer\s+data|client\s+data|account\s+number|"
        r"api[ _-]?key|access[ _-]?token|bearer\s+token)\b|"
        r"\bsk-[A-Za-z0-9_-]{8,}|\bgh[pousr]_[A-Za-z0-9]{8,}|"
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b|\b\d{3}-\d{2}-\d{4}\b",
        "Private, confidential, proprietary, or sensitive information is not accepted.",
    ),
    (
        "personalized_advice",
        r"\b(my|our)\s+(portfolio|retirement|savings|investments|pension|401k|401\(k\)|ira)\b|"
        r"\b(should\s+i\s+(invest|allocate|hold|own)|how\s+much\s+should\s+i|"
        r"recommend\s+(me|an?\s+investment)|invest\s+(my|our)|"
        r"for\s+my\s+(risk|goals|family|situation)|personalized\s+(investment|financial)|"
        r"financial\s+advice|investment\s+advice|suitable\s+for\s+(me|us)|"
        r"(my|our)\s+risk\s+tolerance|i\s+am\s+\d{1,3}|i'm\s+\d{1,3})\b|"
        r"\ballocate\s+\$?\d|\b(for\s+me|for\s+us)\b|\brecommend\b.{0,80}\bto\s+(me|us)\b",
        "Personalized investment advice is outside this research-only system.",
    ),
)


def check_request(topic: str) -> dict:
    """Return an explainable decision without echoing submitted text.

    Negated boundary terms may also be rejected. This conservative behavior and
    the limited English vocabulary are intentional, documented MVP limitations.
    """
    if not isinstance(topic, str) or not topic.strip():
        return _decision(False, "empty_request", "A substantive research direction is required.")
    if len(topic) > 4000:
        return _decision(False, "oversized_request", "Use a concise public-literature research direction.")
    text = " ".join(topic.lower().split())
    for code, pattern, reason in _RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return _decision(False, code, reason)
    has_signal = re.search(r"\b(volatility|volatile|volatilities|beta|variance|low.vol|lower.vol)\b", text)
    has_direction = re.search(
        r"\b(research|explore|evaluate|investigate|test|compare|study|analyze|analyse|"
        r"hypothesis|returns?|stocks?|equities|equity|risk.adjusted)\b", text
    )
    if not has_signal or not has_direction or len(text.split()) < 4:
        return _decision(
            False,
            "ambiguous_or_out_of_scope",
            "Specify a public-literature hypothesis about stock volatility, beta, or variance and returns.",
        )
    return _decision(True, "research_request_accepted", "The request fits the fixed volatility-research workflow.")


def _decision(allowed: bool, code: str, reason: str) -> dict:
    return {
        "allowed": allowed,
        "code": code,
        "reason": reason,
        "requires_human_intervention": not allowed,
    }
