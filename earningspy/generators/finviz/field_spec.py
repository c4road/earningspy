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
    note: str = ""


# ---------------------------------------------------------------------------
# Comparability groups (fields equal in magnitude / directly comparable)
# ---------------------------------------------------------------------------
# eps_growth_1y : single-year EPS growth (This Y vs Next Y are the same magnitude scale)
# eps_growth_5y : annualized (CAGR) EPS growth — NOT comparable to 1y growth
# eps_yoy       : year-over-year EPS growth (Q/Q [actually YoY] vs YoY TTM)
# eps_level     : dollar EPS values (ttm actual vs next-Q estimate)
# sales_growth_5y, sales_yoy, money_level, margins, returns_pct, ...

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
        "| Finviz code | Field | Kind | Unit | Period | Compare with | Src | Conf | Note |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for fs in FIELD_SPECS:
        code = "-" if fs.finviz_code is None else str(fs.finviz_code)
        cmp = ", ".join(comparable_to(fs.name)) or "-"
        note = fs.note.replace("|", "\\|")
        lines.append(
            f"| {code} | `{fs.name}` | {fs.kind} | {fs.unit} | {fs.period or '-'} | "
            f"{cmp} | {fs.source} | {fs.confidence} | {note} |"
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
