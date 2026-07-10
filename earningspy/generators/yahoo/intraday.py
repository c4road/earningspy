"""
Intraday OHLCV data fetching from Yahoo Finance v8 chart endpoint.

This module provides intraday price bars with full timestamp resolution (no
normalization to midnight), reusing the session, retry, and helper patterns
from the daily time_series module.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime as dt, timedelta
from typing import Optional, Union, Dict

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .time_series import (
    _get_response_hint,
    _get_retry_strategy,
    _create_session,
    get_range_timestamps,
)

logger = logging.getLogger(__name__)

# Max lookback (in days) Yahoo allows per request, keyed by interval.
INTRADAY_MAX_DAYS = {
    "1m": 7,
    "2m": 60,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "90m": 60,
    "1h": 60,
    "60m": 730,
}
VALID_INTRADAY_INTERVALS = tuple(INTRADAY_MAX_DAYS.keys())


def get_one_ticker_intraday(
    asset: str,
    interval: str = "5m",
    *,
    lookback_days: Optional[int] = None,
    range_: Optional[str] = None,
    include_prepost: bool = False,
    end_date=None,
    session=None,
    timeout: int = 10,
) -> Optional[pd.DataFrame]:
    """
    Fetch INTRADAY OHLCV bars for one ticker from the Yahoo v8 chart API.

    Returns a DataFrame indexed by a timezone-naive DatetimeIndex named 'Date'
    at full intraday resolution (the timestamp is NOT normalized to midnight),
    with columns: open, high, low, close, volume. Returns None on any fetch/parse
    failure.

    Interval history caps (Yahoo limits per request — requests beyond these
    can return HTTP 422 or empty data, so lookback is clamped to the cap):

        interval                       max history back from now
        ------------------------------ -------------------------
        1m                             7 days
        2m, 5m, 15m, 30m, 90m, 1h      60 days
        60m                            730 days (~2 years)

    Parameters
    ----------
    asset : str
        Ticker symbol, e.g. 'HELE'.
    interval : str
        One of VALID_INTRADAY_INTERVALS. Default '5m'.
    lookback_days : Optional[int]
        How many days back to request via period1/period2. If None, defaults to
        the interval's cap. Values above the cap are clamped (a warning is logged).
        Ignored if range_ is given.
    range_ : Optional[str]
        Optional Yahoo 'range' value ('1d','5d',...) used INSTEAD of
        period1/period2. When set, lookback_days is ignored. Prefer range_='1d'
        or '5d' for "today / this week" intraday pulls.
    include_prepost : bool
        Include pre/after-hours bars (includePrePost=true). Default False.
    end_date
        Window end (datetime.date). Default today.
    session
        Optional requests.Session (reuse _create_session() for pooling).
    timeout : int
        Per-request timeout seconds. Default 10.

    Returns
    -------
    Optional[pd.DataFrame]
        DataFrame with DatetimeIndex (intraday resolution, not normalized to
        midnight) and columns [open, high, low, close, volume]. None if fetch
        or parse fails.

    Raises
    ------
    ValueError
        If interval not in VALID_INTRADAY_INTERVALS.
    """
    if interval not in VALID_INTRADAY_INTERVALS:
        raise ValueError(
            f"Invalid interval '{interval}'. Must be one of: {', '.join(VALID_INTRADAY_INTERVALS)}"
        )

    if end_date is None:
        end_date = dt.now().date()

    headers = {
        "User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; .NET CLR 1.0.3705;)",
    }

    # Build URL and log intent
    if range_ is not None:
        url = (
            f"https://query2.finance.yahoo.com/v8/finance/chart/{asset}?"
            f"range={range_}&interval={interval}&events=history"
        )
        if include_prepost:
            url += "&includePrePost=true"

        logger.info(
            "Fetching Yahoo intraday ticker %s interval=%s range=%s",
            asset,
            interval,
            range_,
        )
        logger.debug("Yahoo intraday request asset=%s url=%s", asset, url)
    else:
        # Use period1/period2 with clamped lookback_days
        cap = INTRADAY_MAX_DAYS[interval]
        if lookback_days is None:
            lookback_days = cap
        elif lookback_days > cap:
            logger.warning(
                "Clamping lookback_days=%s to interval cap=%s for %s interval=%s",
                lookback_days,
                cap,
                asset,
                interval,
            )
            lookback_days = cap

        # Calculate start date from lookback_days
        start_date = end_date - timedelta(days=lookback_days)
        start_ts, end_ts = get_range_timestamps(str(start_date), str(end_date))

        url = (
            f"https://query2.finance.yahoo.com/v8/finance/chart/{asset}?"
            f"period1={start_ts}&period2={end_ts}&interval={interval}&events=history"
        )
        if include_prepost:
            url += "&includePrePost=true"

        logger.info(
            "Fetching Yahoo intraday ticker %s interval=%s lookback_days=%s start_date=%s end_date=%s",
            asset,
            interval,
            lookback_days,
            start_date,
            end_date,
        )
        logger.debug(
            "Yahoo intraday request asset=%s start_ts=%s end_ts=%s url=%s",
            asset,
            start_ts,
            end_ts,
            url,
        )

    # Fetch
    try:
        if session is None:
            response = requests.get(url, headers=headers, timeout=timeout)
        else:
            response = session.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        logger.warning("Yahoo intraday request failed for %s: %s", asset, exc)
        return None
    except Exception:
        logger.exception("Unexpected Yahoo intraday request failure for %s", asset)
        return None

    if not response.ok:
        # Handle 422 (over-cap) specially
        if response.status_code == 422:
            try:
                error_payload = response.json()
                error_desc = error_payload.get("chart", {}).get("error", {}).get("description", "")
                if error_desc:
                    logger.warning(
                        "Yahoo 422 for %s interval=%s: %s",
                        asset,
                        interval,
                        error_desc,
                    )
                else:
                    logger.warning(
                        "Yahoo request returned 422 for %s interval=%s (no error description)",
                        asset,
                        interval,
                    )
            except (ValueError, KeyError, TypeError):
                logger.warning(
                    "Yahoo request returned 422 for %s interval=%s (could not parse error body)",
                    asset,
                    interval,
                )
        else:
            logger.warning(
                "Yahoo intraday request returned non-OK response for %s: status=%s body_hint=%s",
                asset,
                getattr(response, "status_code", "unknown"),
                _get_response_hint(response),
            )
        return None

    # Parse payload
    try:
        payload = response.json()
        result = payload["chart"]["result"][0]
        timestamp_list = result.get("timestamp", [])
        
        # Empty but 200 response (e.g., range=1d pre-open)
        if not timestamp_list:
            logger.warning(
                "Yahoo intraday returned empty result (no bars) for %s interval=%s",
                asset,
                interval,
            )
            return None

        quote = result["indicators"]["quote"][0]
        data = pd.DataFrame.from_dict(quote)
        data["Date"] = timestamp_list
        
        # Convert epoch seconds to datetime (UTC, then localize to exchange tz)
        data["Date"] = pd.to_datetime(data["Date"], unit="s", utc=True)
        
        # Get exchange timezone from response, fall back to NY
        exchange_tz = result.get("meta", {}).get("exchangeTimezoneName", "America/New_York")
        data["Date"] = data["Date"].dt.tz_convert(exchange_tz).dt.tz_localize(None)
        
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("Yahoo intraday payload parsing failed for %s: %s", asset, exc)
        return None
    except Exception:
        logger.exception("Unexpected Yahoo intraday payload parsing failure for %s", asset)
        return None

    # Finalize frame
    data = data.set_index("Date", drop=True)
    data.index.name = "Date"
    
    # Keep only OHLCV columns, round prices to 2dp, volume as int
    ohlcv_cols = [col for col in ["open", "high", "low", "close", "volume"] if col in data.columns]
    data = data[ohlcv_cols]
    
    # Round price columns; volume is int
    price_cols = [col for col in ["open", "high", "low", "close"] if col in data.columns]
    data[price_cols] = data[price_cols].round(2)
    if "volume" in data.columns:
        data["volume"] = data["volume"].astype("int64")
    
    result_data = data
    logger.info(
        "Successfully fetched Yahoo intraday ticker %s interval=%s rows=%s",
        asset,
        interval,
        len(result_data),
    )
    return result_data


def get_portfolio_intraday(
    assets,
    interval: str = "5m",
    *,
    lookback_days: Optional[int] = None,
    range_: Optional[str] = None,
    include_prepost: bool = False,
    field: str = "close",
    end_date=None,
    timeout: int = 10,
    max_workers: int = 10,
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
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

    Parameters
    ----------
    assets
        Iterable of ticker symbols.
    interval : str
        One of VALID_INTRADAY_INTERVALS. Default '5m'.
    lookback_days : Optional[int]
        How many days back to request. If None, defaults to the interval's cap.
        Values above the cap are clamped.
    range_ : Optional[str]
        Optional Yahoo 'range' value. When set, lookback_days is ignored.
    include_prepost : bool
        Include pre/after-hours bars. Default False.
    field : str
        'close' (default) for close-only wide matrix, 'ohlcv' for per-ticker frames.
    end_date
        Window end (datetime.date). Default today.
    timeout : int
        Per-request timeout seconds. Default 10.
    max_workers : int
        Max concurrent workers. Default 10.

    Returns
    -------
    Union[pd.DataFrame, Dict[str, pd.DataFrame]]
        If field='close': wide DataFrame with one close column per ticker.
        If field='ohlcv': dict mapping ticker -> OHLCV DataFrame.

    Raises
    ------
    ValueError
        If no valid assets found (all failed).
    """
    if end_date is None:
        end_date = dt.now().date()

    close_frames = []
    ohlcv_frames = {}
    not_found = []
    assets = list(assets)

    # Dedup assets while preserving order
    seen_assets = set()
    unique_assets = []
    for asset in assets:
        if asset not in seen_assets:
            unique_assets.append(asset)
            seen_assets.add(asset)

    logger.info(
        "Fetching Yahoo intraday portfolio for %s assets with interval=%s lookback_days=%s range=%s end_date=%s",
        len(unique_assets),
        interval,
        lookback_days,
        range_,
        end_date,
    )

    with _create_session() as session:
        futures = {}
        total = len(unique_assets)
        completed = 0
        worker_count = min(max_workers, total) if unique_assets else 1

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            for asset in unique_assets:
                futures[
                    executor.submit(
                        get_one_ticker_intraday,
                        asset,
                        interval,
                        lookback_days=lookback_days,
                        range_=range_,
                        include_prepost=include_prepost,
                        end_date=end_date,
                        session=session,
                        timeout=timeout,
                    )
                ] = asset

            for future in as_completed(futures):
                asset = futures[future]
                completed += 1
                percent = completed * 100.0 / total if total else 0.0
                logger.info(
                    "Yahoo intraday progress %s/%s (%.0f%%) for %s",
                    completed,
                    total,
                    percent,
                    asset,
                )

                try:
                    ticker_data = future.result()
                except Exception as exc:
                    logger.warning("Skipping %s: Yahoo intraday fetch failed (%s)", asset, exc)
                    not_found.append(asset)
                    continue

                if ticker_data is None:
                    logger.warning("Skipping %s: no intraday data returned from Yahoo fetch", asset)
                    not_found.append(asset)
                    continue

                if ticker_data.empty:
                    logger.warning("Skipping %s: Yahoo returned an empty intraday dataset", asset)
                    not_found.append(asset)
                    continue

                if field == "ohlcv":
                    ohlcv_frames[asset] = ticker_data
                elif field == "close":
                    if "close" not in ticker_data.columns:
                        logger.warning("Skipping %s: no close column in intraday data", asset)
                        not_found.append(asset)
                        continue
                    close_frame = ticker_data[["close"]].rename(columns={"close": asset})
                    close_frames.append(close_frame)
                else:
                    logger.warning("Skipping %s: invalid field=%s (must be 'close' or 'ohlcv')", asset, field)
                    not_found.append(asset)
                    continue

    if field == "ohlcv":
        if not ohlcv_frames:
            logger.error(
                "No valid assets found for Yahoo intraday portfolio request. requested_assets=%s failure_count=%s",
                assets,
                len(not_found),
            )
            raise ValueError("No valid assets found — portfolio is empty")
        logger.info("Not found assets: %s, %s", len(set(not_found)), sorted(set(not_found)))
        return ohlcv_frames

    elif field == "close":
        if not close_frames:
            logger.error(
                "No valid assets found for Yahoo intraday portfolio request. requested_assets=%s failure_count=%s",
                assets,
                len(not_found),
            )
            raise ValueError("No valid assets found — portfolio is empty")

        portfolio = pd.concat(close_frames, axis=1, join="outer")
        portfolio.index = pd.to_datetime(portfolio.index, errors="coerce")
        portfolio = portfolio[~portfolio.index.isna()]
        portfolio = portfolio[~portfolio.index.duplicated(keep="last")]
        portfolio.index.name = "Date"
        portfolio = portfolio.sort_index()
        portfolio = portfolio.round(2)

        logger.info("Not found assets: %s, %s", len(set(not_found)), sorted(set(not_found)))
        return portfolio
