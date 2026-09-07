# Investment Signal Research Agent

**Offline MVP | Deterministic synthetic data | Historical research only | Not investment advice | No trade execution | Not evidence of future performance**

Run: `run-f5689df1f9c6a23c`

Status: **completed**

Verdict: **supported_in_synthetic_fixture_only**

Human intervention required: **False**

Synthetic results describe this fixture only; they provide no evidence about real markets.

## Research direction

Explore whether lower-volatility stocks have better risk-adjusted returns

## Preregistered hypothesis

ID: `hyp-v1-c4c216edea2a7ba3`

SHA-256: `c4c216edea2a7ba3cdf0d078f34d5037f1c1316484f09e2958d607a10f75da55`

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
  "lookback_months": 12,
  "holding_months": 1,
  "selection_count": 4,
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
    "Use 12 trailing monthly simple returns known at formation; hold for the following month.",
    "Observe and rebalance at the same synthetic month-end close, assuming zero latency.",
    "Choose the four lowest-volatility assets, equally weighted; break signal ties by asset identifier.",
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
  ]
}
```

## Bounded pre-outcome search

Candidates: total volatility, beta, and idiosyncratic volatility. Ranking uses literature coverage and fixed-harness feasibility only.

```json
{
  "method": "bounded_deterministic_beam_search",
  "description": "Tree-of-Thought-style explicit candidate tree; no LLM is used.",
  "max_depth": 2,
  "beam_width": 2,
  "max_nodes": 5,
  "max_revisions": 1,
  "nodes_visited": 5,
  "outcome_access": false,
  "scoring_inputs": [
    "source_topic_coverage",
    "offline_harness_feasibility"
  ],
  "score_rule": "grounding_source_count + 4 * feasibility_score",
  "alternatives": [
    {
      "definition": "total_volatility",
      "definition_detail": "Dispersion of all stock returns, initially using lagged daily returns.",
      "required_inputs": [
        "daily_price_panel"
      ],
      "feasibility_score": 0.75,
      "feasible": false,
      "objection": "The offline harness has monthly prices; daily methodology requires a pre-lock adaptation.",
      "depth": 1,
      "source_ids": [
        "baker-2010-benchmarks",
        "french-variance-methodology"
      ],
      "grounding_score": 2,
      "score": 5.0
    },
    {
      "definition": "beta",
      "definition_detail": "Covariance with an external market return divided by market variance.",
      "required_inputs": [
        "monthly_price_panel",
        "point_in_time_market_factor"
      ],
      "feasibility_score": 0.0,
      "feasible": false,
      "objection": "An independently specified, dated market factor and beta harness are unavailable.",
      "depth": 1,
      "source_ids": [
        "baker-2010-benchmarks",
        "french-factor-methodology"
      ],
      "grounding_score": 2,
      "score": 2.0
    },
    {
      "definition": "idiosyncratic_volatility",
      "definition_detail": "Dispersion of residual returns after an explicitly specified factor regression.",
      "required_inputs": [
        "monthly_price_panel",
        "point_in_time_factor_panel",
        "factor_regression"
      ],
      "feasibility_score": 0.0,
      "feasible": false,
      "objection": "Dated factor observations and a fixed regression harness are unavailable; residual risk is not total risk.",
      "depth": 1,
      "source_ids": [
        "ang-2004-volatility",
        "french-factor-methodology"
      ],
      "grounding_score": 2,
      "score": 2.0
    }
  ],
  "trace": [
    {
      "depth": 1,
      "expanded": [
        "total_volatility",
        "beta",
        "idiosyncratic_volatility"
      ],
      "retained": [
        "total_volatility",
        "beta"
      ]
    },
    {
      "depth": 2,
      "expanded": [
        {
          "definition": "total_volatility",
          "definition_detail": "Sample standard deviation of 12 trailing monthly simple returns.",
          "required_inputs": [
            "monthly_price_panel"
          ],
          "feasibility_score": 1.0,
          "feasible": true,
          "objection": "Monthly lookback is a declared educational adaptation, not replication of daily-return papers.",
          "depth": 2,
          "source_ids": [
            "baker-2010-benchmarks",
            "french-variance-methodology"
          ],
          "grounding_score": 2,
          "score": 6.0,
          "parent": "total_volatility"
        },
        {
          "definition": "beta",
          "definition_detail": "Covariance with an external market return divided by market variance.",
          "required_inputs": [
            "monthly_price_panel",
            "point_in_time_market_factor"
          ],
          "feasibility_score": 0.0,
          "feasible": false,
          "objection": "An independently specified, dated market factor and beta harness are unavailable.",
          "depth": 2,
          "source_ids": [
            "baker-2010-benchmarks",
            "french-factor-methodology"
          ],
          "grounding_score": 2,
          "score": 2.0,
          "parent": "beta"
        }
      ],
      "retained": [
        "total_volatility",
        "beta"
      ]
    }
  ],
  "revisions": [
    {
      "definition": "total_volatility",
      "from": "lagged_daily_variance",
      "to": "trailing_sample_std_monthly_returns",
      "before_lock": true,
      "reason": "Only monthly synthetic prices and the fixed total-volatility harness are available."
    }
  ],
  "selected": "total_volatility",
  "stopping_rule": "Stop after depth 2 and one pre-lock revision; never rerank using outcomes."
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
| cumulative_return | 0.52465708 | 0.67198003 |
| annualized_return | 0.04797872 | 0.05877445 |
| annualized_volatility | 0.04881393 | 0.06956175 |
| sharpe_ratio | 0.98600843 | 0.85726910 |
| maximum_drawdown | -0.08293595 | -0.09427482 |
| average_monthly_turnover | 0.13021201 | 0.03316088 |
| total_turnover | 14.06289654 | 3.58137539 |
| total_cost_fraction | 0.01406290 | 0.00358138 |
| observation_count | 108 | 108 |

Methodology:

```json
{
  "data_kind": "deterministic_synthetic",
  "formation": "Trailing 12 sample-standard-deviation monthly returns, computed at formation close",
  "execution": "Observe and transact at the same synthetic month-end close with zero latency",
  "holding": "Next one-month simple price return; no dividends or corporate actions",
  "selection": "Four lowest-volatility assets; alphabetical asset-ID tie break",
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

## Independent skeptical review

Confidence: limited_to_deterministic_fixture

### Objections

- None recorded.

### Limitations

- Offline MVP using deterministic synthetic data; historical research only.
- Not investment advice. No trade execution. Not evidence of future performance.
- Synthetic returns are not empirical evidence about real markets or expected profits.
- A single fixture and zero-risk-free Sharpe comparison do not establish statistical significance or causality.
- The fixed universe omits delistings, changing constituents, taxes, market impact, and corporate actions.
- Data checks attest structure and recorded hashes; the Skeptic does not independently rerun the generator seed.
- The Skeptic is independently coded deterministic checking, not an independent human or language model.
- Local hash chains lack external checkpoints and cannot detect valid tail deletion or complete chain rewriting.

## Audit and memory

`audit.jsonl` records role events and gates. `research_journal.jsonl` retains locks and conclusions across runs. Both use append-only SHA-256 chains. They are local integrity checks, not externally authenticated evidence.
