# Live verification: preserved failures and diagnostics

Deterministic synthetic data · Historical research only · Not investment advice · No trade execution · Not evidence of future performance · Not evidence about real markets

**Live verification is complete: all four checks passed.** The targeted [batch 007 resume](../artifacts/live_verification/batch_007/live_verification_results.json) completed C with two new real calls, 8,679 new tokens, and 26.677 seconds elapsed. It reused verified A/B/D evidence from batch 006. The aggregate is seven calls and 29,458 tokens, including the failed earlier C. No additional retry is needed; cost remains unknown.

The successful [C result](../artifacts/live_verification/batch_007/C_controlled_feedback/result.json) shows initial `r1a` rejected for omitting the deliberately required same-close/zero-latency limitation. Actual feedback reached the second provider context. The model returned child `r2a`, parent `r1a`, with the limitation and valid 6/3 parameters. Both search gates passed; the application locked `hyp-v1-22fb628b816eadfc`, executed 114 synthetic observations, and passed all 19 independent Skeptic checks. This is a completed real-provider revision, not a scripted response.

The earlier [batch 006](../artifacts/live_verification/batch_006/live_verification_results.json) passed A genuine research, B persisted duplicate prevention, and D explicit choices. It made five real provider calls, reported 20,779 total tokens, and took 76.129 seconds. A and D completed 6-month/3-asset synthetic experiments with an independent Skeptic verdict. B returned the prior experiment reference without a redundant backtest. The original output limit remained 2,500 tokens.

C received the deliberately injected same-close/zero-latency objection and produced a revised, otherwise valid candidate. Its child ID `c3` reused an initial ID that had been pruned from the beam. Parent-only validation missed that reuse, while the full-tree audit gate correctly rejected it before locking. This is a candidate-identity problem in the revision protocol. The [C result](../artifacts/live_verification/batch_006/C_controlled_feedback/result.json) remains unchanged as failed evidence.

The current prompt v3/schema v4 reserves `r1a/r1b/r1c` for initial candidates and `r2a/r2b` for children, with matching selection enums. Feedback now carries all prior IDs, including pruned nodes, and deterministic validation rejects any reuse. The model still chooses claims, parameters, citations, parent relationships, and revisions; the application owns only the identity namespace. Scientific parameters, budgets and both audit gates remain unchanged.

Earlier `batch_005` made one real call and stopped after 4.097 seconds. It reports `provider_incomplete`, upstream `incomplete`, and reason `max_output_tokens`, with 2,619 input tokens and zero output tokens. No lock or backtest exists. See [batch 005](../artifacts/live_verification/batch_005/live_verification_results.json). This gives the provider's reported reason, but does not establish why no generated tokens were reported. Earlier v1 responses completed in 1,424 and 1,536 output tokens under the same 2,500-token cap; simply increasing that cap is not supported by these records.

The provider schema's v2 claim pattern was a prefix-only expression, `^Test whether\b`, paired with a minimum length of 20. It accepts a complete claim under JSON Schema's search semantics, but not under whole-string regex matching. That difference is a possible constrained-decoder compatibility issue, not an established backend diagnosis. Schema v3 uses `^Test whether .+$`, which accepts the intended single-line claim under either matching approach. Initial/revision action enums, parent references, candidate bounds, text-length bounds, and independent validators are preserved. Prompt v2, model, token cap, fixture, and all scientific parameters are unchanged. The adapter also records the requested token cap and the canonical hash of the effective provider schema. See [current regression evidence](../artifacts/extension_verification/schema_compatibility_fix/verification_results.json).

The official [Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs) documents incomplete output handling and string patterns, with whole-string pattern examples. It does not establish the cause of that particular zero-output response. Batch 006 subsequently completed A and D under the same output cap after the compatibility correction; this is successful live evidence without proving the earlier backend cause.

The earlier `batch_003` made one real provider call, recorded 2,619 input tokens and zero output tokens, and stopped with `provider_incomplete` after 2.513 seconds. No hypothesis was locked and no backtest ran. The old adapter mapped every non-completed response to this status and omitted the provider's termination details. Its precise cause remains unknown. See the preserved [batch 003 result](../artifacts/live_verification/batch_003/live_verification_results.json). Batch 004 stopped at missing credentials and made zero calls.

The adapter now records the allowlisted `provider_response_status`, `incomplete_reason`, and `provider_error_code` when supplied by the SDK, while retaining unknowns as null. It distinguishes a failed response from an incomplete or unexpected-status response. The console prints these fields. Raw provider messages, refusal content, authentication headers, and arbitrary status/code strings remain excluded. This fixes the diagnostic gap; it does not establish or fix the unknown cause of batch 003. No prompts, models, output limits, retries, or research settings were changed for this diagnostic correction. Its [offline regression results](../artifacts/extension_verification/provider_diagnostics_fix/verification_results.json) are separate from live evidence.

The earlier `batch_002` authenticated successfully. Both OpenAI calls completed using `gpt-4.1-mini-2025-04-14`; the application then rejected the research proposal. This was a research-design protocol failure, not a missing-key or API-connectivity failure.

The preserved [batch result](../artifacts/live_verification/batch_002/live_verification_results.json) records two actual provider calls and 9,008 total tokens: 6,048 input and 2,960 output. Monetary cost was not provided and remains unknown. No hypothesis was locked, no backtest ran, and dependent checks B/C/D were not attempted.

## What failed

1. The first response proposed three candidates. All used declarative research-claim wording that failed the application's conservative requirement for explicit hypothesis/test framing. Candidates `cand1` and `cand3` also failed the lexical citation-support requirement for their methodological caution. This heuristic does not prove whether a claim is scientifically entailed by its excerpt.
2. The Coordinator sent the actual objections and retained parent IDs `cand2` and `cand1` to the model. The second response changed its wording and citation claims, showing that the feedback reached it, but again used `action: propose`, three candidates, and null parent IDs.
3. A revision requires `action: revise`, at most two candidates, and parent references to retained candidates. The application correctly stopped with `malformed_output`. The JSON itself was parseable; it violated the current round's protocol. The old console summary did not explain that distinction.

Both responses, contexts, and metadata remain in the original [audit](../artifacts/live_verification/batch_002/A_research/audit.jsonl) and [result](../artifacts/live_verification/batch_002/A_research/result.json). They have not been rewritten as successful evidence.

## Local correction

The provider schema now depends on the current round. Initial output permits an initial proposal or deferral; revision output permits a revision or deferral, at most two children, and only the actual retained parent IDs. The planning context also includes an explicit round contract. Hypothesis-framing instructions and citation feedback are more specific. Deterministic citation, parameter, safety, locking, and budget checks remain in place.

Malformed candidate-tree stops now retain concrete validation observations, and the live script prints each run's status and application-owned stop reasons. The correction changes the format contract, not the synthetic fixture, seed, numerical success rule, or candidate scores. It does not guarantee that the next model proposal will satisfy scientific grounding checks.

The earlier [regression verification](../artifacts/extension_verification/phase_contract_fix/verification_results.json) separates offline checks from genuine provider evidence. Those checks preceded the owner's subsequent batches. The current candidate-ID correction passed 259 tests, 31 offline scenarios, and 12 scripted-provider scenarios before the successful targeted live C run. Source hashes remain unchanged since those tests.

## Successful targeted resume: recorded command

The owner's existing environment key worked. After installing the correction, the owner ran only C while reusing verified A/B/D evidence:

```powershell
.\.venv\Scripts\python.exe scripts/run_live_verification.py --resume-batch artifacts/live_verification/batch_006
```

The narrow resume path verifies the source results, journal heads, result digests, provider provenance, and A/B/D checks before creating a provider. It creates a new numbered batch and runs only C with a fresh planning journal. The five earlier attempts, including the failed C attempt pair, count toward the combined limit of 16; the new C run allows at most four more. Original evidence is never rewritten. Resuming this source again in the same output root is refused to prevent resetting that budget. The source must be an original batch with exactly A/B/D passing and C failing; this is not a general-purpose resume chain. Unknown provider causes remain unknown rather than being guessed or hidden by an offline fallback.
