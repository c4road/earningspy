"""
Finviz field specification — the single source of truth for what each fetched
Finviz column means.

Every field we request from the Finviz screener custom-table export is described
here with:

    - finviz_code : the numeric column id used in the `&c=...` URL parameter
                    (``CUSTOM_TABLE_FIELDS_ON_URL`` in ``constants.py``). ``None``
                    for post-generated fields that do not come from Finviz.
    - kind        : the semantic type (see ``Kind``) — crucially distinguishes a
                    dollar/level value from a simple growth %, a CAGR, a YoY %,
                    or a surprise %.
    - unit        : human-readable unit.
    - period      : the time basis (ttm, next FY, 5y annualized, ...).
    - compare_group : fields sharing a ``compare_group`` are equal in magnitude /
                    directly comparable to each other. ``None`` = not meaningfully
                    comparable to another fetched field.
    - source      : provenance of the definition — 'finviz' (from finviz.com/help/
                    screener), 'fixture' (semantic type empirically confirmed
                    against the real mock payload in tests/), 'cross-ref', or
                    'convention' (inferred, still to verify).
    - confidence  : 'high' | 'med' | 'verify'.
    - note        : short clarification, especially where the field name is
                    misleading (e.g. "Q/Q" fields are actually YoY).

The human-readable table in ``FINVIZ_FIELDS.md`` is generated from this module
(``python -m earningspy.generators.finviz.field_spec``), and
``tests/generators/test_field_spec.py`` validates this spec against the actual
fetch configuration in ``constants.py``.

Primary source: https://finviz.com/help/screener (verified 2026-07-26).
See also ``docs/FINVIZ_METRIC_BASES.md`` for the net-income vs operating basis of
the profitability ratios.
"""
from dataclasses import dataclass, field
from typing import Optional


class Kind:
    """Semantic type of a field value."""
    LEVEL_USD = "level_usd"          # dollar amount (price, market cap, sales $)
    LEVEL_USD_SHARE = "level_usd_sh"  # dollar amount per share
    LEVEL_COUNT = "level_count"       # a raw count (shares, employees)
    SIMPLE_GROWTH = "simple_growth"   # single-period % growth (one year vs next)
    CAGR = "cagr"                     # annualized % growth over a multi-year window
    YOY = "yoy"                       # year-over-year % change
    SURPRISE = "surprise"             # actual vs consensus estimate, %
    RATIO = "ratio"                   # a unitless ratio (P/E, Debt/Eq, Beta)
    PCT = "pct"                       # a percentage that is neither growth nor yoy
    PCT_RETURN = "pct_return"         # a point price return over a window
    PCT_FROM_LEVEL = "pct_from_level"  # % distance of price from an SMA / 52w level
    DATE = "date"
    BOOL = "bool"
    TEXT = "text"


class Cadence:
    """How often a field's value changes / is refreshed. This is about the
    *driver* of change, which determines whether a value is 'live' or 'frozen'
    between events.
    """
    # Recomputed every trading session because it contains live market price
    # (or is a pure market/technical value). Effectively daily.
    MARKET_DAILY = "market_daily"
    # A ratio whose fundamental input is frozen to the last report BUT whose
    # value still moves every day because PRICE is in the numerator/denominator
    # (e.g. P/E, P/S, dividend yield, EV multiples). Drifts daily; "resets" at
    # earnings when the fundamental updates.
    PRICE_OVER_FUNDAMENTAL = "price_over_fundamental"
    # Frozen between quarterly/annual financial reports. Only changes when the
    # company files new financials (10-Q/10-K) — the classic "frozen at earnings".
    REPORT_FROZEN = "report_frozen"
    # Analyst-driven: revised by analysts on no fixed schedule (any day), tends
    # to cluster around earnings but is NOT frozen to it. Estimates/targets/ratings.
    ESTIMATE_DRIVEN = "estimate_driven"
    # Regulatory filing cadence, NOT earnings: institutional 13F (quarterly,
    # ~45-day lag), insider Form 4 (event-driven, ~2-day lag), short interest
    # (bi-monthly, ~7-business-day lag).
    FILING_PERIODIC = "filing_periodic"
    # Essentially static (identifiers, sector) — changes rarely, if ever.
    STATIC = "static"


class Serving:
    """Operational serving decision for the pre-earnings snapshot model.

    Context: the snapshot is scraped ONCE per stock, 1-5 days before that stock's
    earnings, and stored. A client request may arrive later. The question each
    field must answer is: *can I serve the stored value, or must I re-fetch?*
    over that ~1-5 day (up to weekly) staleness window.
    """
    # Value is stable over a 1-5 day window (frozen fundamentals, multi-week
    # filing cadences, static identifiers). Serve the stored snapshot directly.
    FROM_SNAPSHOT = "serve_from_snapshot"
    # The fundamental part is fine from the snapshot, but the value embeds live
    # PRICE and is therefore stale within days. Serve stored, but recompute the
    # price component (or re-fetch) before presenting it as current.
    STALE_RECOMPUTE = "serve_stale_recompute"
    # Moves materially day-to-day (pure market/technical). The stored snapshot is
    # noise by the time it is served — fetch on demand.
    ON_DEMAND = "fetch_on_demand"


# Cadence -> default serving decision. The serving column is DERIVED from cadence
# so the two never contradict each other.
_CADENCE_TO_SERVING = {
    Cadence.REPORT_FROZEN: Serving.FROM_SNAPSHOT,
    Cadence.FILING_PERIODIC: Serving.FROM_SNAPSHOT,   # multi-week cadence >> 5d lag
    Cadence.STATIC: Serving.FROM_SNAPSHOT,
    Cadence.ESTIMATE_DRIVEN: Serving.FROM_SNAPSHOT,   # revised ad hoc, no price to recompute
    Cadence.PRICE_OVER_FUNDAMENTAL: Serving.STALE_RECOMPUTE,
    Cadence.MARKET_DAILY: Serving.ON_DEMAND,
}


def serving_for(cadence):
    """Derive the serving decision from a cadence label."""
    return _CADENCE_TO_SERVING.get(cadence)


@dataclass(frozen=True)
class FieldSpec:
    name: str                         # our internal column name (matches constants.py)
    finviz_code: Optional[int]        # numeric &c= id, or None for post-generated
    kind: str
    unit: str
    period: str = ""
    compare_group: Optional[str] = None
    source: str = "finviz"
    confidence: str = "high"
    note: str = ""                    # terse engineering caveat (misleading names, etc.)

    @property
    def description(self):
        """Plain-language, client-facing description: what the value tells you and
        how it is composed. Sourced from DESCRIPTIONS below."""
        return DESCRIPTIONS.get(self.name, "")

    @property
    def cadence(self):
        """Update-frequency class (see ``Cadence``). Sourced from CADENCE below."""
        return CADENCE.get(self.name, (None, None))[0]

    @property
    def cadence_confidence(self):
        """Confidence in the cadence classification: 'high' | 'med'. Higher bar is
        applied to the REPORT_FROZEN set per the catalog owner's request."""
        return CADENCE.get(self.name, (None, None))[1]

    @property
    def is_frozen(self):
        """True if the value is frozen between financial reports (the classic
        'frozen at earnings' set)."""
        return self.cadence == Cadence.REPORT_FROZEN

    @property
    def serving(self):
        """Operational serving decision (see ``Serving``), derived from cadence:
        can the 1-5 day-old pre-earnings snapshot be served, or must the field be
        re-fetched / price-recomputed on demand?"""
        return serving_for(self.cadence)


# ---------------------------------------------------------------------------
# Comparability groups (fields equal in magnitude / directly comparable)
# ---------------------------------------------------------------------------
# eps_growth_1y : single-year EPS growth (This Y vs Next Y are the same magnitude scale)
# eps_growth_5y : annualized (CAGR) EPS growth — NOT comparable to 1y growth
# eps_yoy       : year-over-year EPS growth (Q/Q [actually YoY] vs YoY TTM)
# eps_level     : dollar EPS values (ttm actual vs next-Q estimate)
# sales_growth_5y, sales_yoy, money_level, margins, returns_pct, ...

# ---------------------------------------------------------------------------
# Client-facing descriptions: for each field, what it tells you and how it is
# composed. Kept in a name-keyed map so the FIELD_SPECS list stays compact; the
# test suite asserts every fetched field has a non-empty description here.
# ---------------------------------------------------------------------------
DESCRIPTIONS = {
    # --- identifiers ---
    "Ticker": "Exchange ticker symbol identifying the security.",
    "Company": "Legal/brand name of the company.",
    "Sector": "Broad economic sector (e.g. Technology, Healthcare) for grouping and peer comparison.",
    "Industry": "Finer-grained industry classification within the sector; used to build peer sets.",
    "Country": "Country of the company's headquarters/domicile.",

    # --- valuation ---
    "Market Cap": "Total equity market value of the company = share price x shares outstanding. The primary size measure.",
    "P/E": "Price-to-earnings: share price divided by trailing-12-month EPS. How many dollars investors pay per dollar of past earnings; a core valuation gauge.",
    "Forward P/E": "Share price divided by the consensus EPS estimate for the next fiscal year. Valuation on expected (not historical) earnings.",
    "PEG": "P/E divided by the expected EPS growth rate. Contextualizes the P/E against growth: ~1 is often read as fairly priced for growth.",
    "P/S": "Price-to-sales: market cap divided by trailing-12-month revenue. Useful when earnings are thin or negative.",
    "P/B": "Price-to-book: share price divided by book value per share. Price relative to accounting net worth; common for financials/asset-heavy names.",
    "P/C": "Price-to-cash: share price divided by cash per share. How much of the price is backed by cash on hand.",
    "P/FCF": "Price-to-free-cash-flow: market cap divided by trailing free cash flow. Valuation against actual cash generation.",

    # --- dividends ---
    "Dividend": "Forward/indicated dividend YIELD: annualized dividend as a percent of the share price. Income return a buyer earns at today's price. (Dollar amount is 'Dividend TTM'.)",
    "Payout Ratio": "Share of earnings paid out as dividends (dividends / earnings). Signals dividend sustainability and reinvestment posture.",

    # --- EPS family ---
    "EPS": "Trailing-12-month diluted earnings per share, in dollars. Company profit attributable to each share; the denominator of the P/E.",
    "EPS next Q": "Consensus analyst estimate of next quarter's EPS, in dollars. The market's near-term earnings expectation to beat or miss.",
    "EPS This Y": "Percent growth in EPS expected this fiscal year vs last fiscal year. Current-year earnings momentum.",
    "EPS Next Y": "Percent growth in EPS expected next fiscal year vs this fiscal year. Forward earnings-growth expectation.",
    "EPS Past 5Y": "Annualized (CAGR) EPS growth over the past 5 fiscal years. Long-run historical earnings-growth track record.",
    "EPS Next 5Y": "Analysts' annualized long-term EPS growth estimate (~5 years, CAGR). Consensus view of durable growth.",
    "EPS Q/Q": "EPS growth of the most recent quarter vs the SAME quarter one year ago (year-over-year, despite the name). Latest earnings acceleration/deceleration.",
    "EPS YoY TTM": "EPS growth of the trailing 12 months vs the prior trailing 12 months. A smoothed, seasonality-free earnings-growth read.",
    "EPS Surprise": "Percent by which the last reported EPS beat (+) or missed (-) consensus. A catalyst signal around earnings.",

    # --- sales / revenue ---
    "Sales Past 5Y": "Annualized (CAGR) revenue growth over the past 5 fiscal years. Long-run top-line growth track record.",
    "Sales Q/Q": "Revenue growth of the most recent quarter vs the same quarter one year ago (year-over-year, despite the name). Latest top-line momentum.",
    "Sales YoY TTM": "Revenue growth of the trailing 12 months vs the prior trailing 12 months. Smoothed top-line growth read.",
    "Sales": "Trailing-12-month total revenue, in dollars. Overall business scale on the top line.",
    "Income": "Trailing-12-month net income (bottom-line profit), in dollars. Absolute profitability after all costs, interest, and taxes.",
    "Revenue Surprise": "Percent by which the last reported revenue beat (+) or missed (-) consensus. Demand-side catalyst signal.",

    # --- shares / ownership ---
    "Outstanding": "Total shares issued and held by all holders. Basis for market cap and per-share figures.",
    "Float": "Shares actually available for public trading (excludes locked-up insider/strategic holdings). Drives liquidity and volatility.",
    "Float %": "Float as a percent of shares outstanding. How much of the company freely trades.",
    "Insider Own": "Percent of shares held by company insiders. Higher levels can signal management alignment.",
    "Insider Trans": "Net recent change in insider holdings (percent). Direction of insider buying/selling.",
    "Inst Own": "Percent of shares held by institutions (funds, banks). Indicates professional sponsorship.",
    "Inst Trans": "Net recent change in institutional holdings (percent). Direction of institutional accumulation/distribution.",
    "Short Float": "Shares sold short as a percent of float. Gauges bearish positioning and squeeze potential.",
    "Short Ratio": "Days-to-cover: short interest divided by average daily volume. How long shorts would take to buy back.",
    "Short Interest": "Total number of shares currently sold short. Absolute bearish positioning.",

    # --- profitability & returns ---
    "ROA": "Return on assets: net income as a percent of total assets. How efficiently assets generate profit. (Net-income based - sensitive to one-off items.)",
    "ROE": "Return on equity: net income as a percent of shareholder equity. Profit generated on shareholders' capital. (Net-income based - one-off sensitive.)",
    "ROIC": "Finviz return on invested capital = net income / invested capital. Return on all capital employed. NOTE: net-income based here (not the textbook NOPAT version), so one-off sensitive.",
    "Curr R": "Current ratio: current assets / current liabilities. Short-term liquidity - ability to cover near-term obligations.",
    "Quick R": "Quick ratio: liquid current assets (ex-inventory) / current liabilities. A stricter liquidity test.",
    "LTDebt/Eq": "Long-term debt relative to shareholder equity. Structural leverage from long-dated borrowing.",
    "Debt/Eq": "Total debt relative to shareholder equity. Overall financial leverage and balance-sheet risk.",
    "Gross M": "Gross margin: (revenue - cost of goods sold) / revenue. Core product profitability before operating costs.",
    "Oper M": "Operating margin: operating income / revenue. Profitability from core operations, before interest, taxes, and one-offs.",
    "Profit M": "Net profit margin: net income / revenue. Cents of bottom-line profit per dollar of sales. (One-off sensitive.)",

    # --- performance ---
    "Perf Week": "Total price return over the past week. Very short-term momentum.",
    "Perf Month": "Total price return over the past month. Short-term momentum.",
    "Perf Quart": "Total price return over the past quarter. Intermediate momentum.",
    "Perf Half": "Total price return over the past six months. Medium-term momentum.",
    "Perf Year": "Total price return over the past year. Longer-term momentum / trend.",
    "Perf YTD": "Total price return since the start of the calendar year.",

    # --- risk / technical ---
    "Beta": "Sensitivity of the stock's returns to the overall market (1 = moves with the market). Systematic-risk measure.",
    "ATR": "Average True Range: typical daily price movement in dollars. Absolute volatility for sizing/stops.",
    "Volatility W": "Average daily price volatility over the past week (percent). Recent choppiness.",
    "Volatility M": "Average daily price volatility over the past month (percent). Recent risk level.",
    "SMA20": "Percent distance of the current price from its 20-day simple moving average. Short-term trend position.",
    "SMA50": "Percent distance of the current price from its 50-day simple moving average. Medium-term trend position.",
    "SMA200": "Percent distance of the current price from its 200-day simple moving average. Long-term trend position.",
    "52W High": "Percent below the highest price of the last 52 weeks. Proximity to yearly highs (breakout context).",
    "52W Low": "Percent above the lowest price of the last 52 weeks. Proximity to yearly lows (support/oversold context).",
    "RSI": "Relative Strength Index (14-day, 0-100). Momentum oscillator; >70 often overbought, <30 oversold.",

    # --- misc / identifiers ---
    "Earnings": "Date (and BMO/AMC timing) of the next scheduled earnings report. Key event marker.",
    "Target Price": "Mean analyst 12-month price target. Consensus expected fair value.",
    "Book/sh": "Book (accounting net-worth) value per share, in dollars.",
    "Cash/sh": "Cash and equivalents per share, in dollars. Downside cushion / dry powder per share.",
    "Employees": "Reported full-time headcount. A rough operating-scale proxy.",
    "Index": "Membership in major indices (e.g. S&P 500). Signals inclusion-driven demand and profile.",
    "Optionable": "Whether listed options trade on the stock (hedging/leverage availability).",
    "Prev Close": "Previous trading session's closing price, in dollars.",
    "Shortable": "Whether the stock can be sold short.",
    "Recom": "Mean analyst recommendation on a 1-5 scale (1 = strong buy, 5 = strong sell). Consensus rating.",
    "Avg Volume": "Average daily share volume. Liquidity measure for position sizing.",
    "Rel Volume": "Today's volume relative to its average. Spots unusual activity / news-driven interest.",
    "Volume": "Shares traded in the current/most recent session.",
    "Price": "Current (or latest) share price, in dollars.",
    "Change": "Percent price change on the day.",
    "Return% 1Y": "Total return over the trailing one year (price appreciation).",
    "Dividend TTM": "Trailing-12-month dividend paid per share, in dollars. The actual cash dividend amount.",
    "Dividend Ex Date": "Ex-dividend date: buy before this date to receive the next dividend.",
    "52W Range": "The 52-week low-to-high price range as a raw string. Context for where price sits in its yearly band.",
    "Enterprise Value": "Total takeover value = market cap + debt - cash. Capital-structure-neutral size measure used in EV multiples.",
    "EV/EBITDA": "Enterprise value divided by EBITDA. Capital-structure-neutral valuation multiple; common for cross-company comparison.",
    "EV/Sales": "Enterprise value divided by revenue. EV-based valuation useful when margins/earnings are not comparable.",
}


# ---------------------------------------------------------------------------
# Update cadence: (Cadence, confidence) per field. See the Cadence class.
#
# How this was determined (Finviz does not document per-field refresh rates):
#   - MARKET_DAILY / PRICE_OVER_FUNDAMENTAL: deduced from the formula — anything
#     containing live price necessarily moves every session. HIGH confidence.
#   - REPORT_FROZEN: values sourced purely from filed financial statements; they
#     cannot change until the next 10-Q/10-K. HIGH confidence (the set you want
#     to rely on).
#   - ESTIMATE_DRIVEN: analyst estimates/targets/ratings are revised ad hoc; not
#     frozen to earnings, not strictly daily. MED confidence on exact timing.
#   - FILING_PERIODIC: cross-checked against the actual regulatory schedules —
#     13F quarterly / ~45-day lag, Form 4 ~2 business days, short interest
#     bi-monthly / ~7 business-day lag (FINRA). HIGH on the mechanism, MED on the
#     exact day Finviz ingests it.
#   - STATIC: identifiers/classification. HIGH.
#
# Sources for the periodic ones: FINRA short-interest reporting (twice monthly,
# disseminated 7 business days after settlement); SEC Form 13F (quarterly, 45-day
# deadline); SEC Form 4 (within 2 business days of the transaction).
# ---------------------------------------------------------------------------
CADENCE = {
    # identifiers / classification — static
    "Ticker": (Cadence.STATIC, "high"),
    "Company": (Cadence.STATIC, "high"),
    "Sector": (Cadence.STATIC, "high"),
    "Industry": (Cadence.STATIC, "high"),
    "Country": (Cadence.STATIC, "high"),

    # valuation ratios that contain PRICE -> drift every day, reset at earnings
    "Market Cap": (Cadence.MARKET_DAILY, "high"),   # price x shares
    "P/E": (Cadence.PRICE_OVER_FUNDAMENTAL, "high"),
    "Forward P/E": (Cadence.PRICE_OVER_FUNDAMENTAL, "high"),  # price / forward EPS est
    "PEG": (Cadence.PRICE_OVER_FUNDAMENTAL, "med"),  # P/E (price) over an estimate
    "P/S": (Cadence.PRICE_OVER_FUNDAMENTAL, "high"),
    "P/B": (Cadence.PRICE_OVER_FUNDAMENTAL, "high"),
    "P/C": (Cadence.PRICE_OVER_FUNDAMENTAL, "high"),
    "P/FCF": (Cadence.PRICE_OVER_FUNDAMENTAL, "high"),
    "Enterprise Value": (Cadence.MARKET_DAILY, "high"),   # market cap + debt - cash
    "EV/EBITDA": (Cadence.PRICE_OVER_FUNDAMENTAL, "high"),
    "EV/Sales": (Cadence.PRICE_OVER_FUNDAMENTAL, "high"),
    "Dividend": (Cadence.PRICE_OVER_FUNDAMENTAL, "high"),  # yield = payout / price

    # dividends
    "Payout Ratio": (Cadence.REPORT_FROZEN, "high"),      # dividends / earnings (filed)
    "Dividend TTM": (Cadence.REPORT_FROZEN, "med"),       # trailing paid $, changes on declaration
    "Dividend Ex Date": (Cadence.FILING_PERIODIC, "med"),  # set by dividend declarations

    # EPS actuals & fundamentals — FROZEN at earnings
    "EPS": (Cadence.REPORT_FROZEN, "high"),
    "EPS Past 5Y": (Cadence.REPORT_FROZEN, "high"),
    "EPS Q/Q": (Cadence.REPORT_FROZEN, "high"),
    "EPS YoY TTM": (Cadence.REPORT_FROZEN, "high"),
    "EPS Surprise": (Cadence.REPORT_FROZEN, "high"),      # fixed once the report lands
    "Sales Past 5Y": (Cadence.REPORT_FROZEN, "high"),
    "Sales Q/Q": (Cadence.REPORT_FROZEN, "high"),
    "Sales YoY TTM": (Cadence.REPORT_FROZEN, "high"),
    "Sales": (Cadence.REPORT_FROZEN, "high"),
    "Income": (Cadence.REPORT_FROZEN, "high"),
    "Revenue Surprise": (Cadence.REPORT_FROZEN, "high"),

    # EPS ESTIMATES / growth-vs-estimates — analyst driven, not frozen to earnings
    "EPS next Q": (Cadence.ESTIMATE_DRIVEN, "high"),
    "EPS This Y": (Cadence.ESTIMATE_DRIVEN, "med"),  # this-FY growth uses FY estimate
    "EPS Next Y": (Cadence.ESTIMATE_DRIVEN, "high"),
    "EPS Next 5Y": (Cadence.ESTIMATE_DRIVEN, "high"),

    # profitability & balance-sheet ratios from filed statements — FROZEN
    "ROA": (Cadence.REPORT_FROZEN, "high"),
    "ROE": (Cadence.REPORT_FROZEN, "high"),
    "ROIC": (Cadence.REPORT_FROZEN, "high"),
    "Curr R": (Cadence.REPORT_FROZEN, "high"),
    "Quick R": (Cadence.REPORT_FROZEN, "high"),
    "LTDebt/Eq": (Cadence.REPORT_FROZEN, "high"),
    "Debt/Eq": (Cadence.REPORT_FROZEN, "high"),
    "Gross M": (Cadence.REPORT_FROZEN, "high"),
    "Oper M": (Cadence.REPORT_FROZEN, "high"),
    "Profit M": (Cadence.REPORT_FROZEN, "high"),
    "Book/sh": (Cadence.REPORT_FROZEN, "high"),
    "Cash/sh": (Cadence.REPORT_FROZEN, "high"),
    "Employees": (Cadence.REPORT_FROZEN, "med"),          # from filings, updated infrequently

    # shares / ownership — regulatory filing cadences (NOT earnings, NOT daily)
    "Outstanding": (Cadence.REPORT_FROZEN, "med"),        # updated on filings
    "Float": (Cadence.REPORT_FROZEN, "med"),
    "Float %": (Cadence.REPORT_FROZEN, "med"),
    "Insider Own": (Cadence.FILING_PERIODIC, "high"),     # Form 4, ~2 business days
    "Insider Trans": (Cadence.FILING_PERIODIC, "high"),
    "Inst Own": (Cadence.FILING_PERIODIC, "high"),        # 13F, quarterly ~45-day lag
    "Inst Trans": (Cadence.FILING_PERIODIC, "high"),
    "Short Float": (Cadence.FILING_PERIODIC, "high"),     # FINRA, bi-monthly ~7 bd lag
    "Short Ratio": (Cadence.FILING_PERIODIC, "high"),
    "Short Interest": (Cadence.FILING_PERIODIC, "high"),

    # performance / technicals — recomputed every session from price
    "Perf Week": (Cadence.MARKET_DAILY, "high"),
    "Perf Month": (Cadence.MARKET_DAILY, "high"),
    "Perf Quart": (Cadence.MARKET_DAILY, "high"),
    "Perf Half": (Cadence.MARKET_DAILY, "high"),
    "Perf Year": (Cadence.MARKET_DAILY, "high"),
    "Perf YTD": (Cadence.MARKET_DAILY, "high"),
    "Beta": (Cadence.MARKET_DAILY, "med"),                # rolling regression on returns
    "ATR": (Cadence.MARKET_DAILY, "high"),
    "Volatility W": (Cadence.MARKET_DAILY, "high"),
    "Volatility M": (Cadence.MARKET_DAILY, "high"),
    "SMA20": (Cadence.MARKET_DAILY, "high"),
    "SMA50": (Cadence.MARKET_DAILY, "high"),
    "SMA200": (Cadence.MARKET_DAILY, "high"),
    "52W High": (Cadence.MARKET_DAILY, "high"),
    "52W Low": (Cadence.MARKET_DAILY, "high"),
    "52W Range": (Cadence.MARKET_DAILY, "high"),
    "RSI": (Cadence.MARKET_DAILY, "high"),
    "Prev Close": (Cadence.MARKET_DAILY, "high"),
    "Price": (Cadence.MARKET_DAILY, "high"),
    "Change": (Cadence.MARKET_DAILY, "high"),
    "Return% 1Y": (Cadence.MARKET_DAILY, "high"),
    "Avg Volume": (Cadence.MARKET_DAILY, "high"),
    "Rel Volume": (Cadence.MARKET_DAILY, "high"),
    "Volume": (Cadence.MARKET_DAILY, "high"),

    # analyst outputs — estimate driven
    "Target Price": (Cadence.ESTIMATE_DRIVEN, "high"),
    "Recom": (Cadence.ESTIMATE_DRIVEN, "high"),

    # calendar / flags
    "Earnings": (Cadence.ESTIMATE_DRIVEN, "med"),         # scheduled/estimated date, can shift
    "Index": (Cadence.FILING_PERIODIC, "med"),            # index reconstitution
    "Optionable": (Cadence.STATIC, "high"),
    "Shortable": (Cadence.STATIC, "high"),
}


# ---------------------------------------------------------------------------
# The spec. Order mirrors CUSTOM_TABLE_ALL_FIELDS_NEW.
# ---------------------------------------------------------------------------
FIELD_SPECS = [
    # --- identifiers -------------------------------------------------------
    FieldSpec("Ticker",   0, Kind.TEXT, "symbol"),
    FieldSpec("Company",  1, Kind.TEXT, "name"),
    FieldSpec("Sector",   2, Kind.TEXT, "category"),
    FieldSpec("Industry", 3, Kind.TEXT, "category"),
    FieldSpec("Country",  4, Kind.TEXT, "category"),

    # --- valuation ---------------------------------------------------------
    FieldSpec("Market Cap",  5, Kind.LEVEL_USD, "USD", "instant", "money_level"),
    FieldSpec("P/E",         6, Kind.RATIO, "x", "ttm"),
    FieldSpec("Forward P/E", 7, Kind.RATIO, "x", "next FY est"),
    FieldSpec("PEG",         8, Kind.RATIO, "x", "", note="P/E / EPS growth rate"),
    FieldSpec("P/S",         9, Kind.RATIO, "x", "ttm"),
    FieldSpec("P/B",        10, Kind.RATIO, "x"),
    FieldSpec("P/C",        11, Kind.RATIO, "x"),
    FieldSpec("P/FCF",      12, Kind.RATIO, "x", "ttm"),

    # --- dividends ---------------------------------------------------------
    FieldSpec("Dividend",     13, Kind.PCT, "%", "forward/indicated", "dividend_yield",
              note="Dividend YIELD % (forward/indicated), NOT dollars per share. "
                   "The $/share figure is 'Dividend TTM'."),
    FieldSpec("Payout Ratio", 14, Kind.PCT, "%", "ttm"),

    # --- EPS family (the important part) -----------------------------------
    FieldSpec("EPS",         15, Kind.LEVEL_USD_SHARE, "USD/share", "ttm",
              "eps_level", note="Diluted EPS, trailing twelve months (a $ level)."),
    FieldSpec("EPS next Q",  16, Kind.LEVEL_USD_SHARE, "USD/share", "next FQ est",
              "eps_level", source="fixture", confidence="high",
              note="Consensus $ EPS estimate for next quarter (a $ level, NOT a %). "
                   "Confirmed $-formatted in the mock payload."),
    FieldSpec("EPS This Y",  17, Kind.SIMPLE_GROWTH, "%", "this FY vs last FY",
              "eps_growth_1y",
              note="EPS GROWTH this fiscal year (a %), not a dollar estimate."),
    FieldSpec("EPS Next Y",  18, Kind.SIMPLE_GROWTH, "%", "next FY vs this FY (est)",
              "eps_growth_1y",
              note="EPS GROWTH next fiscal year (a %), not a dollar estimate."),
    FieldSpec("EPS Past 5Y", 19, Kind.CAGR, "%/yr", "5y annualized", "eps_growth_5y",
              note="Annualized (CAGR) EPS growth, past 5 FY. NOT comparable to 1y growth."),
    FieldSpec("EPS Next 5Y", 20, Kind.CAGR, "%/yr", "~5y annualized est", "eps_growth_5y",
              note="Annualized long-term EPS growth estimate (CAGR)."),
    # NOTE: field order below mirrors CUSTOM_TABLE_ALL_FIELDS_NEW (i.e. the order
    # Finviz emits the columns), which interleaves the Sales and EPS growth
    # fields. Do not "tidy" this into pure EPS-then-Sales groups — the test
    # test_spec_covers_exactly_the_fetched_fields enforces this exact order.
    FieldSpec("Sales Past 5Y", 21, Kind.CAGR, "%/yr", "5y annualized", "sales_growth_5y",
              note="Annualized (CAGR) sales growth, past 5 FY."),
    FieldSpec("Sales Q/Q",     23, Kind.YOY, "%", "latest Q vs year-ago Q", "sales_yoy",
              note="MISLEADING NAME: YEAR-OVER-YEAR revenue growth (latest quarter vs "
                   "same quarter last year), not sequential."),
    FieldSpec("Sales YoY TTM", 22, Kind.YOY, "%", "ttm vs prior ttm", "sales_yoy",
              source="fixture", confidence="high",
              note="Revenue growth, trailing-12m vs prior trailing-12m (a %). "
                   "Confirmed %-formatted in the mock payload; exact window still "
                   "TTM-vs-prior-TTM by convention."),
    FieldSpec("EPS Q/Q",     78, Kind.YOY, "%", "latest Q vs year-ago Q", "eps_yoy",
              note="MISLEADING NAME: this is YEAR-OVER-YEAR (latest quarter vs the "
                   "same quarter one year ago), not sequential quarter-over-quarter."),
    FieldSpec("Sales",  127, Kind.LEVEL_USD, "USD", "ttm", "money_level",
              note="Total revenue, trailing twelve months (a $ level)."),
    FieldSpec("Income", 128, Kind.LEVEL_USD, "USD", "ttm", "money_level",
              source="fixture", confidence="high",
              note="Net income, trailing twelve months (a $ level). Confirmed "
                   "money-magnitude (K/M/B/T) in the mock payload."),
    FieldSpec("EPS Surprise", 24, Kind.SURPRISE, "%", "last report", "surprise",
              source="fixture", confidence="high",
              note="Actual EPS vs consensus estimate, last interim report (a beat/miss %). "
                   "Confirmed %-formatted in the mock payload."),
    FieldSpec("Revenue Surprise", 25, Kind.SURPRISE, "%", "last report", "surprise",
              source="fixture", confidence="high",
              note="Actual revenue vs consensus estimate, last report (a beat/miss %). "
                   "Confirmed %-formatted in the mock payload."),

    # --- shares / ownership ------------------------------------------------
    FieldSpec("Outstanding",   85, Kind.LEVEL_COUNT, "shares", "instant"),
    FieldSpec("Float",         26, Kind.LEVEL_COUNT, "shares", "instant"),
    FieldSpec("Float %",       27, Kind.PCT, "%", "", note="Float / shares outstanding."),
    FieldSpec("Insider Own",   28, Kind.PCT, "%"),
    FieldSpec("Insider Trans", 29, Kind.PCT, "%", note="Recent net insider transactions."),
    FieldSpec("Inst Own",      30, Kind.PCT, "%"),
    FieldSpec("Inst Trans",    31, Kind.PCT, "%", note="Net institutional transactions."),
    FieldSpec("Short Float",   32, Kind.PCT, "%", note="Short interest / float."),
    FieldSpec("Short Ratio",   33, Kind.RATIO, "days", note="Short interest / avg daily volume."),
    FieldSpec("Short Interest", 34, Kind.LEVEL_COUNT, "shares"),

    # --- profitability & returns (see FINVIZ_METRIC_BASES.md) --------------
    FieldSpec("ROA",  35, Kind.PCT, "%", "ttm", "returns_ratio", note="Net income / assets. One-off-sensitive."),
    FieldSpec("ROE",  36, Kind.PCT, "%", "ttm", "returns_ratio", note="Net income / equity. One-off-sensitive."),
    FieldSpec("ROIC", 37, Kind.PCT, "%", "ttm", "returns_ratio",
              note="Finviz ROIC = Net Income / Invested Capital (NOT NOPAT-based!). "
                   "One-off-sensitive. See FINVIZ_METRIC_BASES.md."),
    FieldSpec("Curr R",    38, Kind.RATIO, "x", note="Current ratio."),
    FieldSpec("Quick R",   39, Kind.RATIO, "x", note="Quick ratio."),
    FieldSpec("LTDebt/Eq", 40, Kind.RATIO, "x"),
    FieldSpec("Debt/Eq",   41, Kind.RATIO, "x"),
    FieldSpec("Gross M",   42, Kind.PCT, "%", "ttm", "margins", note="(Revenue - COGS) / Revenue. Clean (operating-level)."),
    FieldSpec("Oper M",    43, Kind.PCT, "%", "ttm", "margins", note="Operating income / net sales. Clean."),
    FieldSpec("Profit M",  44, Kind.PCT, "%", "ttm", "margins", note="Net income / revenue. One-off-sensitive."),

    # --- performance (point returns) --------------------------------------
    FieldSpec("Perf Week",  45, Kind.PCT_RETURN, "%", "1 week", "returns_pct"),
    FieldSpec("Perf Month", 46, Kind.PCT_RETURN, "%", "1 month", "returns_pct"),
    FieldSpec("Perf Quart", 47, Kind.PCT_RETURN, "%", "1 quarter", "returns_pct"),
    FieldSpec("Perf Half",  48, Kind.PCT_RETURN, "%", "6 months", "returns_pct"),
    FieldSpec("Perf Year",  49, Kind.PCT_RETURN, "%", "1 year", "returns_pct"),
    FieldSpec("Perf YTD",   50, Kind.PCT_RETURN, "%", "year to date", "returns_pct"),

    # --- risk / technical --------------------------------------------------
    FieldSpec("Beta",         51, Kind.RATIO, "x"),
    FieldSpec("ATR",          52, Kind.LEVEL_USD, "USD", note="Average true range."),
    FieldSpec("Volatility W", 53, Kind.PCT, "%", "1 week"),
    FieldSpec("Volatility M", 54, Kind.PCT, "%", "1 month"),
    FieldSpec("SMA20",  57, Kind.PCT_FROM_LEVEL, "%", "", "sma_dist", note="% distance of price from SMA20 (not the SMA level)."),
    FieldSpec("SMA50",  58, Kind.PCT_FROM_LEVEL, "%", "", "sma_dist", note="% distance of price from SMA50."),
    FieldSpec("SMA200", 59, Kind.PCT_FROM_LEVEL, "%", "", "sma_dist", note="% distance of price from SMA200."),
    FieldSpec("52W High", 62, Kind.PCT_FROM_LEVEL, "%", "", note="% distance below the 52-week high."),
    FieldSpec("52W Low",  63, Kind.PCT_FROM_LEVEL, "%", "", note="% distance above the 52-week low."),
    FieldSpec("RSI",      64, Kind.RATIO, "0-100", "14-period"),

    # --- misc / identifiers ------------------------------------------------
    FieldSpec("Earnings",     65, Kind.DATE, "date", note="Next earnings date/time. Dropped in FINVIZ_DROP_COLUMNS."),
    FieldSpec("Target Price", 66, Kind.LEVEL_USD, "USD", note="Mean analyst price target."),
    FieldSpec("Book/sh",      67, Kind.LEVEL_USD_SHARE, "USD/share"),
    FieldSpec("Cash/sh",      68, Kind.LEVEL_USD_SHARE, "USD/share"),
    FieldSpec("Employees",    69, Kind.LEVEL_COUNT, "count"),
    FieldSpec("Index",        73, Kind.TEXT, "membership", note="Dropped in FINVIZ_DROP_COLUMNS."),
    FieldSpec("Optionable",   74, Kind.BOOL, "bool"),
    FieldSpec("Prev Close",   76, Kind.LEVEL_USD, "USD"),
    FieldSpec("Shortable",    77, Kind.BOOL, "bool"),
    FieldSpec("Recom",        79, Kind.RATIO, "1-5", note="Mean analyst recommendation (1=strong buy .. 5=strong sell)."),
    FieldSpec("Avg Volume",   80, Kind.LEVEL_COUNT, "shares"),
    FieldSpec("Rel Volume",   81, Kind.RATIO, "x"),
    FieldSpec("Volume",       82, Kind.LEVEL_COUNT, "shares"),
    FieldSpec("Price",        83, Kind.LEVEL_USD, "USD"),
    FieldSpec("Change",       84, Kind.PCT_RETURN, "%", "today", "returns_pct"),
    FieldSpec("Return% 1Y",   120, Kind.PCT_RETURN, "%", "1 year", "returns_pct", note="Dropped in FINVIZ_DROP_COLUMNS."),
    FieldSpec("Dividend TTM", 130, Kind.LEVEL_USD_SHARE, "USD/share", "ttm"),
    FieldSpec("Dividend Ex Date", 131, Kind.DATE, "date"),
    FieldSpec("EPS YoY TTM", 132, Kind.YOY, "%", "ttm vs prior ttm", "eps_yoy",
              source="fixture", confidence="high",
              note="EPS growth, trailing-12m vs prior trailing-12m (a %). "
                   "Confirmed %-formatted in the mock payload; exact window still "
                   "TTM-vs-prior-TTM by convention."),
    FieldSpec("52W Range",    133, Kind.TEXT, "low-high", note="Raw range string. Dropped in FINVIZ_DROP_COLUMNS."),
    FieldSpec("Enterprise Value", 134, Kind.LEVEL_USD, "USD", "instant", "money_level"),
    FieldSpec("EV/EBITDA",    144, Kind.RATIO, "x", "ttm"),
    FieldSpec("EV/Sales",     145, Kind.RATIO, "x", "ttm"),
]


# Extra Finviz code present in CUSTOM_TABLE_FIELDS_ON_URL but with no captured
# field name (the source of the "89 codes vs 88 names" offset). Recorded here so
# the test can assert it stays known/intentional rather than silently drifting.
UNMAPPED_FINVIZ_CODES = {146}


# Fast lookups
BY_NAME = {fs.name: fs for fs in FIELD_SPECS}
BY_CODE = {fs.finviz_code: fs for fs in FIELD_SPECS if fs.finviz_code is not None}


def comparable_to(name):
    """Return the other fetched field names that are directly comparable
    (equal in magnitude / same compare_group) to ``name``."""
    fs = BY_NAME.get(name)
    if fs is None or fs.compare_group is None:
        return []
    return [o.name for o in FIELD_SPECS
            if o.compare_group == fs.compare_group and o.name != name]


# ---------------------------------------------------------------------------
# Markdown generation (keeps FINVIZ_FIELDS.md in sync with this spec)
# ---------------------------------------------------------------------------
def to_markdown():
    lines = [
        "# Finviz Field Spec",
        "",
        "> **Generated file — do not edit by hand.** Regenerate with:",
        "> `python -m earningspy.generators.finviz.field_spec > "
        "earningspy/generators/finviz/FINVIZ_FIELDS.md`",
        "",
        "Source of truth: `earningspy/generators/finviz/field_spec.py`. "
        "Validated by `tests/generators/test_field_spec.py`.",
        "Primary definition source: <https://finviz.com/help/screener> (2026-07-26).",
        "See `docs/FINVIZ_METRIC_BASES.md` for the net-income vs operating basis of "
        "the profitability ratios.",
        "",
        "**Legend — `kind`:** `level_usd`/`level_usd_sh` = dollar amount; "
        "`level_count` = raw count; `simple_growth` = single-period % growth; "
        "`cagr` = annualized multi-year % growth; `yoy` = year-over-year % change; "
        "`surprise` = actual vs estimate %; `ratio`/`pct` = ratio/percentage; "
        "`pct_return` = point price return; `pct_from_level` = % distance from an "
        "SMA/52w level.",
        "",
        "**`compare with`** lists fields that are equal in magnitude / directly "
        "comparable (same growth basis, same unit).",
        "",
        "**Legend — `Src` (provenance):** `finviz` = defined on finviz.com/help/"
        "screener; `fixture` = semantic type empirically confirmed against the real "
        "mock payload in tests; `cross-ref` / `convention` = inferred, lower "
        "confidence.",
        "",
        "**`Description`** is the plain-language, client-facing summary of what the "
        "value tells you and how it is composed.",
        "",
        "**Legend — `Serving`** (the operational decision for the pre-earnings "
        "snapshot model: data is scraped once per stock 1-5 days before its "
        "earnings and stored, so each field must say whether a stored value can be "
        "served or must be re-fetched):",
        "- `serve_from_snapshot` — stable over a 1-5 day (up to weekly) window; "
        "serve the stored value. Covers filing-reported fundamentals, the "
        "multi-week ownership/short cadences, analyst estimates, and static ids.",
        "- `serve_stale_recompute` — the fundamental part is fine from the "
        "snapshot, but the value embeds **live price** and goes stale within days; "
        "serve stored only if you recompute the price component (or re-fetch).",
        "- `fetch_on_demand` — moves materially day-to-day (pure price/technical); "
        "the stored snapshot is noise by serving time, so fetch live.",
        "",
        "**Legend — `Update cadence`** (how often the value changes; Finviz does "
        "not publish per-field refresh rates, so these are reasoned from the "
        "formula/data source and cross-checked against regulatory schedules):",
        "- `market_daily` — recomputed every trading session (pure price/technical).",
        "- `price_over_fundamental` — a ratio whose fundamental input is frozen at "
        "the last report, but the value still **drifts every day because price is "
        "in it** (e.g. P/E, P/S, dividend yield); it 'resets' at earnings.",
        "- `report_frozen` — **frozen between financial reports** (10-Q/10-K); the "
        "classic 'frozen at earnings' set. Changes only when new financials are filed.",
        "- `estimate_driven` — analyst estimates/targets/ratings, revised on no fixed "
        "schedule; clusters around earnings but is not frozen to it.",
        "- `filing_periodic` — regulatory filing cadence, **not** earnings: 13F "
        "institutional (quarterly, ~45-day lag), Form 4 insider (~2 business days), "
        "short interest (bi-monthly, ~7 business-day lag).",
        "- `static` — identifiers/classification; changes rarely if ever.",
        "",
        "`Cad.conf` is the confidence in the cadence label (a higher bar was applied "
        "to the `report_frozen` set, since that is the one intended for downstream "
        "'frozen' logic).",
        "",
        "| Finviz code | Field | Description | Serving | Update cadence | Cad.conf | Kind | Unit | Period | Compare with | Src | Conf | Note |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for fs in FIELD_SPECS:
        code = "-" if fs.finviz_code is None else str(fs.finviz_code)
        cmp = ", ".join(comparable_to(fs.name)) or "-"
        note = fs.note.replace("|", "\\|")
        desc = fs.description.replace("|", "\\|")
        serving = fs.serving or "-"
        cadence = fs.cadence or "-"
        cad_conf = fs.cadence_confidence or "-"
        lines.append(
            f"| {code} | `{fs.name}` | {desc} | {serving} | {cadence} | {cad_conf} | "
            f"{fs.kind} | {fs.unit} | {fs.period or '-'} | {cmp} | {fs.source} | "
            f"{fs.confidence} | {note} |"
        )
    lines += [
        "",
        f"**Unmapped Finviz code(s)** requested in the URL but not captured as a "
        f"named column: {sorted(UNMAPPED_FINVIZ_CODES)} "
        f"(source of the 89-codes vs 88-names offset).",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(to_markdown())
