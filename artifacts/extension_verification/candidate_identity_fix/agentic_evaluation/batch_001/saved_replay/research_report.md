# Investment Signal Research Agent

**Deterministic saved-specification replay | Deterministic synthetic data | Historical research only | Not investment advice | No trade execution | Not evidence of future performance | Not evidence about real markets**

Run: `run-46832cff15056eec`

Status: **completed**

Verdict: **supported_in_synthetic_fixture_only**

Human intervention required: **False**

Synthetic results describe this fixture only; they provide no evidence about real markets.

## Research direction

Explore whether lower-volatility stocks have better risk-adjusted returns

## Preregistered hypothesis

ID: `hyp-v1-d52c05a78f156a54`

SHA-256: `d52c05a78f156a54afa73ffb140990bb5b5f262702d68431c2cdcac3cd13de7b`

```json
{
  "version": "1.0",
  "topic": "Explore whether lower-volatility stocks have better risk-adjusted returns",
  "signal": "trailing_sample_std_monthly_returns",
  "universe": [
    "SYN01",
    "SYN02",
    "SYN03",
    "SYN04",
    "SYN05",
    "SYN06",
    "SYN07",
    "SYN08",
    "SYN09",
    "SYN10",
    "SYN11",
    "SYN12"
  ],
  "lookback_months": 6,
  "holding_months": 1,
  "selection_count": 3,
  "benchmark": "monthly_rebalanced_equal_weight_universe",
  "cost_bps": 10.0,
  "risk_free_rate": 0.0,
  "as_of_date": "2024-12-31",
  "min_observations": 36,
  "success_rule": "strategy_net_sharpe > benchmark_net_sharpe",
  "seed": 42,
  "generator_version": "synthetic-monthly-v1",
  "start_date": "2014-12-31",
  "n_months": 121,
  "assumptions": [
    "Every price and return is deterministic synthetic data, not observed market history.",
    "Use 6 trailing monthly simple returns known at formation; hold for the following month.",
    "Observe and rebalance at the same synthetic month-end close, assuming zero latency.",
    "Choose the 3 lowest-volatility assets, equally weighted; break signal ties by asset identifier.",
    "Apply 10 basis points per unit gross traded notional to both portfolios, including initial investment.",
    "Use drifted pre-rebalance weights for turnover; do not charge a final liquidation.",
    "Deduct costs before the holding return: net return = (1 - cost fraction) * (1 + gross return) - 1.",
    "No leverage, short selling, external factors, dividends, taxes, borrowing, or brokerage access.",
    "The fixed complete universe has no entries, exits, delistings, or real-world survivorship coverage.",
    "The risk-free rate is fixed at zero and annualization uses 12 months per year.",
    "Monthly volatility is an educational adaptation; idiosyncratic and total volatility are different signals.",
    "The success rule is a descriptive synthetic-fixture comparison, not a statistical significance test.",
    "Data generation and backtest outcomes are unavailable during candidate selection and locking."
  ],
  "source_ids": [
    "ang-2004-volatility",
    "arnott-2019-protocol",
    "bailey-2017-overfitting",
    "baker-2010-benchmarks",
    "french-factor-methodology",
    "french-variance-methodology"
  ],
  "design_mode": "llm",
  "candidate_id": "design-a",
  "research_claim": "Test whether lower-volatility synthetic stocks have better risk-adjusted returns than an equal-weight benchmark.",
  "evidence_claims": [
    {
      "claim": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern.",
      "source_id": "baker-2010-benchmarks",
      "summary_excerpt": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern."
    },
    {
      "claim": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered.",
      "source_id": "arnott-2019-protocol",
      "summary_excerpt": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered."
    }
  ],
  "decision_rationale": "Compare a grounded feasible monthly volatility hypothesis without inspecting outcomes.",
  "limitations": [
    "Synthetic observations cannot establish any real-market investment effect."
  ],
  "parameter_basis": "agent_design_choice",
  "adaptation_rationale": null,
  "agent_assumptions": [
    "Monthly lookback and selection count are educational design choices."
  ]
}
```

## Bounded pre-outcome search

Structured proposals, deterministic observations, and any actual feedback are recorded below. No calculated outcomes are used for planning.

```json
{
  "method": "saved_specification_replay",
  "outcome_access": false,
  "provider_calls": 0,
  "original_search_hash": "3359eeb6a4b12556330a650a4fff3fa8cd206090a17a6f2ba6349523f99024d5",
  "saved_lock_hash": "d52c05a78f156a54afa73ffb140990bb5b5f262702d68431c2cdcac3cd13de7b"
}
```

## Public grounding

- [Benchmarks as Limits to Arbitrage: Understanding the Low-Volatility Anomaly](https://archive.nyu.edu/handle/2451/29593) (`baker-2010-benchmarks`): The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern.
- [The Cross-Section of Volatility and Expected Returns](https://www.nber.org/papers/w10852) (`ang-2004-volatility`): The authors study aggregate volatility exposure and firm-specific volatility in stock returns. Their evidence links high residual volatility relative to the Fama/French model with lower average returns. Residual volatility is distinct from total return volatility, so this paper motivates a separate candidate rather than directly validating the MVP's total-volatility specification.
- [Portfolios Formed Monthly on Variance](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_port_form_VAR.html) (`french-variance-methodology`): This methodology forms variance-ranked portfolios each month using NYSE breakpoints and lagged daily returns. Its variance window uses 60 days, with at least 20 observations. The MVP's 12-month signal uses synthetic monthly returns and is an explicitly different educational specification. Only the methodology description is indexed; numerical portfolio returns are not included.
- [Description of Fama/French Factors](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html) (`french-factor-methodology`): The page explains market excess returns and the size and value factors built from stock portfolios. These factors provide context for separating market exposure from residual volatility. A factor-based test would need dated factor observations and an explicit estimation model. This MVP retrieves the description only and neither downloads nor substitutes real factor data.
- [A Backtesting Protocol in the Era of Machine Learning](https://people.duke.edu/~charvey/Research/Published_Papers/G138_A_backtesting_protocol.pdf) (`arnott-2019-protocol`): The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered.
- [The Probability of Backtest Overfitting](https://escholarship.org/content/qt4w1110bb/qt4w1110bb.pdf) (`bailey-2017-overfitting`): Selecting the best historical result from many strategy trials can select noise. The paper develops a probability-of-overfitting framework and combinatorially symmetric cross-validation to examine this selection problem. The MVP records its bounded search and forbids performance-based revision; it does not implement the paper's probability estimator or establish statistical significance.

## Synthetic data validation

```json
{
  "passed": true,
  "errors": [],
  "row_count": 1452,
  "asset_count": 12,
  "month_count": 121,
  "data_hash": "7e7107a3f87b86354abdf6ed21bf1bd81b0368a6f1515049f45125471b524361",
  "checks": {
    "schema": true,
    "duplicates": true,
    "missing_values": true,
    "finite_prices": true,
    "positive_prices": true,
    "minimum_history": true,
    "equal_asset_histories": true,
    "expected_universe": true,
    "monthly_calendar": true,
    "expected_history": true,
    "availability_dates": true,
    "as_of_date_leakage": true,
    "synthetic_labels": true
  }
}
```

## Synthetic fixture metrics

All returns are fractions; costs apply to both portfolios. This is a pipeline exercise, not an investment performance claim.

| Metric | Strategy | Equal-weight benchmark |
|---|---:|---:|
| cumulative_return | 0.62322503 | 0.83320812 |
| annualized_return | 0.05231347 | 0.06587556 |
| annualized_volatility | 0.04791668 | 0.07005653 |
| sharpe_ratio | 1.09012062 | 0.94762809 |
| maximum_drawdown | -0.06679210 | -0.09427482 |
| average_monthly_turnover | 0.28456060 | 0.03274317 |
| total_turnover | 32.43990873 | 3.73272088 |
| total_cost_fraction | 0.03243991 | 0.00373272 |
| observation_count | 114 | 114 |

Methodology:

```json
{
  "data_kind": "deterministic_synthetic",
  "formation": "Trailing 6 sample-standard-deviation monthly returns, computed at formation close",
  "execution": "Observe and transact at the same synthetic month-end close with zero latency",
  "holding": "Next one-month simple price return; no dividends or corporate actions",
  "selection": "Three lowest-volatility assets; alphabetical asset-ID tie break",
  "weights": "Selected assets equal weighted; benchmark all 12 assets equal weighted monthly",
  "costs": "10 bps times L1 traded weight; initial entry included; both portfolios charged",
  "turnover": "Sum of absolute target minus prior post-return drifted weights; initial value 1",
  "net_return": "(1 - cost_fraction) * (1 + gross_return) - 1",
  "total_cost_fraction": "Sum of monthly fractions of pre-rebalance portfolio wealth; not dollar costs or cumulative wealth drag",
  "terminal_liquidation": false,
  "annualization": "12 monthly periods; sample standard deviation; zero risk-free rate",
  "maximum_drawdown": "Minimum wealth / running peak - 1, including initial wealth of 1",
  "inference": "Descriptive synthetic fixture comparison only; no statistical or real-market inference",
  "limitations": [
    "Same-close execution assumes zero latency and no slippage beyond fixed costs",
    "Fixed complete synthetic universe excludes survivorship, delistings, dividends, and liquidity effects",
    "A single deterministic sample cannot establish real-market validity or future performance"
  ]
}
```

## Execution provenance and persistent memory

```json
{
  "execution_mode": "replay",
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
  "replay_provenance": {
    "saved_lock_hash": "d52c05a78f156a54afa73ffb140990bb5b5f262702d68431c2cdcac3cd13de7b",
    "original_search": {
      "method": "llm_bounded_candidate_search",
      "mode": "llm",
      "max_initial_candidates": 3,
      "beam_width": 2,
      "max_depth": 2,
      "max_revisions": 1,
      "max_provider_calls": 4,
      "provider_calls": 1,
      "outcome_access": false,
      "rounds": [
        {
          "depth": 1,
          "proposal": {
            "action": "propose",
            "candidates": [
              {
                "id": "design-a",
                "parent_id": null,
                "research_claim": "Test whether lower-volatility synthetic stocks have better risk-adjusted returns than an equal-weight benchmark.",
                "signal": "total_volatility",
                "lookback_months": 6,
                "selection_count": 3,
                "evidence_claims": [
                  {
                    "claim": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern.",
                    "source_id": "baker-2010-benchmarks",
                    "summary_excerpt": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern."
                  },
                  {
                    "claim": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered.",
                    "source_id": "arnott-2019-protocol",
                    "summary_excerpt": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered."
                  }
                ],
                "assumptions": [
                  "Monthly lookback and selection count are educational design choices."
                ],
                "decision_rationale": "Compare a grounded feasible monthly volatility hypothesis without inspecting outcomes.",
                "limitations": [
                  "Synthetic observations cannot establish any real-market investment effect."
                ],
                "parameter_basis": "agent_design_choice",
                "adaptation_rationale": null
              }
            ],
            "selected_candidate_id": "design-a",
            "decision_rationale": "Compare a grounded feasible monthly volatility hypothesis without inspecting outcomes.",
            "deferral_reason": null
          },
          "candidates": [
            {
              "candidate": {
                "id": "design-a",
                "parent_id": null,
                "research_claim": "Test whether lower-volatility synthetic stocks have better risk-adjusted returns than an equal-weight benchmark.",
                "signal": "total_volatility",
                "lookback_months": 6,
                "selection_count": 3,
                "evidence_claims": [
                  {
                    "claim": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern.",
                    "source_id": "baker-2010-benchmarks",
                    "summary_excerpt": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern."
                  },
                  {
                    "claim": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered.",
                    "source_id": "arnott-2019-protocol",
                    "summary_excerpt": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered."
                  }
                ],
                "assumptions": [
                  "Monthly lookback and selection count are educational design choices."
                ],
                "decision_rationale": "Compare a grounded feasible monthly volatility hypothesis without inspecting outcomes.",
                "limitations": [
                  "Synthetic observations cannot establish any real-market investment effect."
                ],
                "parameter_basis": "agent_design_choice",
                "adaptation_rationale": null
              },
              "valid": true,
              "errors": [],
              "score": 9,
              "score_breakdown": {
                "grounding": 2,
                "methodological_suitability": 2,
                "feasibility": 3,
                "question_fit": 2
              },
              "duplicate_reference": null
            }
          ],
          "retained": [
            "design-a"
          ]
        }
      ],
      "feedback": [],
      "selected_candidate_id": "design-a",
      "selected_candidate": {
        "id": "design-a",
        "parent_id": null,
        "research_claim": "Test whether lower-volatility synthetic stocks have better risk-adjusted returns than an equal-weight benchmark.",
        "signal": "total_volatility",
        "lookback_months": 6,
        "selection_count": 3,
        "evidence_claims": [
          {
            "claim": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern.",
            "source_id": "baker-2010-benchmarks",
            "summary_excerpt": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern."
          },
          {
            "claim": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered.",
            "source_id": "arnott-2019-protocol",
            "summary_excerpt": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered."
          }
        ],
        "assumptions": [
          "Monthly lookback and selection count are educational design choices."
        ],
        "decision_rationale": "Compare a grounded feasible monthly volatility hypothesis without inspecting outcomes.",
        "limitations": [
          "Synthetic observations cannot establish any real-market investment effect."
        ],
        "parameter_basis": "agent_design_choice",
        "adaptation_rationale": null
      },
      "replication_rationale": null
    },
    "original_search_hash": "3359eeb6a4b12556330a650a4fff3fa8cd206090a17a6f2ba6349523f99024d5",
    "source_result_hash": "4b35ed161db3147c46e8c891147b22c531c6180fa9996fca788d716ad8f30b8d",
    "original_audit_head": "cb48b7c69661a5d701425e809b7e7a2d559bfef35c5f0f19995303500222ac53"
  },
  "controlled_validation": null
}
```

Citation checks verify eligible IDs, exact summary excerpts, and limited lexical support. They are not a proof of entailment; human review of the source-to-claim relationship remains necessary.

## Independent skeptical review

Confidence: limited_to_deterministic_fixture

### Objections

- None recorded.

### Limitations

- Deterministic saved-specification replay | Deterministic synthetic data | Historical research only | Not investment advice | No trade execution | Not evidence of future performance | Not evidence about real markets
- Synthetic returns are not empirical evidence about real markets or expected profits.
- A single fixture and zero-risk-free Sharpe comparison do not establish statistical significance or causality.
- The fixed universe omits delistings, changing constituents, taxes, market impact, and corporate actions.
- Data checks attest structure and recorded hashes; the Skeptic does not independently rerun the generator seed.
- The Skeptic is independently coded deterministic checking, not an independent human or language model.
- Local hash chains lack external checkpoints and cannot detect valid tail deletion or complete chain rewriting.

## Audit and memory

`audit.jsonl` records role events and gates. `research_journal.jsonl` retains locks and conclusions across runs. Both use append-only SHA-256 chains. They are local integrity checks, not externally authenticated evidence.
