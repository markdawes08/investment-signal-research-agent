# Investment Signal Research Agent

**LLM-assisted research MVP | Deterministic synthetic data | Historical research only | Not investment advice | No trade execution | Not evidence of future performance | Not evidence about real markets**

Run: `run-efeb9edb87fdd011`

Status: **completed**

Verdict: **supported_in_synthetic_fixture_only**

Human intervention required: **False**

Synthetic results describe this fixture only; they provide no evidence about real markets.

## Research direction

Explore whether lower-volatility stocks have better risk-adjusted returns

## Preregistered hypothesis

ID: `hyp-v1-caba4786545b70a6`

SHA-256: `caba4786545b70a640c4f5581d35da0cc4406a894c1d12322584cf33d0212aae`

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
  "candidate_id": "C1",
  "research_claim": "Test whether portfolios selecting the 3 lowest total-volatility stocks over a 6-month lookback have higher subsequent risk-adjusted returns than portfolios with higher-volatility selections, using synthetic monthly returns.",
  "evidence_claims": [
    {
      "claim": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks, motivating comparisons of total volatility.",
      "source_id": "baker-2010-benchmarks",
      "summary_excerpt": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern."
    },
    {
      "claim": "Methodology forms variance-ranked portfolios each month using lagged daily returns and a variance window of 60 days; MVP uses synthetic monthly returns and a 12-month window as a different educational specification.",
      "source_id": "french-variance-methodology",
      "summary_excerpt": "This methodology forms variance-ranked portfolios each month using NYSE breakpoints and lagged daily returns. Its variance window uses 60 days, with at least 20 observations. The MVP's 12-month signal uses synthetic monthly returns and is an explicitly different educational specification. Only the methodology description is indexed; numerical portfolio returns are not included."
    },
    {
      "claim": "Research protocols recommend pre-specification of hypotheses to reduce false discoveries in financial research.",
      "source_id": "arnott-2019-protocol",
      "summary_excerpt": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered."
    }
  ],
  "decision_rationale": "6-month lookback and 3-stock selection match explicit constraints and allow feasible low-volatility portfolio testing with the synthetic dataset.",
  "limitations": [
    "Synthetic data may not capture all real market dynamics.",
    "Small portfolio size could limit generalizability.",
    "No factor adjustment due to synthetic data limitations."
  ],
  "parameter_basis": "agent_design_choice",
  "adaptation_rationale": null,
  "agent_assumptions": [
    "Synthetic monthly return volatility approximates true total volatility for ranking.",
    "A 6-month lookback captures recent volatility dynamics relevant for portfolio formation.",
    "Selecting the 3 lowest volatility stocks is sufficient to test the low-volatility effect in a small portfolio setting."
  ]
}
```

## Bounded pre-outcome search

Structured proposals, deterministic observations, and any actual feedback are recorded below. No calculated outcomes are used for planning.

```json
{
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
            "id": "C1",
            "parent_id": null,
            "research_claim": "Test whether portfolios selecting the 3 lowest total-volatility stocks over a 6-month lookback have higher subsequent risk-adjusted returns than portfolios with higher-volatility selections, using synthetic monthly returns.",
            "signal": "total_volatility",
            "lookback_months": 6,
            "selection_count": 3,
            "evidence_claims": [
              {
                "claim": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks, motivating comparisons of total volatility.",
                "source_id": "baker-2010-benchmarks",
                "summary_excerpt": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern."
              },
              {
                "claim": "Methodology forms variance-ranked portfolios each month using lagged daily returns and a variance window of 60 days; MVP uses synthetic monthly returns and a 12-month window as a different educational specification.",
                "source_id": "french-variance-methodology",
                "summary_excerpt": "This methodology forms variance-ranked portfolios each month using NYSE breakpoints and lagged daily returns. Its variance window uses 60 days, with at least 20 observations. The MVP's 12-month signal uses synthetic monthly returns and is an explicitly different educational specification. Only the methodology description is indexed; numerical portfolio returns are not included."
              },
              {
                "claim": "Research protocols recommend pre-specification of hypotheses to reduce false discoveries in financial research.",
                "source_id": "arnott-2019-protocol",
                "summary_excerpt": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered."
              }
            ],
            "assumptions": [
              "Synthetic monthly return volatility approximates true total volatility for ranking.",
              "A 6-month lookback captures recent volatility dynamics relevant for portfolio formation.",
              "Selecting the 3 lowest volatility stocks is sufficient to test the low-volatility effect in a small portfolio setting."
            ],
            "decision_rationale": "6-month lookback and 3-stock selection match explicit constraints and allow feasible low-volatility portfolio testing with the synthetic dataset.",
            "limitations": [
              "Synthetic data may not capture all real market dynamics.",
              "Small portfolio size could limit generalizability.",
              "No factor adjustment due to synthetic data limitations."
            ],
            "parameter_basis": "agent_design_choice",
            "adaptation_rationale": null
          },
          {
            "id": "C2",
            "parent_id": null,
            "research_claim": "Test whether portfolios selecting the 3 lowest total-volatility stocks over a 12-month lookback have better subsequent risk-adjusted returns than higher-volatility selections, using synthetic monthly returns.",
            "signal": "total_volatility",
            "lookback_months": 12,
            "selection_count": 3,
            "evidence_claims": [
              {
                "claim": "The methodology uses 12-month total volatility computed from synthetic monthly returns to form portfolios.",
                "source_id": "french-variance-methodology",
                "summary_excerpt": "The MVP's 12-month signal uses synthetic monthly returns and is an explicitly different educational specification. Only the methodology description is indexed; numerical portfolio returns are not included."
              },
              {
                "claim": "Low-volatility anomaly literature motivates testing total volatility portfolios despite debate about implementation specifics.",
                "source_id": "baker-2010-benchmarks",
                "summary_excerpt": "This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern."
              },
              {
                "claim": "Rigorous research protocol requires pre-outcome hypothesis locking to reduce overfitting risk.",
                "source_id": "arnott-2019-protocol",
                "summary_excerpt": "Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success."
              }
            ],
            "assumptions": [
              "A 12-month lookback better smooths volatility estimates than shorter windows.",
              "A selection count of 3 fits experimental constraints for a small focused portfolio.",
              "Synthetic monthly returns can replicate variance ranking comparably to real returns for this horizon."
            ],
            "decision_rationale": "Longer lookback may yield more stable volatility estimates, potentially improving test validity under synthetic data.",
            "limitations": [
              "Synthetic data may not reflect real-world volatility persistence.",
              "Longer lookback may dilute recent volatility changes.",
              "Small selection count limits breadth of comparison."
            ],
            "parameter_basis": "agent_design_choice",
            "adaptation_rationale": null
          },
          {
            "id": "C3",
            "parent_id": null,
            "research_claim": "Test whether portfolios selecting the 4 lowest total-volatility stocks over a 6-month lookback have superior subsequent risk-adjusted returns than higher-volatility selections, using synthetic monthly returns.",
            "signal": "total_volatility",
            "lookback_months": 6,
            "selection_count": 4,
            "evidence_claims": [
              {
                "claim": "Agent-design choices include selection counts of 3 or 4 and total volatility lookbacks of 6 or 12 months for experimental permutations.",
                "source_id": "french-variance-methodology",
                "summary_excerpt": "The MVP's 12-month signal uses synthetic monthly returns and is an explicitly different educational specification."
              },
              {
                "claim": "Low-volatility anomaly research supports testing portfolios formed with total volatility signals.",
                "source_id": "baker-2010-benchmarks",
                "summary_excerpt": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions."
              },
              {
                "claim": "Use of falsifiable research design and pre-specified hypotheses is endorsed to avoid backtest overfitting.",
                "source_id": "arnott-2019-protocol",
                "summary_excerpt": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection."
              }
            ],
            "assumptions": [
              "Increasing selection count to 4 may better represent the low-volatility effect over a slightly larger portfolio.",
              "6-month volatility estimation remains responsive and feasible within constraints.",
              "Synthetic data quality supports both 3 and 4 selection counts in similar fashion."
            ],
            "decision_rationale": "Selecting 4 stocks over 6 months balances portfolio size slightly upward while respecting the 6-month explicit constraint.",
            "limitations": [
              "Small portfolio sizes limit statistical power.",
              "Synthetic returns may not perfectly replicate volatility effects.",
              "No adjustment for factor exposures possible."
            ],
            "parameter_basis": "agent_design_choice",
            "adaptation_rationale": null
          }
        ],
        "selected_candidate_id": "C1",
        "decision_rationale": "Candidate C1 strictly satisfies the explicit constraints of a 6-month lookback and a selection count of 3, focusing on a minimal but clean test of the low-volatility hypothesis with synthetic data. This matches the user-specified parameters exactly and leverages literature support for total volatility as the signal, with pre-specified design to minimize overfitting risk.",
        "deferral_reason": null
      },
      "candidates": [
        {
          "candidate": {
            "id": "C1",
            "parent_id": null,
            "research_claim": "Test whether portfolios selecting the 3 lowest total-volatility stocks over a 6-month lookback have higher subsequent risk-adjusted returns than portfolios with higher-volatility selections, using synthetic monthly returns.",
            "signal": "total_volatility",
            "lookback_months": 6,
            "selection_count": 3,
            "evidence_claims": [
              {
                "claim": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks, motivating comparisons of total volatility.",
                "source_id": "baker-2010-benchmarks",
                "summary_excerpt": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern."
              },
              {
                "claim": "Methodology forms variance-ranked portfolios each month using lagged daily returns and a variance window of 60 days; MVP uses synthetic monthly returns and a 12-month window as a different educational specification.",
                "source_id": "french-variance-methodology",
                "summary_excerpt": "This methodology forms variance-ranked portfolios each month using NYSE breakpoints and lagged daily returns. Its variance window uses 60 days, with at least 20 observations. The MVP's 12-month signal uses synthetic monthly returns and is an explicitly different educational specification. Only the methodology description is indexed; numerical portfolio returns are not included."
              },
              {
                "claim": "Research protocols recommend pre-specification of hypotheses to reduce false discoveries in financial research.",
                "source_id": "arnott-2019-protocol",
                "summary_excerpt": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered."
              }
            ],
            "assumptions": [
              "Synthetic monthly return volatility approximates true total volatility for ranking.",
              "A 6-month lookback captures recent volatility dynamics relevant for portfolio formation.",
              "Selecting the 3 lowest volatility stocks is sufficient to test the low-volatility effect in a small portfolio setting."
            ],
            "decision_rationale": "6-month lookback and 3-stock selection match explicit constraints and allow feasible low-volatility portfolio testing with the synthetic dataset.",
            "limitations": [
              "Synthetic data may not capture all real market dynamics.",
              "Small portfolio size could limit generalizability.",
              "No factor adjustment due to synthetic data limitations."
            ],
            "parameter_basis": "agent_design_choice",
            "adaptation_rationale": null
          },
          "valid": true,
          "errors": [],
          "score": 10,
          "score_breakdown": {
            "grounding": 3,
            "methodological_suitability": 2,
            "feasibility": 3,
            "question_fit": 2
          },
          "duplicate_reference": null
        },
        {
          "candidate": {
            "id": "C2",
            "parent_id": null,
            "research_claim": "Test whether portfolios selecting the 3 lowest total-volatility stocks over a 12-month lookback have better subsequent risk-adjusted returns than higher-volatility selections, using synthetic monthly returns.",
            "signal": "total_volatility",
            "lookback_months": 12,
            "selection_count": 3,
            "evidence_claims": [
              {
                "claim": "The methodology uses 12-month total volatility computed from synthetic monthly returns to form portfolios.",
                "source_id": "french-variance-methodology",
                "summary_excerpt": "The MVP's 12-month signal uses synthetic monthly returns and is an explicitly different educational specification. Only the methodology description is indexed; numerical portfolio returns are not included."
              },
              {
                "claim": "Low-volatility anomaly literature motivates testing total volatility portfolios despite debate about implementation specifics.",
                "source_id": "baker-2010-benchmarks",
                "summary_excerpt": "This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern."
              },
              {
                "claim": "Rigorous research protocol requires pre-outcome hypothesis locking to reduce overfitting risk.",
                "source_id": "arnott-2019-protocol",
                "summary_excerpt": "Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success."
              }
            ],
            "assumptions": [
              "A 12-month lookback better smooths volatility estimates than shorter windows.",
              "A selection count of 3 fits experimental constraints for a small focused portfolio.",
              "Synthetic monthly returns can replicate variance ranking comparably to real returns for this horizon."
            ],
            "decision_rationale": "Longer lookback may yield more stable volatility estimates, potentially improving test validity under synthetic data.",
            "limitations": [
              "Synthetic data may not reflect real-world volatility persistence.",
              "Longer lookback may dilute recent volatility changes.",
              "Small selection count limits breadth of comparison."
            ],
            "parameter_basis": "agent_design_choice",
            "adaptation_rationale": null
          },
          "valid": false,
          "errors": [
            "Candidate violates the explicit lookback_months constraint.",
            "Every executable candidate needs a supported methodological-caution claim.",
            "Evidence claim 3 (arnott-2019-protocol): the claim lacks minimal lexical support in its cited excerpt; cite an excerpt supporting the stated claim or remove the unsupported claim."
          ],
          "score": 8,
          "score_breakdown": {
            "grounding": 2,
            "methodological_suitability": 1,
            "feasibility": 3,
            "question_fit": 2
          }
        },
        {
          "candidate": {
            "id": "C3",
            "parent_id": null,
            "research_claim": "Test whether portfolios selecting the 4 lowest total-volatility stocks over a 6-month lookback have superior subsequent risk-adjusted returns than higher-volatility selections, using synthetic monthly returns.",
            "signal": "total_volatility",
            "lookback_months": 6,
            "selection_count": 4,
            "evidence_claims": [
              {
                "claim": "Agent-design choices include selection counts of 3 or 4 and total volatility lookbacks of 6 or 12 months for experimental permutations.",
                "source_id": "french-variance-methodology",
                "summary_excerpt": "The MVP's 12-month signal uses synthetic monthly returns and is an explicitly different educational specification."
              },
              {
                "claim": "Low-volatility anomaly research supports testing portfolios formed with total volatility signals.",
                "source_id": "baker-2010-benchmarks",
                "summary_excerpt": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions."
              },
              {
                "claim": "Use of falsifiable research design and pre-specified hypotheses is endorsed to avoid backtest overfitting.",
                "source_id": "arnott-2019-protocol",
                "summary_excerpt": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection."
              }
            ],
            "assumptions": [
              "Increasing selection count to 4 may better represent the low-volatility effect over a slightly larger portfolio.",
              "6-month volatility estimation remains responsive and feasible within constraints.",
              "Synthetic data quality supports both 3 and 4 selection counts in similar fashion."
            ],
            "decision_rationale": "Selecting 4 stocks over 6 months balances portfolio size slightly upward while respecting the 6-month explicit constraint.",
            "limitations": [
              "Small portfolio sizes limit statistical power.",
              "Synthetic returns may not perfectly replicate volatility effects.",
              "No adjustment for factor exposures possible."
            ],
            "parameter_basis": "agent_design_choice",
            "adaptation_rationale": null
          },
          "valid": false,
          "errors": [
            "Candidate violates the explicit selection_count constraint.",
            "Evidence claim 1 (french-variance-methodology): the claim lacks minimal lexical support in its cited excerpt; cite an excerpt supporting the stated claim or remove the unsupported claim.",
            "Evidence claim 2 (baker-2010-benchmarks): the excerpt is not an exact substring of the retrieved summary.",
            "Executable total-volatility research needs a supported claim from a direct retrieved total-volatility source."
          ],
          "score": 8,
          "score_breakdown": {
            "grounding": 1,
            "methodological_suitability": 2,
            "feasibility": 3,
            "question_fit": 2
          }
        }
      ],
      "retained": [
        "C1",
        "C2"
      ]
    }
  ],
  "feedback": [],
  "selected_candidate_id": "C1",
  "selected_candidate": {
    "id": "C1",
    "parent_id": null,
    "research_claim": "Test whether portfolios selecting the 3 lowest total-volatility stocks over a 6-month lookback have higher subsequent risk-adjusted returns than portfolios with higher-volatility selections, using synthetic monthly returns.",
    "signal": "total_volatility",
    "lookback_months": 6,
    "selection_count": 3,
    "evidence_claims": [
      {
        "claim": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks, motivating comparisons of total volatility.",
        "source_id": "baker-2010-benchmarks",
        "summary_excerpt": "The paper examines comparatively weak historical returns among high-volatility and high-beta stocks. It proposes that investor demand for risk and benchmark-relative mandates can limit corrective arbitrage. This motivates comparing total-volatility and beta definitions, while leaving open whether any particular implementation will reproduce the reported pattern."
      },
      {
        "claim": "Methodology forms variance-ranked portfolios each month using lagged daily returns and a variance window of 60 days; MVP uses synthetic monthly returns and a 12-month window as a different educational specification.",
        "source_id": "french-variance-methodology",
        "summary_excerpt": "This methodology forms variance-ranked portfolios each month using NYSE breakpoints and lagged daily returns. Its variance window uses 60 days, with at least 20 observations. The MVP's 12-month signal uses synthetic monthly returns and is an explicitly different educational specification. Only the methodology description is indexed; numerical portfolio returns are not included."
      },
      {
        "claim": "Research protocols recommend pre-specification of hypotheses to reduce false discoveries in financial research.",
        "source_id": "arnott-2019-protocol",
        "summary_excerpt": "The authors propose disciplined empirical research to reduce false discoveries in limited financial samples. Economic motivation and a falsifiable hypothesis should precede performance inspection. Repeatedly modifying models after seeing returns can inflate apparent success. The MVP uses this guidance for pre-outcome specification locks and a record of every candidate considered."
      }
    ],
    "assumptions": [
      "Synthetic monthly return volatility approximates true total volatility for ranking.",
      "A 6-month lookback captures recent volatility dynamics relevant for portfolio formation.",
      "Selecting the 3 lowest volatility stocks is sufficient to test the low-volatility effect in a small portfolio setting."
    ],
    "decision_rationale": "6-month lookback and 3-stock selection match explicit constraints and allow feasible low-volatility portfolio testing with the synthetic dataset.",
    "limitations": [
      "Synthetic data may not capture all real market dynamics.",
      "Small portfolio size could limit generalizability.",
      "No factor adjustment due to synthetic data limitations."
    ],
    "parameter_basis": "agent_design_choice",
    "adaptation_rationale": null
  },
  "replication_rationale": null
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
  "execution_mode": "llm",
  "provider_execution": {
    "calls_attempted": 1,
    "actual_provider_calls": 1,
    "calls": [
      {
        "provider": "openai",
        "requested_model": "gpt-4.1-mini-2025-04-14",
        "actual_model": "gpt-4.1-mini-2025-04-14",
        "response_id": "resp_070a43e066d3617b016a9f444f871487d1a5df9057836abbe1",
        "usage": {
          "input_tokens": 2629,
          "output_tokens": 1391,
          "total_tokens": 4020
        },
        "actual_provider_call": true,
        "status": "completed",
        "cost_usd": null,
        "provider_response_status": "completed",
        "incomplete_reason": null,
        "provider_error_code": null,
        "requested_max_output_tokens": 2500,
        "response_schema_hash": "166ffec853feb971a7d6db1fc86e727e4b38d92698789f45eb438e6cba05bc53"
      }
    ],
    "token_usage": {
      "input_tokens": 2629,
      "output_tokens": 1391,
      "total_tokens": 4020
    },
    "cost_usd": null,
    "live_execution_verified": true
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

Confidence: limited_to_deterministic_fixture

### Objections

- None recorded.

### Limitations

- LLM-assisted research MVP | Deterministic synthetic data | Historical research only | Not investment advice | No trade execution | Not evidence of future performance | Not evidence about real markets
- Synthetic returns are not empirical evidence about real markets or expected profits.
- A single fixture and zero-risk-free Sharpe comparison do not establish statistical significance or causality.
- The fixed universe omits delistings, changing constituents, taxes, market impact, and corporate actions.
- Data checks attest structure and recorded hashes; the Skeptic does not independently rerun the generator seed.
- The Skeptic is independently coded deterministic checking, not an independent human or language model.
- Local hash chains lack external checkpoints and cannot detect valid tail deletion or complete chain rewriting.

## Audit and memory

`audit.jsonl` records role events and gates. `research_journal.jsonl` retains locks and conclusions across runs. Both use append-only SHA-256 chains. They are local integrity checks, not externally authenticated evidence.
