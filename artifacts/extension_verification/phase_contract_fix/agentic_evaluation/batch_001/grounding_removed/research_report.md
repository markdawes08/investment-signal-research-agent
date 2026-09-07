# Investment Signal Research Agent

**LLM-assisted research MVP | Deterministic synthetic data | Historical research only | Not investment advice | No trade execution | Not evidence of future performance | Not evidence about real markets**

Run: `run-efeb9edb87fdd011`

Status: **grounding_failed**

Verdict: **rejected**

Human intervention required: **True**

Synthetic results describe this fixture only; they provide no evidence about real markets.

## Research direction

Explore whether lower-volatility stocks have better risk-adjusted returns

## Execution provenance and persistent memory

```json
{
  "execution_mode": "llm",
  "provider_execution": {
    "calls_attempted": 0,
    "actual_provider_calls": 0,
    "calls": [],
    "token_usage": null,
    "cost_usd": null,
    "live_execution_verified": false
  },
  "memory_context": [],
  "duplicate_reference": null,
  "replication_rationale": null,
  "replay_provenance": null,
  "controlled_validation": null
}
```

Citation checks verify eligible IDs, exact summary excerpts, and limited lexical support. They are not a proof of entailment; human review of the source-to-claim relationship remains necessary.

## Independent skeptical review

Confidence: none

### Objections

- Eligible public grounding is insufficient, altered, or contains instruction-like content.

### Limitations

- No new research conclusion is supported by this stopped run.

## Audit and memory

`audit.jsonl` records role events and gates. `research_journal.jsonl` retains locks and conclusions across runs. Both use append-only SHA-256 chains. They are local integrity checks, not externally authenticated evidence.
