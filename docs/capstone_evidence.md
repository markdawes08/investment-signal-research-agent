# Capstone evidence handoff

**Deterministic synthetic data · Historical research only · Not investment advice · No trade execution · Not evidence of future performance · Not evidence about real markets**

This is a factual handoff for a later report, slide deck, and recording. Those presentation deliverables are not part of this repository extension. **All four genuine-provider verification checks passed.** Batch 007 completed controlled feedback/revision C and reused integrity-verified batch 006 A research, B persisted duplicate prevention, and D explicit-choice evidence. The resume made two new calls, bringing the aggregate to seven including the preserved failed C attempt. The full history and limits are documented in [the diagnosis](live_verification_troubleshooting.md). Local implementation and verification are complete; Git commands and publication remain with the owner.

## Problem and intended user

Students and research engineers need a reviewable way to turn broad investment-signal ideas into falsifiable experiments without changing hypotheses after seeing results. This project exposes evidence, design choices, validation, point-in-time calculations, skeptical review, and integrity-linked memory. Its synthetic outcomes are software fixtures, never evidence about real stocks or future performance.

## Implemented architecture and evolution

The Coordinator owns actions, budgets, feedback, duplicate decisions, and stopping gates. The Hypothesis Generator uses either the preserved deterministic offline tree or, in explicit LLM mode, the optional OpenAI Responses adapter. Data Engineer generates and validates the fixed synthetic fixture. Backtester executes the unchanged accepted design. Skeptic independently checks provenance, mode contracts, signals, weights, costs, observation counts, and statistics.

The earlier simplified prototype had predefined 12-month/four-asset selection and passive journals. The extension adds structured model-authored candidate designs, a real application decision/action/observation/revision loop, active verified memory without performance, scientific duplicate fingerprints, explicit replication, and saved-specification replay. LLM choices are limited to 6/12 trailing months and 3/4 selected assets. The model's accepted values drive execution; the fixture, seed, dates, benchmark and cost convention remain fixed.

Only the Hypothesis Generator is LLM-powered. CrewAI, LangGraph, MCP, learned embeddings, vector databases, live-market data, brokerage connections, and additional LLM agents are not implemented. TF-IDF uses a small explicit synonym map. See [architecture.md](architecture.md) for the diagram, formulas, schemas, event contracts, and integrity threat model.

## Measured verification

All provider interactions in the unittest and agentic acceptance suites are explicitly mocked. Their success does not establish live provider behavior.

| Verification | Actual result | Evidence |
|---|---|---|
| Source baseline before editing | 97 tests passed; 18.273s; original evaluation 31/31 | [Verification record](../artifacts/extension_verification/verification_results.json) |
| Earlier installed extension, Python 3.13.5, optional SDK 2.54.0 | 214/214 tests passed; 41.479s | [Test log](../artifacts/extension_verification/test_console_output.txt), [JSON](../artifacts/extension_verification/unit_test_results.json) |
| Earlier phase-contract correction, reinstalled package | 225/225 tests passed; 42.478s; offline 31/31, mocked agentic 12/12, and saved v1 replay passed; zero additional real calls | [Phase-contract verification](../artifacts/extension_verification/phase_contract_fix/verification_results.json), [test log](../artifacts/extension_verification/phase_contract_fix/tests.txt) |
| Earlier provider-diagnostic correction, reinstalled package | 232/232 tests passed; 42.708s; offline 31/31, mocked agentic 12/12, and saved v1 replay passed; zero additional real calls | [Diagnostic verification](../artifacts/extension_verification/provider_diagnostics_fix/verification_results.json), [test log](../artifacts/extension_verification/provider_diagnostics_fix/tests.txt) |
| Earlier schema-compatibility correction, reinstalled package | 234/234 tests passed; 23.121s; offline 31/31, mocked agentic 12/12, and saved v1 replay passed; zero additional real calls | [Schema verification](../artifacts/extension_verification/schema_compatibility_fix/verification_results.json), [test log](../artifacts/extension_verification/schema_compatibility_fix/tests.txt) |
| Current candidate-identity/resume correction, reinstalled package | **259/259 tests passed; 48.678s; offline 31/31, mocked agentic 12/12, saved v1 replay and genuine A replay passed; zero additional real calls** | [Current verification](../artifacts/extension_verification/candidate_identity_fix/verification_results.json), [test log](../artifacts/extension_verification/candidate_identity_fix/tests.txt), [genuine A replay](../artifacts/extension_verification/candidate_identity_fix/live_saved_replay/result.json) |
| Preserved offline acceptance | 31/31 passed; 1.594s | [Offline evaluation](../artifacts/offline_evaluation/evaluation_results.json) |
| Scripted-provider agentic acceptance | 12/12 passed; 1.526s; zero real calls | [Agentic evaluation](../artifacts/agentic_evaluation/evaluation_results.json) |
| Earlier isolated source copy, Python 3.11.9, base installation without OpenAI SDK | 214 tests passed; 46.083s; both acceptance suites, example, corpus and replay succeeded | [Clean-environment checks](../artifacts/extension_verification/verification_results.json) |
| Missing credentials in fresh base environment | Explicit exit 2; no silent offline fallback | [Clean-environment checks](../artifacts/extension_verification/verification_results.json) |
| Actual SDK call interface | Installed `Responses.create` signature supports configured arguments; no API call made | [SDK check](../artifacts/extension_verification/verification_results.json) |
| Initial genuine provider batch | `blocked_missing_credentials`; **0 actual provider calls**, 1 adapter invocation | [Preserved initial A attempt](../artifacts/live_verification/batch_001/A_research/result.json) |
| Owner's second genuine provider batch | `malformed_output`; **2 actual provider calls**, 9,008 total tokens, 34.150s; no lock or backtest | [Preserved batch](../artifacts/live_verification/batch_002/live_verification_results.json), [diagnosis](live_verification_troubleshooting.md) |
| Owner's third genuine provider batch | `provider_incomplete`; **1 actual provider call**, 2,619 input tokens, zero output tokens, 2.513s; exact termination cause unknown; no lock or backtest | [Preserved batch](../artifacts/live_verification/batch_003/live_verification_results.json) |
| Batch 004 | `missing_credentials`; zero calls | [Preserved batch](../artifacts/live_verification/batch_004/live_verification_results.json) |
| Earlier batch 005 | `provider_incomplete`, reason `max_output_tokens`; **1 actual call**, 2,619 input tokens, zero output tokens, 4.097s; no lock or backtest | [Preserved batch](../artifacts/live_verification/batch_005/live_verification_results.json) |
| Earlier genuine batch 006 | A/B/D passed, C failed; 5 actual calls; 20,779 total tokens; 76.129s | [Preserved verification](../artifacts/live_verification/batch_006/live_verification_results.json) |
| Completed genuine batch 007 resume | **4/4 checks passed; 2 new calls, 7 aggregate calls; 8,679 new tokens; 26.677s for the resume** | [Completed live verification](../artifacts/live_verification/batch_007/live_verification_results.json), [evidence integrity review](../artifacts/extension_verification/live_evidence_review.json) |

All original 97 tests remain, preserving the offline behavioral protections. New mode tests extend supported choices rather than removing the old fixed contract. An explicit beta-adaptation test was corrected to name total volatility in the executable claim; it still verifies honest adaptation, rather than allowing beta-labeled output from a total-volatility harness. Additional tests cover strict output, citations, prompt injection, partial constraints, feedback and call budgets, provider failures, persistent process restarts, memory exclusion, tampering, numerical gates, and saved replay.

The preserved 12/4 fixture reports 108 synthetic holding months; strategy net annualized return 4.7979%, annualized volatility 4.8814%, Sharpe 0.986008; benchmark 5.8774%, 6.9562%, and 0.857269. The strategy's lower absolute return and higher Sharpe are both disclosed. Four controlled valid parameter combinations execute correctly, and six-month designs have 114 holding observations. No setting was chosen because it produced favorable results.

## Concrete retrieval example

The direction “Explore whether lower-volatility stocks have better risk-adjusted returns” retrieves `baker-2010-benchmarks` and the original summary itself, together with methodological sources including `arnott-2019-protocol`. A recorded candidate includes exact summary excerpts for its declared claims. Lookback and selection size are separately labeled `agent_design_choice`.

The [batch_002 6/3 result](../artifacts/agentic_evaluation/batch_002/accepted_6_months_3_assets/result.json) records the public summaries in `planning_contexts`, citation excerpts in `evidence_claims`, and the accepted parameters. The [necessary-grounding removal case](../artifacts/agentic_evaluation/batch_002/grounding_removed/result.json) deliberately removes direct total-volatility sources: it produces `grounding_failed`, makes zero provider calls, and never runs a backtest. Removing necessary evidence therefore changes execution, rather than just changing a narrative.

Exact excerpts and lexical overlap establish reviewable attribution, not semantic entailment. The validator cannot prove all associated prose is supported, and human review of scientific meaning remains necessary.

## Concrete persistent-memory example

The first scripted design completes as `hyp-v1-d52c05a78f156a54`. The next request reads the persisted shared journal and returns `duplicate_deferred` with no second backtest. Its prior reference is:

```text
journal_record_id: eed3bd2861a211c1841bd921931de7ad9610e8e94e928403ee48d8a609684aab
scientific_fingerprint: eb3b0f678ad669d0b2dbd36037b682e8f6319ff965216d040a9cf0e0d2270ff5
```

See [first run](../artifacts/agentic_evaluation/batch_002/memory_first/result.json), [second run](../artifacts/agentic_evaluation/batch_002/memory_second/result.json), [shared journal](../artifacts/agentic_evaluation/batch_002/shared_journal/experiments.jsonl), and [new-process duplicate reference](../artifacts/agentic_evaluation/batch_002/restart_reference.json). Tests additionally run the Coordinator after a subprocess restart. These records demonstrate persisted application behavior using scripted providers, not genuine model memory behavior.

The fingerprint ignores topic wording, timestamps, explanations, and source order. Planning receives only substantive specifications, IDs, and controlled methodological limitations; it never receives prior returns, Sharpe values, profitability rankings, or performance verdicts. Every changed design axis must be explicitly constrained by the user; an identical experiment needs a user-supplied replication rationale.

## Concrete feedback/revision example

In the [deliberately scripted feedback case](../artifacts/agentic_evaluation/batch_002/feedback_revision/research_report.md), initial candidate `design-a` proposes unsupported lookback 9. The actual deterministic assessment rejects it and returns:

> design-a: Supported lookback_months choices are 6 or 12.

The next provider context contains that objection and retained parent ID. Candidate `design-b`, parent `design-a`, proposes lookback 6 and selection count 3. The application validates the new object, locks it, generates data, executes 114 synthetic observations, and receives the independent Skeptic verdict. The [audit](../artifacts/agentic_evaluation/batch_002/feedback_revision/audit.jsonl) shows two rounds before locking and no pre-lock results. This verifies actual application feedback plumbing; the provider response is scripted and is not evidence of a successful live model revision.

Live case C deliberately adds a requirement to state same-close execution and zero latency in limitations. In the successful [batch 007 C result](../artifacts/live_verification/batch_007/C_controlled_feedback/result.json), initial `r1a` lacked this limitation. The actual objection appeared in the second provider context; the model returned `r2a`, parent `r1a`, with the limitation and valid 6/3 parameters. It passed both search gates, locked `hyp-v1-22fb628b816eadfc`, executed 114 synthetic observations, and passed all 19 independent Skeptic checks. There were three initial candidates, a two-candidate beam, two revised children, and two actual calls. The other child, `r2b`, was rejected for duplicate parameters and the missing limitation. This condition was deliberately injected to demonstrate pre-lock methodological feedback; no seed, data, or outcome was changed. If a first proposal already satisfies the condition, the script reports that no feedback was demonstrated and does not force another attempt.

## Exact verification commands

From the repository root, the installed primary interpreter was `.\.venv\Scripts\python.exe`. The fresh isolated source copy used a separate Python 3.11 environment with only the base package. No Git commands were run.

```powershell
.\.venv\Scripts\python.exe -m pip install ".[llm]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m signal_research_agent evaluate --output-dir artifacts/offline_evaluation
.\.venv\Scripts\python.exe -m signal_research_agent evaluate --suite agentic --output-dir artifacts/agentic_evaluation
.\.venv\Scripts\python.exe -m signal_research_agent run --topic "Explore whether lower-volatility stocks have better risk-adjusted returns" --output-dir artifacts/run_extension
.\.venv\Scripts\python.exe -m signal_research_agent replay --result artifacts/agentic_evaluation/batch_001/accepted_6_months_3_assets/result.json --output-dir artifacts/replay_example
.\.venv\Scripts\python.exe scripts/run_live_verification.py --output-dir artifacts/live_verification
.\.venv\Scripts\python.exe -m pip check
```

Fresh-copy commands were `py -3.11 -m venv .venv`, `.\.venv\Scripts\python.exe -m pip install .`, then the same test, offline evaluation, agentic evaluation, corpus, research and replay commands. The clean LLM command returned the expected missing-credentials status with exit 2. SDK signature inspection used Python `inspect.signature` without contacting the provider. Full source-file fingerprints and measured exit codes are in the verification JSON.

## Completed live verification

Latest update: all four checks passed after batch 007 resumed C. The verified batch 006/007 sequence used seven actual calls and seven adapter attempts against the combined limit of 16. Five were earlier calls, including the failed C pair; only two were new. Combined usage was 20,997 input tokens plus 8,461 output tokens, or 29,458 total. The resume took 26.677 seconds. Across all preserved batches there have been eleven distinct actual calls; reused evidence is not counted twice. The actual model remains `gpt-4.1-mini-2025-04-14` with the 2,500-token cap. Cost remains unknown. No further live retry is needed.

The real [A run](../artifacts/live_verification/batch_006/A_research/result.json) locked `hyp-v1-72e2697bc0f0e49a` with lookback 6 and selection count 3, executed 114 synthetic observations, and received `supported_in_synthetic_fixture_only`. Synthetic strategy annualized return is 5.2313% and Sharpe 1.090121, versus benchmark 6.5876% and 0.947628. These figures describe the synthetic fixture, not real investment performance. [D](../artifacts/live_verification/batch_006/D_explicit_choices/result.json) independently honored the explicit 6/3 constraint and completed. Actual model IDs, response IDs, and token usage are in each result; monetary cost remains unknown.

The real [B request](../artifacts/live_verification/batch_006/B_duplicate/result.json) read prior planning memory, identified the same scientific fingerprint, and returned `duplicate_deferred` with no backtest. Its prior reference is A's hypothesis above and journal record `0360108cdd5a3e0bc6ef88ff8fba214d5bcdbdf0e856158c74b742d19e2db7a0`. Prior performance was excluded from the provider planning context.

In the earlier real [C failure](../artifacts/live_verification/batch_006/C_controlled_feedback/result.json), the second response supplied the required limitation and valid 6/3 parameters but reused `c3`, an ID from a pruned initial candidate. The whole-tree gate correctly rejected it. Current provider schemas reserve disjoint IDs for the two rounds, and validation checks all earlier IDs before selection. The successful resumed C used prompt `research-design-v3` and schema `research-proposal-v4`; reused A/B/D evidence retains its original prompt v2/schema v3. Those runs were verified, not rerun or relabeled with the newer versions. Failed attempts remain unchanged.

The owner's existing PowerShell environment key worked. The exact successful resume command was:

```powershell
.\.venv\Scripts\python.exe scripts/run_live_verification.py --resume-batch artifacts/live_verification/batch_006
```

This source is already resumed; running the same resume again is correctly refused. The batch has at most 16 adapter attempts and at most four per run including retries. A durable reservation prevents an interrupted resume from resetting the budget. It preserves every attempt in a new directory and does not change fixture seeds or settings to chase outcomes. The provider-contract fixes addressed recorded format failures, not numerical results. A failed or incomplete historical batch remains labeled accordingly. Never paste a credential into chat or a command argument.

## Safety and limitations

Input screening precedes provider access. The model has no tools, arbitrary code execution, account access, or trading capability. Retrieved documents and memory are untrusted data, not instructions. Strict schemas, authenticated-by-local-corpus source metadata, exact excerpts, mode contracts, full lock hashes, data gates, independent arithmetic, bounded calls/revisions, outcome exclusion, and append-only chains work together. “Authenticated by local corpus” means equality with bundled records, not external cryptographic authentication.

Human intervention is required for refusals, unsupported designs, insufficient/conflicting grounding, unresolved output objections, provider/budget failures, duplicates without rationale, data/leakage failures, altered locks, invalid memory/replay, or unreliable conclusions. A valid unsupported synthetic result is still a completed research outcome.

Limits include heuristic English safety and claim checks, a small curated corpus, four executable parameter combinations, local rather than process-isolated agents, same-close execution, a fabricated complete universe, zero risk-free rate, no statistical significance or real-market generalization, and unkeyed local chains that cannot detect valid-tail deletion or complete rewriting without a checkpoint. SDK timeouts are HTTP timeouts, not operating-system deadlines. Replication is numerical and can differ at final floating-point bits across interpreter versions. All required live checks passed; this bounded demonstration does not guarantee every future model proposal will satisfy the schema or scientific grounding checks.

## Short recording sequence

1. State the synthetic/research-only boundary and show the three execution modes in README.
2. Run `corpus` and show one original summary and stable source ID.
3. Run the offline workflow and show the lock event before data generation/backtesting.
4. Clearly announce “scripted-provider test”; open the feedback example and trace invalid 9-month proposal → objection → valid 6-month child.
5. Show the first/second shared-memory runs and subprocess duplicate reference; show no second backtest and no prior metrics in planning context.
6. Replay the saved 6/3 specification and show zero provider calls and matching numerical output.
7. Show the completed live summary and trace actual `r1a` objection → `r2a` revision → lock → Skeptic review in batch 007. Show reused A/B/D references and preserved failed C separately. The recording can use saved evidence and replay without additional paid calls.
8. End with the measured tests, independent Skeptic limits, and remaining research work.

## Repository handoff

Existing public repository URL: [investment-signal-research-agent](https://github.com/markdawes08/investment-signal-research-agent). All Git commands and publication remain with the owner. No new commit, pushed SHA, or newly published contents are claimed. The local extension and evidence handoff are complete, including successful genuine research, persistent duplicate prevention, controlled feedback/revision, and explicit supported choices. The report, slides, and recorded presentation are separate deliverables.
