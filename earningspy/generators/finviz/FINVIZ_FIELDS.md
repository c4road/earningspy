# Finviz Field Spec

> **Generated file — do not edit by hand.** Regenerate with:
> `python -m earningspy.generators.finviz.field_spec > earningspy/generators/finviz/FINVIZ_FIELDS.md`

Source of truth: `earningspy/generators/finviz/field_spec.py`. Validated by `tests/generators/test_field_spec.py`.
Primary definition source: <https://finviz.com/help/screener> (2026-07-26).
See `docs/FINVIZ_METRIC_BASES.md` for the net-income vs operating basis of the profitability ratios.

**Legend — `kind`:** `level_usd`/`level_usd_sh` = dollar amount; `level_count` = raw count; `simple_growth` = single-period % growth; `cagr` = annualized multi-year % growth; `yoy` = year-over-year % change; `surprise` = actual vs estimate %; `ratio`/`pct` = ratio/percentage; `pct_return` = point price return; `pct_from_level` = % distance from an SMA/52w level.

**`compare with`** lists fields that are equal in magnitude / directly comparable (same growth basis, same unit).

**Legend — `Src` (provenance):** `finviz` = defined on finviz.com/help/screener; `fixture` = semantic type empirically confirmed against the real mock payload in tests; `cross-ref` / `convention` = inferred, lower confidence.

**`Description`** is the plain-language, client-facing summary of what the value tells you and how it is composed.

| Finviz code | Field | Description | Kind | Unit | Period | Compare with | Src | Conf | Note |
|---|---|---|---|---|---|---|---|---|---|
| 0 | `Ticker` | Exchange ticker symbol identifying the security. | text | symbol | - | - | finviz | high |  |
| 1 | `Company` | Legal/brand name of the company. | text | name | - | - | finviz | high |  |
| 2 | `Sector` | Broad economic sector (e.g. Technology, Healthcare) for grouping and peer comparison. | text | category | - | - | finviz | high |  |
| 3 | `Industry` | Finer-grained industry classification within the sector; used to build peer sets. | text | category | - | - | finviz | high |  |
| 4 | `Country` | Country of the company's headquarters/domicile. | text | category | - | - | finviz | high |  |
| 5 | `Market Cap` | Total equity market value of the company = share price x shares outstanding. The primary size measure. | level_usd | USD | instant | Sales, Income, Enterprise Value | finviz | high |  |
| 6 | `P/E` | Price-to-earnings: share price divided by trailing-12-month EPS. How many dollars investors pay per dollar of past earnings; a core valuation gauge. | ratio | x | ttm | - | finviz | high |  |
| 7 | `Forward P/E` | Share price divided by the consensus EPS estimate for the next fiscal year. Valuation on expected (not historical) earnings. | ratio | x | next FY est | - | finviz | high |  |
| 8 | `PEG` | P/E divided by the expected EPS growth rate. Contextualizes the P/E against growth: ~1 is often read as fairly priced for growth. | ratio | x | - | - | finviz | high | P/E / EPS growth rate |
| 9 | `P/S` | Price-to-sales: market cap divided by trailing-12-month revenue. Useful when earnings are thin or negative. | ratio | x | ttm | - | finviz | high |  |
| 10 | `P/B` | Price-to-book: share price divided by book value per share. Price relative to accounting net worth; common for financials/asset-heavy names. | ratio | x | - | - | finviz | high |  |
| 11 | `P/C` | Price-to-cash: share price divided by cash per share. How much of the price is backed by cash on hand. | ratio | x | - | - | finviz | high |  |
| 12 | `P/FCF` | Price-to-free-cash-flow: market cap divided by trailing free cash flow. Valuation against actual cash generation. | ratio | x | ttm | - | finviz | high |  |
| 13 | `Dividend` | Forward/indicated dividend YIELD: annualized dividend as a percent of the share price. Income return a buyer earns at today's price. (Dollar amount is 'Dividend TTM'.) | pct | % | forward/indicated | - | finviz | high | Dividend YIELD % (forward/indicated), NOT dollars per share. The $/share figure is 'Dividend TTM'. |
| 14 | `Payout Ratio` | Share of earnings paid out as dividends (dividends / earnings). Signals dividend sustainability and reinvestment posture. | pct | % | ttm | - | finviz | high |  |
| 15 | `EPS` | Trailing-12-month diluted earnings per share, in dollars. Company profit attributable to each share; the denominator of the P/E. | level_usd_sh | USD/share | ttm | EPS next Q | finviz | high | Diluted EPS, trailing twelve months (a $ level). |
| 16 | `EPS next Q` | Consensus analyst estimate of next quarter's EPS, in dollars. The market's near-term earnings expectation to beat or miss. | level_usd_sh | USD/share | next FQ est | EPS | fixture | high | Consensus $ EPS estimate for next quarter (a $ level, NOT a %). Confirmed $-formatted in the mock payload. |
| 17 | `EPS This Y` | Percent growth in EPS expected this fiscal year vs last fiscal year. Current-year earnings momentum. | simple_growth | % | this FY vs last FY | EPS Next Y | finviz | high | EPS GROWTH this fiscal year (a %), not a dollar estimate. |
| 18 | `EPS Next Y` | Percent growth in EPS expected next fiscal year vs this fiscal year. Forward earnings-growth expectation. | simple_growth | % | next FY vs this FY (est) | EPS This Y | finviz | high | EPS GROWTH next fiscal year (a %), not a dollar estimate. |
| 19 | `EPS Past 5Y` | Annualized (CAGR) EPS growth over the past 5 fiscal years. Long-run historical earnings-growth track record. | cagr | %/yr | 5y annualized | EPS Next 5Y | finviz | high | Annualized (CAGR) EPS growth, past 5 FY. NOT comparable to 1y growth. |
| 20 | `EPS Next 5Y` | Analysts' annualized long-term EPS growth estimate (~5 years, CAGR). Consensus view of durable growth. | cagr | %/yr | ~5y annualized est | EPS Past 5Y | finviz | high | Annualized long-term EPS growth estimate (CAGR). |
| 21 | `Sales Past 5Y` | Annualized (CAGR) revenue growth over the past 5 fiscal years. Long-run top-line growth track record. | cagr | %/yr | 5y annualized | - | finviz | high | Annualized (CAGR) sales growth, past 5 FY. |
| 23 | `Sales Q/Q` | Revenue growth of the most recent quarter vs the same quarter one year ago (year-over-year, despite the name). Latest top-line momentum. | yoy | % | latest Q vs year-ago Q | Sales YoY TTM | finviz | high | MISLEADING NAME: YEAR-OVER-YEAR revenue growth (latest quarter vs same quarter last year), not sequential. |
| 22 | `Sales YoY TTM` | Revenue growth of the trailing 12 months vs the prior trailing 12 months. Smoothed top-line growth read. | yoy | % | ttm vs prior ttm | Sales Q/Q | fixture | high | Revenue growth, trailing-12m vs prior trailing-12m (a %). Confirmed %-formatted in the mock payload; exact window still TTM-vs-prior-TTM by convention. |
| 78 | `EPS Q/Q` | EPS growth of the most recent quarter vs the SAME quarter one year ago (year-over-year, despite the name). Latest earnings acceleration/deceleration. | yoy | % | latest Q vs year-ago Q | EPS YoY TTM | finviz | high | MISLEADING NAME: this is YEAR-OVER-YEAR (latest quarter vs the same quarter one year ago), not sequential quarter-over-quarter. |
| 127 | `Sales` | Trailing-12-month total revenue, in dollars. Overall business scale on the top line. | level_usd | USD | ttm | Market Cap, Income, Enterprise Value | finviz | high | Total revenue, trailing twelve months (a $ level). |
| 128 | `Income` | Trailing-12-month net income (bottom-line profit), in dollars. Absolute profitability after all costs, interest, and taxes. | level_usd | USD | ttm | Market Cap, Sales, Enterprise Value | fixture | high | Net income, trailing twelve months (a $ level). Confirmed money-magnitude (K/M/B/T) in the mock payload. |
| 24 | `EPS Surprise` | Percent by which the last reported EPS beat (+) or missed (-) consensus. A catalyst signal around earnings. | surprise | % | last report | Revenue Surprise | fixture | high | Actual EPS vs consensus estimate, last interim report (a beat/miss %). Confirmed %-formatted in the mock payload. |
| 25 | `Revenue Surprise` | Percent by which the last reported revenue beat (+) or missed (-) consensus. Demand-side catalyst signal. | surprise | % | last report | EPS Surprise | fixture | high | Actual revenue vs consensus estimate, last report (a beat/miss %). Confirmed %-formatted in the mock payload. |
| 85 | `Outstanding` | Total shares issued and held by all holders. Basis for market cap and per-share figures. | level_count | shares | instant | - | finviz | high |  |
| 26 | `Float` | Shares actually available for public trading (excludes locked-up insider/strategic holdings). Drives liquidity and volatility. | level_count | shares | instant | - | finviz | high |  |
| 27 | `Float %` | Float as a percent of shares outstanding. How much of the company freely trades. | pct | % | - | - | finviz | high | Float / shares outstanding. |
| 28 | `Insider Own` | Percent of shares held by company insiders. Higher levels can signal management alignment. | pct | % | - | - | finviz | high |  |
| 29 | `Insider Trans` | Net recent change in insider holdings (percent). Direction of insider buying/selling. | pct | % | - | - | finviz | high | Recent net insider transactions. |
| 30 | `Inst Own` | Percent of shares held by institutions (funds, banks). Indicates professional sponsorship. | pct | % | - | - | finviz | high |  |
| 31 | `Inst Trans` | Net recent change in institutional holdings (percent). Direction of institutional accumulation/distribution. | pct | % | - | - | finviz | high | Net institutional transactions. |
| 32 | `Short Float` | Shares sold short as a percent of float. Gauges bearish positioning and squeeze potential. | pct | % | - | - | finviz | high | Short interest / float. |
| 33 | `Short Ratio` | Days-to-cover: short interest divided by average daily volume. How long shorts would take to buy back. | ratio | days | - | - | finviz | high | Short interest / avg daily volume. |
| 34 | `Short Interest` | Total number of shares currently sold short. Absolute bearish positioning. | level_count | shares | - | - | finviz | high |  |
| 35 | `ROA` | Return on assets: net income as a percent of total assets. How efficiently assets generate profit. (Net-income based - sensitive to one-off items.) | pct | % | ttm | ROE, ROIC | finviz | high | Net income / assets. One-off-sensitive. |
| 36 | `ROE` | Return on equity: net income as a percent of shareholder equity. Profit generated on shareholders' capital. (Net-income based - one-off sensitive.) | pct | % | ttm | ROA, ROIC | finviz | high | Net income / equity. One-off-sensitive. |
| 37 | `ROIC` | Finviz return on invested capital = net income / invested capital. Return on all capital employed. NOTE: net-income based here (not the textbook NOPAT version), so one-off sensitive. | pct | % | ttm | ROA, ROE | finviz | high | Finviz ROIC = Net Income / Invested Capital (NOT NOPAT-based!). One-off-sensitive. See FINVIZ_METRIC_BASES.md. |
| 38 | `Curr R` | Current ratio: current assets / current liabilities. Short-term liquidity - ability to cover near-term obligations. | ratio | x | - | - | finviz | high | Current ratio. |
| 39 | `Quick R` | Quick ratio: liquid current assets (ex-inventory) / current liabilities. A stricter liquidity test. | ratio | x | - | - | finviz | high | Quick ratio. |
| 40 | `LTDebt/Eq` | Long-term debt relative to shareholder equity. Structural leverage from long-dated borrowing. | ratio | x | - | - | finviz | high |  |
| 41 | `Debt/Eq` | Total debt relative to shareholder equity. Overall financial leverage and balance-sheet risk. | ratio | x | - | - | finviz | high |  |
| 42 | `Gross M` | Gross margin: (revenue - cost of goods sold) / revenue. Core product profitability before operating costs. | pct | % | ttm | Oper M, Profit M | finviz | high | (Revenue - COGS) / Revenue. Clean (operating-level). |
| 43 | `Oper M` | Operating margin: operating income / revenue. Profitability from core operations, before interest, taxes, and one-offs. | pct | % | ttm | Gross M, Profit M | finviz | high | Operating income / net sales. Clean. |
| 44 | `Profit M` | Net profit margin: net income / revenue. Cents of bottom-line profit per dollar of sales. (One-off sensitive.) | pct | % | ttm | Gross M, Oper M | finviz | high | Net income / revenue. One-off-sensitive. |
| 45 | `Perf Week` | Total price return over the past week. Very short-term momentum. | pct_return | % | 1 week | Perf Month, Perf Quart, Perf Half, Perf Year, Perf YTD, Change, Return% 1Y | finviz | high |  |
| 46 | `Perf Month` | Total price return over the past month. Short-term momentum. | pct_return | % | 1 month | Perf Week, Perf Quart, Perf Half, Perf Year, Perf YTD, Change, Return% 1Y | finviz | high |  |
| 47 | `Perf Quart` | Total price return over the past quarter. Intermediate momentum. | pct_return | % | 1 quarter | Perf Week, Perf Month, Perf Half, Perf Year, Perf YTD, Change, Return% 1Y | finviz | high |  |
| 48 | `Perf Half` | Total price return over the past six months. Medium-term momentum. | pct_return | % | 6 months | Perf Week, Perf Month, Perf Quart, Perf Year, Perf YTD, Change, Return% 1Y | finviz | high |  |
| 49 | `Perf Year` | Total price return over the past year. Longer-term momentum / trend. | pct_return | % | 1 year | Perf Week, Perf Month, Perf Quart, Perf Half, Perf YTD, Change, Return% 1Y | finviz | high |  |
| 50 | `Perf YTD` | Total price return since the start of the calendar year. | pct_return | % | year to date | Perf Week, Perf Month, Perf Quart, Perf Half, Perf Year, Change, Return% 1Y | finviz | high |  |
| 51 | `Beta` | Sensitivity of the stock's returns to the overall market (1 = moves with the market). Systematic-risk measure. | ratio | x | - | - | finviz | high |  |
| 52 | `ATR` | Average True Range: typical daily price movement in dollars. Absolute volatility for sizing/stops. | level_usd | USD | - | - | finviz | high | Average true range. |
| 53 | `Volatility W` | Average daily price volatility over the past week (percent). Recent choppiness. | pct | % | 1 week | - | finviz | high |  |
| 54 | `Volatility M` | Average daily price volatility over the past month (percent). Recent risk level. | pct | % | 1 month | - | finviz | high |  |
| 57 | `SMA20` | Percent distance of the current price from its 20-day simple moving average. Short-term trend position. | pct_from_level | % | - | SMA50, SMA200 | finviz | high | % distance of price from SMA20 (not the SMA level). |
| 58 | `SMA50` | Percent distance of the current price from its 50-day simple moving average. Medium-term trend position. | pct_from_level | % | - | SMA20, SMA200 | finviz | high | % distance of price from SMA50. |
| 59 | `SMA200` | Percent distance of the current price from its 200-day simple moving average. Long-term trend position. | pct_from_level | % | - | SMA20, SMA50 | finviz | high | % distance of price from SMA200. |
| 62 | `52W High` | Percent below the highest price of the last 52 weeks. Proximity to yearly highs (breakout context). | pct_from_level | % | - | - | finviz | high | % distance below the 52-week high. |
| 63 | `52W Low` | Percent above the lowest price of the last 52 weeks. Proximity to yearly lows (support/oversold context). | pct_from_level | % | - | - | finviz | high | % distance above the 52-week low. |
| 64 | `RSI` | Relative Strength Index (14-day, 0-100). Momentum oscillator; >70 often overbought, <30 oversold. | ratio | 0-100 | 14-period | - | finviz | high |  |
| 65 | `Earnings` | Date (and BMO/AMC timing) of the next scheduled earnings report. Key event marker. | date | date | - | - | finviz | high | Next earnings date/time. Dropped in FINVIZ_DROP_COLUMNS. |
| 66 | `Target Price` | Mean analyst 12-month price target. Consensus expected fair value. | level_usd | USD | - | - | finviz | high | Mean analyst price target. |
| 67 | `Book/sh` | Book (accounting net-worth) value per share, in dollars. | level_usd_sh | USD/share | - | - | finviz | high |  |
| 68 | `Cash/sh` | Cash and equivalents per share, in dollars. Downside cushion / dry powder per share. | level_usd_sh | USD/share | - | - | finviz | high |  |
| 69 | `Employees` | Reported full-time headcount. A rough operating-scale proxy. | level_count | count | - | - | finviz | high |  |
| 73 | `Index` | Membership in major indices (e.g. S&P 500). Signals inclusion-driven demand and profile. | text | membership | - | - | finviz | high | Dropped in FINVIZ_DROP_COLUMNS. |
| 74 | `Optionable` | Whether listed options trade on the stock (hedging/leverage availability). | bool | bool | - | - | finviz | high |  |
| 76 | `Prev Close` | Previous trading session's closing price, in dollars. | level_usd | USD | - | - | finviz | high |  |
| 77 | `Shortable` | Whether the stock can be sold short. | bool | bool | - | - | finviz | high |  |
| 79 | `Recom` | Mean analyst recommendation on a 1-5 scale (1 = strong buy, 5 = strong sell). Consensus rating. | ratio | 1-5 | - | - | finviz | high | Mean analyst recommendation (1=strong buy .. 5=strong sell). |
| 80 | `Avg Volume` | Average daily share volume. Liquidity measure for position sizing. | level_count | shares | - | - | finviz | high |  |
| 81 | `Rel Volume` | Today's volume relative to its average. Spots unusual activity / news-driven interest. | ratio | x | - | - | finviz | high |  |
| 82 | `Volume` | Shares traded in the current/most recent session. | level_count | shares | - | - | finviz | high |  |
| 83 | `Price` | Current (or latest) share price, in dollars. | level_usd | USD | - | - | finviz | high |  |
| 84 | `Change` | Percent price change on the day. | pct_return | % | today | Perf Week, Perf Month, Perf Quart, Perf Half, Perf Year, Perf YTD, Return% 1Y | finviz | high |  |
| 120 | `Return% 1Y` | Total return over the trailing one year (price appreciation). | pct_return | % | 1 year | Perf Week, Perf Month, Perf Quart, Perf Half, Perf Year, Perf YTD, Change | finviz | high | Dropped in FINVIZ_DROP_COLUMNS. |
| 130 | `Dividend TTM` | Trailing-12-month dividend paid per share, in dollars. The actual cash dividend amount. | level_usd_sh | USD/share | ttm | - | finviz | high |  |
| 131 | `Dividend Ex Date` | Ex-dividend date: buy before this date to receive the next dividend. | date | date | - | - | finviz | high |  |
| 132 | `EPS YoY TTM` | EPS growth of the trailing 12 months vs the prior trailing 12 months. A smoothed, seasonality-free earnings-growth read. | yoy | % | ttm vs prior ttm | EPS Q/Q | fixture | high | EPS growth, trailing-12m vs prior trailing-12m (a %). Confirmed %-formatted in the mock payload; exact window still TTM-vs-prior-TTM by convention. |
| 133 | `52W Range` | The 52-week low-to-high price range as a raw string. Context for where price sits in its yearly band. | text | low-high | - | - | finviz | high | Raw range string. Dropped in FINVIZ_DROP_COLUMNS. |
| 134 | `Enterprise Value` | Total takeover value = market cap + debt - cash. Capital-structure-neutral size measure used in EV multiples. | level_usd | USD | instant | Market Cap, Sales, Income | finviz | high |  |
| 144 | `EV/EBITDA` | Enterprise value divided by EBITDA. Capital-structure-neutral valuation multiple; common for cross-company comparison. | ratio | x | ttm | - | finviz | high |  |
| 145 | `EV/Sales` | Enterprise value divided by revenue. EV-based valuation useful when margins/earnings are not comparable. | ratio | x | ttm | - | finviz | high |  |

**Unmapped Finviz code(s)** requested in the URL but not captured as a named column: [146] (source of the 89-codes vs 88-names offset).

