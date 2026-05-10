import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime as dt
from time import sleep

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Fixing this problem: https://www.reddit.com/r/sheets/comments/1farvxr/broken_yahoo_finance_url/

logger = logging.getLogger(__name__)


def _get_response_hint(response, limit=200):
    response_text = str(getattr(response, 'text', '') or '').strip().replace('\n', ' ')
    if not response_text:
        return ''
    if len(response_text) > limit:
        return f"{response_text[:limit]}..."
    return response_text


def get_range(range_from, end_date):

    accepted_values = ['3m', '9m', '1y', '5y', '10y', '20y', '30y']
    if range_from not in accepted_values:
        raise Exception('Invalid from value')

    if range_from == '3m':
        start_date = end_date - relativedelta(months=3)
    if range_from == '9m':
        start_date = end_date - relativedelta(months=9)
    if range_from == '1y':
        start_date = end_date - relativedelta(years=1)
    if range_from == '5y':
        start_date = end_date - relativedelta(years=5)
    if range_from == '10y':
        start_date = end_date - relativedelta(years=10)
    if range_from == '20y':
        start_date = end_date - relativedelta(years=20)
    if range_from == '30y':
        start_date = end_date - relativedelta(years=30)

    return str(start_date), str(end_date)


def get_range_timestamps(start_date, end_date):

    start_date = str(dt.strptime(start_date, "%Y-%m-%d")
        .timestamp()) \
        .replace('.0', '')

    end_date = str(dt.strptime(end_date, "%Y-%m-%d")
        .timestamp()) \
        .replace('.0', '')

    return start_date, end_date


def _normalize_close_frame(close_data, asset):
    if close_data.index.name != 'Date':
        close_data.index.name = 'Date'

    if asset not in close_data.columns:
        raise KeyError(asset)

    close_frame = close_data[[asset]].copy()
    close_frame.index = pd.to_datetime(close_frame.index, errors='coerce')
    close_frame = close_frame[~close_frame.index.isna()]
    close_frame = close_frame[~close_frame.index.duplicated(keep='last')]
    close_frame.index.name = 'Date'
    return close_frame


def _finalize_portfolio(close_frames):
    portfolio = pd.concat(close_frames, axis=1, join='outer')
    portfolio.index = pd.to_datetime(portfolio.index, errors='coerce')
    portfolio = portfolio[~portfolio.index.isna()]
    portfolio = portfolio[~portfolio.index.duplicated(keep='last')]
    portfolio.index.name = 'Date'
    portfolio = portfolio.sort_index()
    return portfolio.round(3)


def _get_retry_strategy(total=3, backoff_factor=0.3, status_forcelist=None):
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]

    retry_kwargs = {
        'total': total,
        'backoff_factor': backoff_factor,
        'status_forcelist': status_forcelist,
        'raise_on_status': False,
        'raise_on_redirect': False,
    }

    try:
        retry_kwargs['allowed_methods'] = frozenset(['GET'])
    except TypeError:
        retry_kwargs['method_whitelist'] = frozenset(['GET'])

    return Retry(**retry_kwargs)


def _create_session():
    session = requests.Session()
    retry_strategy = _get_retry_strategy()
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=20)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def _fetch_ticker_data(session, asset, from_='3m', start_date=None, end_date=dt.now().date(), timeout=10):
    headers = {
        'User-Agent': "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; .NET CLR 1.0.3705;)",
    }

    if start_date:
        end_date = str(end_date)
        start, end = get_range_timestamps(start_date, end_date)
    else:
        start, end = get_range(range_from=from_, end_date=end_date)
        start, end = get_range_timestamps(start, end)

    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{asset}?" \
          f"period1={start}&period2={end}&interval=1d&events=history"

    logger.info(
        "Fetching Yahoo ticker %s from_=%s start_date=%s end_date=%s",
        asset,
        from_,
        start_date,
        end_date,
    )
    logger.debug(
        "Yahoo request asset=%s start_ts=%s end_ts=%s url=%s",
        asset,
        start,
        end,
        url,
    )

    try:
        if session is None:
            response = requests.get(url, headers=headers, timeout=timeout)
        else:
            response = session.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        logger.warning("Yahoo request failed for %s: %s", asset, exc)
        return asset, None
    except Exception:
        logger.exception("Unexpected Yahoo request failure for %s", asset)
        return asset, None

    if not response.ok:
        logger.warning(
            "Yahoo request returned non-OK response for %s: status=%s body_hint=%s",
            asset,
            getattr(response, 'status_code', 'unknown'),
            _get_response_hint(response),
        )
        return asset, None

    try:
        payload = response.json()
        result = payload['chart']['result'][0]
        data = pd.DataFrame.from_dict(result['indicators']['quote'][0])
        data['Date'] = result['timestamp']
        data['Date'] = data['Date'].apply(dt.fromtimestamp)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("Yahoo payload parsing failed for %s: %s", asset, exc)
        return asset, None
    except Exception:
        logger.exception("Unexpected Yahoo payload parsing failure for %s", asset)
        return asset, None

    data = data.set_index('Date', drop=True)
    data.index = data.index.normalize()
    data.index.name = 'Date'

    result_data = data.round(2)
    logger.info(
        "Successfully fetched Yahoo ticker %s rows=%s",
        asset,
        len(result_data),
    )
    return asset, result_data


def get_portfolio(assets, from_='3m', start_date=None, end_date=dt.now().date(), timeout=10, max_workers=10):
    close_frames = []
    not_found = []
    assets = list(assets)
    seen_assets = set()
    unique_assets = []

    for asset in assets:
        if asset not in seen_assets:
            unique_assets.append(asset)
            seen_assets.add(asset)

    logger.info(
        "Fetching Yahoo portfolio for %s assets with from_=%s start_date=%s end_date=%s",
        len(unique_assets),
        from_,
        start_date,
        end_date,
    )

    with _create_session() as session:
        futures = {}
        total = len(unique_assets)
        completed = 0
        worker_count = min(max_workers, total) if unique_assets else 1
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            for asset in unique_assets:
                futures[executor.submit(get_one_ticker, asset, from_, start_date, end_date, session, timeout)] = asset

            for future in as_completed(futures):
                asset = futures[future]
                completed += 1
                percent = completed * 100.0 / total if total else 0.0
                logger.info(
                    "Yahoo progress %s/%s (%.0f%%) for %s",
                    completed,
                    total,
                    percent,
                    asset,
                )
                try:
                    ticker_data = future.result()
                except Exception as exc:
                    logger.warning("Skipping %s: Yahoo fetch failed (%s)", asset, exc)
                    not_found.append(asset)
                    continue

                if ticker_data is None:
                    logger.warning("Skipping %s: no data returned from Yahoo fetch", asset)
                    not_found.append(asset)
                    continue

                if ticker_data.empty:
                    logger.warning("Skipping %s: Yahoo returned an empty dataset", asset)
                    not_found.append(asset)
                    continue

                try:
                    close_data = prepare_data(ticker_data, asset)
                except (KeyError, TypeError, ValueError) as exc:
                    logger.warning("Skipping %s: could not prepare ticker data (%s)", asset, exc)
                    not_found.append(asset)
                    continue

                try:
                    close_frame = _normalize_close_frame(close_data, asset)
                except (KeyError, TypeError, ValueError) as exc:
                    logger.warning("Skipping %s: malformed data after preparation (%s)", asset, exc)
                    not_found.append(asset)
                    continue
                except Exception:
                    logger.exception("Skipping %s: could not normalize prepared data", asset)
                    not_found.append(asset)
                    continue

                if close_frame.empty:
                    logger.warning("Skipping %s: malformed data after preparation", asset)
                    not_found.append(asset)
                    continue

                close_frames.append(close_frame)

    if not close_frames:
        logger.error(
            "No valid assets found for Yahoo portfolio request. requested_assets=%s failure_count=%s",
            assets,
            len(not_found),
        )
        raise ValueError("No valid assets found — portfolio is empty")

    portfolio = _finalize_portfolio(close_frames)
    logger.info("Not found assets: %s, %s", len(set(not_found)), sorted(set(not_found)))
    return portfolio


def get_one_ticker(asset, from_='3m', start_date=None, end_date=dt.now().date(), session=None, timeout=10):
    _, data = _fetch_ticker_data(session, asset, from_, start_date, end_date, timeout)
    return data


def prepare_data(data, ticker):
    data = data.drop(['open', 'high', 'low', 'volume'], axis=1)
    data = data.rename(columns={"close": ticker})
    return data.round(2)
