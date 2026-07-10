# Spec — Intraday Yahoo price fetch for the `earningspy` package

Add **new, additive** intraday fetch methods to the `earningspy` package's Yahoo
generators, without touching the existing daily code path. The current daily
functions (`get_portfolio`, `get_one_ticker`, `_fetch_ticker_data`, `prepare_data`,
`get_range`) stay **exactly as they are** — they are relied on across
`earningspy-platform` (kelly, silver VIX, risk_mgmt data) and by the test suite's
patch targets, and their contract (one close price per day, `interval=1d`,
month/year windows) must not change.

## Why new methods (not a flag on the old ones)

The existing chain is daily-only by three separate design decisions, each of which
is *correct* for daily but *wrong* for intraday:

1. `interval=1d` is hardcoded in the request URL.
2. `data.index.normalize()` flattens every timestamp to midnight — this destroys
   intraday granularity and would collapse many bars into one row per day.
3. `prepare_data()` drops `open/high/low/volume`, keeping only `close`.

Rather than thread conditionals through those, intraday gets its own functions that
keep the real timestamp and (optionally) full OHLCV. Shared, interval-agnostic
helpers (`_create_session`, `_get_retry_strategy`, `get_range_timestamps`,
`_get_response_hint`) are **reused as-is**.

## Scope

- **File:** `earningspy/generators/yahoo/intraday.py` (new module, sibling of
  `time_series.py`). Keeps the daily and intraday surfaces cleanly separated.
- **No edits** to `time_series.py` or `async_timeseries.py`.
- Repo side (`earningspy-platform`): out of scope for this spec, but see
  "Downstream" for the follow-up (`fetch_live_prices_intraday`).

---

## Yahoo v8 chart endpoint — reference

Base URL (same host the daily path uses):

```
https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?{params}
```

### Parameters

| Param            | Values / format                                              | Notes |
|------------------|--------------------------------------------------------------|-------|
| `interval`       | `1m,2m,5m,15m,30m,60m,90m,1h` (intraday); `1d,5d,1wk,1mo,3mo` | Intraday = `< 1d`. |
| `range`          | `1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max`                     | Use `range` **or** `period1/period2`, never both. |
| `period1`,`period2` | Unix timestamps (seconds)                                 | Must stay inside the interval's history cap (below). |
| `includePrePost` | `true` / `false`                                             | Pre/after-hours bars. Default `false`. Relevant for earnings gaps. |
| `events`         | `div`, `split`, `earn`, `history`, or piped `div\|split\|earn`| Optional. |
| `corsDomain`     | `finance.yahoo.com`                                          | Optional; can avoid occasional CDN 4xx. |

### Intraday history caps (HARD limits — enforce these)

Yahoo caps how far back each intraday interval reaches per request. A `period1`
older than the cap returns **HTTP 422 Unprocessable Entity** (not empty/partial
data) with a `chart.error.description` like `"1m data not available for
startTime=… and endTime=…"`. **Validated live during spec review — see "Live
validation" below.** So clamping is not just an optimization: unclamped over-cap
requests fail outright, and the code should both clamp proactively AND surface a
422's description as a distinct, informative error. **These caps MUST be documented
in each intraday function's docstring** (requirement below) and enforced in code.

| Interval           | Max history back from now |
|--------------------|---------------------------|
| `1m`               | **7 days**                |
| `2m,5m,15m,30m,90m,1h` | **60 days**           |
| `60m`              | **730 days (~2 years)** — note: Yahoo aliases `60m` to `1h` server-side, so the response `meta.dataGranularity` reads `1h`. Harmless; don't treat it as a mismatch. |
| (general `< 1d` ceiling) | **60 days**         |

Encode as a module constant:

```python
# Max lookback (in days) Yahoo allows per request, keyed by interval.
INTRADAY_MAX_DAYS = {
    "1m": 7,
    "2m": 60, "5m": 60, "15m": 60, "30m": 60, "90m": 60, "1h": 60,
    "60m": 730,
}
VALID_INTRADAY_INTERVALS = tuple(INTRADAY_MAX_DAYS.keys())
```

---

## Live validation (run during spec review, 2026-07-10, HELE)

A naive `requests.get` against the live v8 endpoint confirmed the design and
surfaced the error behaviors above. Evidence:

| Request                                   | Result |
|-------------------------------------------|--------|
| `range=5d&interval=5m`                    | 200 — 391 bars, `meta.exchangeTimezoneName=America/New_York`, first bar `13:30 UTC` = `09:30 ET` (open). OHLCV all present. |
| `range=5d&interval=1m`                    | 200 — 1951 bars, span 7 days (the 1m cap). |
| `range=1mo&interval=1m` (over 7d)         | **422** — `"1m data not available for startTime=… endTime=…"`. |
| `period1/period2` 10d, `interval=5m`      | 200 — 547 bars. |
| `period1` 90d, `interval=5m` (over 60d)   | **422** — `"5m data not available for …"`. |
| `range=1d&interval=5m&includePrePost=true`, run 07:33 ET | 200 — **0 bars** (pre-open timing artifact of `range=1d`). |
| `range=5d&interval=5m&includePrePost=true`| 200 — 415 bars, 99 outside RTH (pre `08:00 UTC`/04:00 ET … post `22:30 UTC`/18:30 ET). prepost works. |
| `range=1y&interval=60m`                   | 200 — 1754 bars, `meta.dataGranularity=1h` (60m aliases to 1h). |
| `range=5d&interval=7m` (invalid)          | **400** — `"Invalid input - interval=7m is not supported. Valid intervals: [1m, 2m, 5m, …]"`. |

Takeaways baked into this spec: over-cap → 422 (clamp + surface description);
`range=1d` can return 0 bars pre-open (prefer `range=5d`); `60m`→`1h` granularity;
tz is `America/New_York`; a `User-Agent` header is required (Yahoo 429s without one).

---

## New public API

### 1. `get_one_ticker_intraday(...)`

```python
def get_one_ticker_intraday(
    asset: str,
    interval: str = "5m",
    *,
    lookback_days: int | None = None,
    range_: str | None = None,
    include_prepost: bool = False,
    end_date=None,          # datetime.date; default today
    session=None,
    timeout: int = 10,
) -> pd.DataFrame | None:
    """
    Fetch INTRADAY OHLCV bars for one ticker from the Yahoo v8 chart API.

    Returns a DataFrame indexed by a timezone-naive DatetimeIndex named 'Date'
    at full intraday resolution (the timestamp is NOT normalized to midnight),
    with columns: open, high, low, close, volume. Returns None on any fetch/parse
    failure (mirrors the daily path's error convention).

    Interval history caps (Yahoo limits per request — requests beyond these
    return empty/partial data, so lookback is clamped to the cap):

        interval                       max history back from now
        ------------------------------ -------------------------
        1m                             7 days
        2m, 5m, 15m, 30m, 90m, 1h      60 days
        60m                            730 days (~2 years)

    Parameters
    ----------
    asset : ticker symbol, e.g. 'HELE'.
    interval : one of VALID_INTRADAY_INTERVALS. Default '5m'.
    lookback_days : how many days back to request via period1/period2. If None,
        defaults to the interval's cap. Values above the cap are clamped (a
        warning is logged). Ignored if range_ is given.
    range_ : optional Yahoo 'range' value ('1d','5d',...) used INSTEAD of
        period1/period2. When set, lookback_days is ignored. Prefer range_='1d'
        or '5d' for "today / this week" intraday pulls.
    include_prepost : include pre/after-hours bars (includePrePost=true).
    end_date : window end (datetime.date). Default today.
    session : optional requests.Session (reuse _create_session() for pooling).
    timeout : per-request timeout seconds.

    Raises
    ------
    ValueError : if interval not in VALID_INTRADAY_INTERVALS.
    """
```

Behavior:
- Validate `interval ∈ VALID_INTRADAY_INTERVALS`, else `ValueError`.
- Build the URL with `interval={interval}` and either `range={range_}` **or**
  `period1/period2` (clamped `lookback_days`), plus `includePrePost` when set.
- Reuse `get_range_timestamps` for the timestamp conversion, `_create_session` /
  session arg for pooling, `_get_retry_strategy` (already mounted on the session).
- Parse `chart.result[0]`: build the frame from
  `result['indicators']['quote'][0]` (open/high/low/close/volume) and
  `result['timestamp']`.
- Timestamps: `pd.to_datetime(ts, unit='s')` — **do NOT call `.normalize()`**.
  Yahoo returns UTC epoch seconds; convert to the exchange session tz if needed
  (see "Timezone" below) but keep the time-of-day.
- Round prices to 2 dp; leave volume as int.
- Same try/except structure and warning logs as `_fetch_ticker_data`.

### 2. `get_portfolio_intraday(...)`

```python
def get_portfolio_intraday(
    assets,
    interval: str = "5m",
    *,
    lookback_days: int | None = None,
    range_: str | None = None,
    include_prepost: bool = False,
    field: str = "close",        # 'close' | 'ohlcv'
    end_date=None,
    timeout: int = 10,
    max_workers: int = 10,
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """
    Fetch INTRADAY data for many tickers concurrently.

    field='close' (default): returns a single wide DataFrame — one column per
        ticker of intraday CLOSE prices, indexed by the union of bar timestamps
        (analogous to the daily get_portfolio close matrix, but intraday-grained).
    field='ohlcv': returns dict[ticker -> per-ticker OHLCV DataFrame] (from
        get_one_ticker_intraday), for callers that need full bars.

    Interval history caps — see get_one_ticker_intraday (1m: 7d; most: 60d;
    60m: 730d). lookback_days is clamped to the interval's cap.

    Mirrors get_portfolio's concurrency (ThreadPoolExecutor + _create_session),
    dedup of requested assets, per-asset failure isolation (skip + collect in
    not_found), and progress logging. Raises ValueError only if NO ticker resolves.
    """
```

Behavior:
- Dedup assets, spin a `ThreadPoolExecutor(max_workers=min(max_workers, n))`,
  submit `get_one_ticker_intraday` per asset over one shared session.
- Per-asset failures are skipped and collected (same as daily `get_portfolio`);
  raise `ValueError("No valid assets found — portfolio is empty")` only if every
  ticker failed.
- `field='close'`: for each ticker take its `close` column, `concat(axis=1,
  join='outer')`, sort index, dedup index keeping last. **No `.normalize()`**.
- `field='ohlcv'`: return the raw per-ticker frames untouched.

---

## Timezone

The daily path is date-only, so tz was irrelevant. Intraday must be explicit:

- Yahoo `timestamp` is **UTC epoch seconds**. `pd.to_datetime(ts, unit='s')` yields
  tz-naive UTC.
- Decision to document in the docstring and implement consistently: convert to the
  instrument's **exchange timezone** (US equities → `America/New_York`) then drop
  tz to keep it naive, so bar times read as market-local (e.g. 09:30–16:00). The
  chart response includes `result['meta']['exchangeTimezoneName']` — use it when
  present, fall back to `America/New_York`.
- Whichever convention is chosen, state it in the docstring; do not leave it
  implicit.

## `include_prepost`

- When `include_prepost=True`, add `includePrePost=true` to the URL. Pre/after-hours
  bars are exactly the moves that matter around earnings, so this is a first-class
  option, off by default to match RTH-only expectations.
- Yahoo also returns `result['meta']['tradingPeriods']` (pre/regular/post ranges);
  optional: expose a helper to tag each bar's session, but not required for v1.

---

## Errors, logging, retries — reuse the daily conventions

- Reuse `_create_session()` and `_get_retry_strategy()` verbatim (429/5xx retry,
  pooled adapters). Do not fork them.
- Same log style: `logger.info` on fetch start/success with row counts,
  `logger.warning` on non-OK status / parse failure / empty data, `logger.exception`
  on unexpected errors. Return `None` (single) / skip-and-collect (portfolio) on
  failure — never raise for a single bad ticker.
- Reuse `_get_response_hint` for non-OK body snippets.
- **HTTP 422 (over-cap) handling:** on a 422, parse `chart.error.description` and
  log it explicitly (e.g. `"Yahoo 422 for %s: %s"`), because it names the exact
  window that exceeded the cap — far more useful than a generic "non-OK status".
  With `lookback_days` clamped this should not fire, but a caller passing raw
  `period1/period2` can still trigger it, so surface it clearly.
- **Empty-but-OK results:** an HTTP 200 can still carry zero bars — most commonly
  `range=1d` called before/at the open (validated live: a pre-market call returned
  0 bars). Treat `len(timestamp)==0` as a skip (single → `None`, portfolio →
  not_found), same as an error, and log it at `warning`.

---

## Testing (add to the package's test suite, network-mocked)

Side-effect-free — mock the HTTP layer (patch `session.get` / `requests.get` to
return a canned `chart` JSON payload). Cover:

1. `interval` validation → `ValueError` for `'1d'`, `'7m'`, junk.
2. `lookback_days` clamping: `1m` with `lookback_days=30` clamps to 7 (assert the
   `period1` sent corresponds to ≤7 days; assert a warning was logged).
2b. **422 over-cap:** mock a 422 with a `chart.error.description` body → function
    returns `None` (single) / skips (portfolio) and logs the description. (Reachable
    when a caller passes raw `period1/period2` beyond the cap.)
2c. **Empty-but-200:** mock a 200 whose `result[0].timestamp` is empty/absent →
    treated as a skip (not a crash), logged at warning. (The `range=1d` pre-open case.)
3. Timestamps are **not** normalized — bar index has intraday times (minutes differ
   within a day), not all midnight.
4. OHLCV columns present and typed (`field='ohlcv'`); `field='close'` yields a wide
   close-only matrix.
5. `include_prepost=True` puts `includePrePost=true` in the requested URL.
6. `range_='5d'` path omits `period1/period2` and sends `range=5d`.
7. Portfolio: one bad ticker is skipped (collected in not_found), others returned;
   all-bad raises `ValueError`.
8. Concurrency dedups repeated tickers.

---

## Downstream (follow-up, separate change in `earningspy-platform` — not this spec)

Once the package ships the above, add a thin repo-side wrapper mirroring
`fetch_live_prices` (kelly.py) but intraday, e.g.:

```python
def fetch_live_prices_intraday(tickers, interval="5m", *, include_prepost=False):
    """Most recent INTRADAY bar close per ticker (latest live mark).

    Uses range_='5d' (NOT '1d'): a 1d intraday window is timing-fragile and can
    legitimately return ZERO bars before/at the open (validated live). A 5d window
    always carries a recent bar, and .iloc[-1] is still the latest mark.
    """
    from earningspy.generators.yahoo.intraday import get_portfolio_intraday
    portfolio = get_portfolio_intraday(tickers, interval=interval,
                                       range_="5d", include_prepost=include_prepost)
    return portfolio.iloc[-1].dropna().to_dict()
```

This would give `tos-order --refetch` a true intraday mark instead of the latest
daily close. Wiring that flag is a later, opt-in step; the daily default path
stays untouched.

> **`range=1d` caveat.** Do not default any intraday convenience path to
> `range_='1d'`. Live validation showed a `range=1d` 5-minute request run at
> 07:33 ET (pre-open) returned an HTTP 200 with **0 bars**. Use `range_='5d'` (or
> an explicit `period1/period2`) for "latest mark" use cases so the call is robust
> across the session, including pre-market.

---

## Acceptance criteria

- [ ] `time_series.py` and `async_timeseries.py` are byte-for-byte unchanged.
- [ ] New `intraday.py` exposes `get_one_ticker_intraday` and
      `get_portfolio_intraday`, reusing the shared session/retry/timestamp helpers.
- [ ] Each intraday function's docstring documents the per-interval max-history
      table (1m→7d, most→60d, 60m→730d).
- [ ] `interval` is validated; `lookback_days` is clamped to the cap with a warning.
- [ ] Over-cap 422 responses are handled distinctly (parse `chart.error.description`,
      log it, return None/skip); empty-but-200 results are treated as a skip, not a crash.
- [ ] Intraday timestamps retain time-of-day (no `.normalize()`); tz convention is
      documented.
- [ ] `include_prepost` and `range_` supported; `events`/`corsDomain` optional.
- [ ] Network-mocked tests cover validation, clamping, non-normalized timestamps,
      OHLCV vs close, prepost, and portfolio failure isolation.

## Sources

- [AlgoTrading101 — Yahoo Finance / yfinance intervals & intraday range caps (1m=7d, intraday ≤60d, 60m=730d)](https://algotrading101.com/learn/yfinance-guide/)
- [Marketcalls — Yahoo v8 chart params: includePrePost, events=div|split|earn, range/interval example URL](https://www.marketcalls.in/intraday/exploring-yahoo-finance-realtime-quotes-and-historical-data-feed-api.html)
- [AlgoTrading101 — Yahoo Finance API guide (range & interval value lists)](https://algotrading101.com/learn/yahoo-finance-api-guide/)
- [yfinance issue #2451 — interval/period interactions](https://github.com/ranaroussi/yfinance/issues/2451)
- [yfinance history scraper (reference impl of the same v8 endpoint)](https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py)
