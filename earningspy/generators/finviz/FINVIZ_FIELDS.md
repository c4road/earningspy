# Finviz Field Spec

> **Generated file — do not edit by hand.** Regenerate with:
> `python -m earningspy.generators.finviz.field_spec > earningspy/generators/finviz/FINVIZ_FIELDS.md`

Source of truth: `earningspy/generators/finviz/field_spec.py`. Validated by `tests/generators/test_field_spec.py`.
Primary definition source: <https://finviz.com/help/screener> (2026-07-26).
See `docs/FINVIZ_METRIC_BASES.md` for the net-income vs operating basis of the profitability ratios.

**Legend — `kind`:** `level_usd`/`level_usd_sh` = dollar amount; `level_count` = raw count; `simple_growth` = single-period % growth; `cagr` = annualized multi-year % growth; `yoy` = year-over-year % change; `surprise` = actual vs estimate %; `ratio`/`pct` = ratio/percentage; `pct_return` = point price return; `pct_from_level` = % distance from an SMA/52w level.

**`compare with`** lists fields that are equal in magnitude / directly comparable (same growth basis, same unit).

**Legend — `Src` (provenance):** `finviz` = defined on finviz.com/help/screener; `fixture` = semantic type empirically confirmed against the real mock payload in tests; `cross-ref` / `convention` = inferred, lower confidence.

| Finviz code | Field | Kind | Unit | Period | Compare with | Src | Conf | Note |
|---|---|---|---|---|---|---|---|---|
| 0 | `Ticker` | text | symbol | - | - | finviz | high |  |
| 1 | `Company` | text | name | - | - | finviz | high |  |
| 2 | `Sector` | text | category | - | - | finviz | high |  |
| 3 | `Industry` | text | category | - | - | finviz | high |  |
| 4 | `Country` | text | category | - | - | finviz | high |  |
| 5 | `Market Cap` | level_usd | USD | instant | Sales, Income, Enterprise Value | finviz | high |  |
| 6 | `P/E` | ratio | x | ttm | - | finviz | high |  |
| 7 | `Forward P/E` | ratio | x | next FY est | - | finviz | high |  |
| 8 | `PEG` | ratio | x | - | - | finviz | high | P/E / EPS growth rate |
| 9 | `P/S` | ratio | x | ttm | - | finviz | high |  |
| 10 | `P/B` | ratio | x | - | - | finviz | high |  |
| 11 | `P/C` | ratio | x | - | - | finviz | high |  |
| 12 | `P/FCF` | ratio | x | ttm | - | finviz | high |  |
| 13 | `Dividend` | pct | % | forward/indicated | - | finviz | high | Dividend YIELD % (forward/indicated), NOT dollars per share. The $/share figure is 'Dividend TTM'. |
| 14 | `Payout Ratio` | pct | % | ttm | - | finviz | high |  |
| 15 | `EPS` | level_usd_sh | USD/share | ttm | EPS next Q | finviz | high | Diluted EPS, trailing twelve months (a $ level). |
| 16 | `EPS next Q` | level_usd_sh | USD/share | next FQ est | EPS | fixture | high | Consensus $ EPS estimate for next quarter (a $ level, NOT a %). Confirmed $-formatted in the mock payload. |
| 17 | `EPS This Y` | simple_growth | % | this FY vs last FY | EPS Next Y | finviz | high | EPS GROWTH this fiscal year (a %), not a dollar estimate. |
| 18 | `EPS Next Y` | simple_growth | % | next FY vs this FY (est) | EPS This Y | finviz | high | EPS GROWTH next fiscal year (a %), not a dollar estimate. |
| 19 | `EPS Past 5Y` | cagr | %/yr | 5y annualized | EPS Next 5Y | finviz | high | Annualized (CAGR) EPS growth, past 5 FY. NOT comparable to 1y growth. |
| 20 | `EPS Next 5Y` | cagr | %/yr | ~5y annualized est | EPS Past 5Y | finviz | high | Annualized long-term EPS growth estimate (CAGR). |
| 21 | `Sales Past 5Y` | cagr | %/yr | 5y annualized | - | finviz | high | Annualized (CAGR) sales growth, past 5 FY. |
| 23 | `Sales Q/Q` | yoy | % | latest Q vs year-ago Q | Sales YoY TTM | finviz | high | MISLEADING NAME: YEAR-OVER-YEAR revenue growth (latest quarter vs same quarter last year), not sequential. |
| 22 | `Sales YoY TTM` | yoy | % | ttm vs prior ttm | Sales Q/Q | fixture | high | Revenue growth, trailing-12m vs prior trailing-12m (a %). Confirmed %-formatted in the mock payload; exact window still TTM-vs-prior-TTM by convention. |
| 78 | `EPS Q/Q` | yoy | % | latest Q vs year-ago Q | EPS YoY TTM | finviz | high | MISLEADING NAME: this is YEAR-OVER-YEAR (latest quarter vs the same quarter one year ago), not sequential quarter-over-quarter. |
| 127 | `Sales` | level_usd | USD | ttm | Market Cap, Income, Enterprise Value | finviz | high | Total revenue, trailing twelve months (a $ level). |
| 128 | `Income` | level_usd | USD | ttm | Market Cap, Sales, Enterprise Value | fixture | high | Net income, trailing twelve months (a $ level). Confirmed money-magnitude (K/M/B/T) in the mock payload. |
| 24 | `EPS Surprise` | surprise | % | last report | Revenue Surprise | fixture | high | Actual EPS vs consensus estimate, last interim report (a beat/miss %). Confirmed %-formatted in the mock payload. |
| 25 | `Revenue Surprise` | surprise | % | last report | EPS Surprise | fixture | high | Actual revenue vs consensus estimate, last report (a beat/miss %). Confirmed %-formatted in the mock payload. |
| 85 | `Outstanding` | level_count | shares | instant | - | finviz | high |  |
| 26 | `Float` | level_count | shares | instant | - | finviz | high |  |
| 27 | `Float %` | pct | % | - | - | finviz | high | Float / shares outstanding. |
| 28 | `Insider Own` | pct | % | - | - | finviz | high |  |
| 29 | `Insider Trans` | pct | % | - | - | finviz | high | Recent net insider transactions. |
| 30 | `Inst Own` | pct | % | - | - | finviz | high |  |
| 31 | `Inst Trans` | pct | % | - | - | finviz | high | Net institutional transactions. |
| 32 | `Short Float` | pct | % | - | - | finviz | high | Short interest / float. |
| 33 | `Short Ratio` | ratio | days | - | - | finviz | high | Short interest / avg daily volume. |
| 34 | `Short Interest` | level_count | shares | - | - | finviz | high |  |
| 35 | `ROA` | pct | % | ttm | ROE, ROIC | finviz | high | Net income / assets. One-off-sensitive. |
| 36 | `ROE` | pct | % | ttm | ROA, ROIC | finviz | high | Net income / equity. One-off-sensitive. |
| 37 | `ROIC` | pct | % | ttm | ROA, ROE | finviz | high | Finviz ROIC = Net Income / Invested Capital (NOT NOPAT-based!). One-off-sensitive. See FINVIZ_METRIC_BASES.md. |
| 38 | `Curr R` | ratio | x | - | - | finviz | high | Current ratio. |
| 39 | `Quick R` | ratio | x | - | - | finviz | high | Quick ratio. |
| 40 | `LTDebt/Eq` | ratio | x | - | - | finviz | high |  |
| 41 | `Debt/Eq` | ratio | x | - | - | finviz | high |  |
| 42 | `Gross M` | pct | % | ttm | Oper M, Profit M | finviz | high | (Revenue - COGS) / Revenue. Clean (operating-level). |
| 43 | `Oper M` | pct | % | ttm | Gross M, Profit M | finviz | high | Operating income / net sales. Clean. |
| 44 | `Profit M` | pct | % | ttm | Gross M, Oper M | finviz | high | Net income / revenue. One-off-sensitive. |
| 45 | `Perf Week` | pct_return | % | 1 week | Perf Month, Perf Quart, Perf Half, Perf Year, Perf YTD, Change, Return% 1Y | finviz | high |  |
| 46 | `Perf Month` | pct_return | % | 1 month | Perf Week, Perf Quart, Perf Half, Perf Year, Perf YTD, Change, Return% 1Y | finviz | high |  |
| 47 | `Perf Quart` | pct_return | % | 1 quarter | Perf Week, Perf Month, Perf Half, Perf Year, Perf YTD, Change, Return% 1Y | finviz | high |  |
| 48 | `Perf Half` | pct_return | % | 6 months | Perf Week, Perf Month, Perf Quart, Perf Year, Perf YTD, Change, Return% 1Y | finviz | high |  |
| 49 | `Perf Year` | pct_return | % | 1 year | Perf Week, Perf Month, Perf Quart, Perf Half, Perf YTD, Change, Return% 1Y | finviz | high |  |
| 50 | `Perf YTD` | pct_return | % | year to date | Perf Week, Perf Month, Perf Quart, Perf Half, Perf Year, Change, Return% 1Y | finviz | high |  |
| 51 | `Beta` | ratio | x | - | - | finviz | high |  |
| 52 | `ATR` | level_usd | USD | - | - | finviz | high | Average true range. |
| 53 | `Volatility W` | pct | % | 1 week | - | finviz | high |  |
| 54 | `Volatility M` | pct | % | 1 month | - | finviz | high |  |
| 57 | `SMA20` | pct_from_level | % | - | SMA50, SMA200 | finviz | high | % distance of price from SMA20 (not the SMA level). |
| 58 | `SMA50` | pct_from_level | % | - | SMA20, SMA200 | finviz | high | % distance of price from SMA50. |
| 59 | `SMA200` | pct_from_level | % | - | SMA20, SMA50 | finviz | high | % distance of price from SMA200. |
| 62 | `52W High` | pct_from_level | % | - | - | finviz | high | % distance below the 52-week high. |
| 63 | `52W Low` | pct_from_level | % | - | - | finviz | high | % distance above the 52-week low. |
| 64 | `RSI` | ratio | 0-100 | 14-period | - | finviz | high |  |
| 65 | `Earnings` | date | date | - | - | finviz | high | Next earnings date/time. Dropped in FINVIZ_DROP_COLUMNS. |
| 66 | `Target Price` | level_usd | USD | - | - | finviz | high | Mean analyst price target. |
| 67 | `Book/sh` | level_usd_sh | USD/share | - | - | finviz | high |  |
| 68 | `Cash/sh` | level_usd_sh | USD/share | - | - | finviz | high |  |
| 69 | `Employees` | level_count | count | - | - | finviz | high |  |
| 73 | `Index` | text | membership | - | - | finviz | high | Dropped in FINVIZ_DROP_COLUMNS. |
| 74 | `Optionable` | bool | bool | - | - | finviz | high |  |
| 76 | `Prev Close` | level_usd | USD | - | - | finviz | high |  |
| 77 | `Shortable` | bool | bool | - | - | finviz | high |  |
| 79 | `Recom` | ratio | 1-5 | - | - | finviz | high | Mean analyst recommendation (1=strong buy .. 5=strong sell). |
| 80 | `Avg Volume` | level_count | shares | - | - | finviz | high |  |
| 81 | `Rel Volume` | ratio | x | - | - | finviz | high |  |
| 82 | `Volume` | level_count | shares | - | - | finviz | high |  |
| 83 | `Price` | level_usd | USD | - | - | finviz | high |  |
| 84 | `Change` | pct_return | % | today | Perf Week, Perf Month, Perf Quart, Perf Half, Perf Year, Perf YTD, Return% 1Y | finviz | high |  |
| 120 | `Return% 1Y` | pct_return | % | 1 year | Perf Week, Perf Month, Perf Quart, Perf Half, Perf Year, Perf YTD, Change | finviz | high | Dropped in FINVIZ_DROP_COLUMNS. |
| 130 | `Dividend TTM` | level_usd_sh | USD/share | ttm | - | finviz | high |  |
| 131 | `Dividend Ex Date` | date | date | - | - | finviz | high |  |
| 132 | `EPS YoY TTM` | yoy | % | ttm vs prior ttm | EPS Q/Q | fixture | high | EPS growth, trailing-12m vs prior trailing-12m (a %). Confirmed %-formatted in the mock payload; exact window still TTM-vs-prior-TTM by convention. |
| 133 | `52W Range` | text | low-high | - | - | finviz | high | Raw range string. Dropped in FINVIZ_DROP_COLUMNS. |
| 134 | `Enterprise Value` | level_usd | USD | instant | Market Cap, Sales, Income | finviz | high |  |
| 144 | `EV/EBITDA` | ratio | x | ttm | - | finviz | high |  |
| 145 | `EV/Sales` | ratio | x | ttm | - | finviz | high |  |

**Unmapped Finviz code(s)** requested in the URL but not captured as a named column: [146] (source of the 89-codes vs 88-names offset).

