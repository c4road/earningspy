"""
Finviz Screener Data Module

This module provides functions to fetch stock screener data from Finviz.com.

Debug Logging Configuration:
To enable detailed debug logging for troubleshooting, configure logging before importing:

    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Enable debug for this module specifically
    logging.getLogger('earningspy.generators.finviz').setLevel(logging.DEBUG)

    # Now import and use
    from earningspy.generators.finviz.data import get_by_earnings_date
    result = get_by_earnings_date('next_week')

This will show detailed logs including:
- HTTP request/response details
- HTML parsing progress
- Selector matching results
- Any scraping issues or failures
"""

import logging
import warnings
import pandas as pd
from earningspy.generators.finviz.screener import Screener
from earningspy.generators.finviz.helper_functions.request_functions import _create_session
from pprint import pprint as pp
from earningspy.generators.finviz.constants import (
    CUSTOM_TABLE_ALL_FIELDS_NEW,
    CUSTOM_TABLE_FIELDS_ON_URL,
    TICKER_KEY,
    VALID_SCOPES_EARNING_SCOPES,
    FINVIZ_COLUMN_RENAMES,
)
from earningspy.generators.finviz.utils import finviz_data_preprocessor

logger = logging.getLogger(__name__)


FINVIZ_URL = "https://finviz.com/screener.ashx?v=152&f={}&{}&o={}"


def get_available_filters(filter_category=None, show_raw=False):
    """Get available filter options from Finviz screener.

    Args:
        filter_category: Specific category to show (e.g., 'technical', 'fundamental')
        show_raw: If True, pretty-print all filters

    Returns:
        Dict of filters for the category, or None if showing all categories
    """
    filters = Screener.load_filter_dict()
    if show_raw:
        pp(Screener.load_filter_dict())
        return
    if not filter_category:
        for category in Screener.load_filter_dict().keys():
            logger.info(f'{category}')
        return
    return filters.get(filter_category)


def _get_screener_data(filter_string=None, sort_column='marketcap', full_query_url=None, log_url=False):
    """Fetch screener data from Finviz with connection pooling and timeout.

    Args:
        filter_string: Filter string (e.g., 'earningsdate_nextweek')
        sort_column: Sort column (default 'marketcap')
        full_query_url: Full query URL (overrides filter_string+sort_column)
        log_url: Log the full Finviz URL

    Returns:
        DataFrame with screener results
    """
    if not full_query_url:
        filter_param = filter_string or ""
        custom_fields = CUSTOM_TABLE_FIELDS_ON_URL
        full_query_url = f"https://finviz.com/screener.ashx?v=152&f={filter_param}&{custom_fields}&o={sort_column}"

    if log_url:
        logger.info(f"Finviz query: {full_query_url}")

    logger.info(f"Fetching Finviz screener data (filters={filter_string}, order={sort_column})")
    
    session = _create_session()
    try:
        stock_list = Screener.init_from_url(full_query_url, session=session)
        logger.info(f"Fetched {len(stock_list)} stocks from Finviz")
    finally:
        session.close()
    
    data = pd.DataFrame(index=CUSTOM_TABLE_ALL_FIELDS_NEW)
    for stock in stock_list:
        ticker = stock.get(TICKER_KEY)
        ticker_data = pd.DataFrame(index=CUSTOM_TABLE_ALL_FIELDS_NEW)
        for key, value in stock.items():
            if key in CUSTOM_TABLE_ALL_FIELDS_NEW:
                ticker_data.loc[key, ticker] = value
        data = pd.concat([data, ticker_data], axis=1)

    missing = [col for col in CUSTOM_TABLE_ALL_FIELDS_NEW if data.loc[col].isna().all()]
    if missing:
        logger.warning(
            f"Finviz column mismatch detected. "
            f"The following columns are entirely NaN: {missing}. "
            f"Finviz may have renamed or removed them. "
            f"Check FINVIZ_COLUMN_RENAMES and update CUSTOM_TABLE_ALL_FIELDS_NEW."
        )

    return finviz_data_preprocessor(data)


def get_stocks_by_earnings_date(time_period, log_url=False):
    """Get stocks filtered by earnings date.

    Args:
        time_period: Time period for earnings ('last_week', 'this_week', 'next_week',
                    'today_bmo', 'yesterday_amc', 'today', 'this_month')
        log_url: Whether to log the full Finviz URL

    Returns:
        DataFrame with stocks matching the earnings date filter

    Raises:
        ValueError: If time_period is not valid
    """
    if time_period not in VALID_SCOPES_EARNING_SCOPES:
        raise ValueError(f"Invalid time_period '{time_period}'. Valid options: {VALID_SCOPES_EARNING_SCOPES}")

    # Map time periods to Finviz filter codes
    earnings_filters = {
        'last_week': 'earningsdate_prevweek',
        'this_week': 'earningsdate_thisweek',
        'next_week': 'earningsdate_nextweek',
        'today_bmo': 'earningsdate_todaybefore',
        'yesterday_amc': 'earningsdate_yesterdayafter',
        'today': 'earningsdate_today',
        'this_month': 'earningsdate_thismonth'
    }

    filter_code = earnings_filters[time_period]
    return _get_screener_data(filter_code, log_url=log_url)


def get_stocks_by_tickers(ticker_list, sort_column='marketcap'):
    """Get stock data for specific tickers.

    Args:
        ticker_list: List of ticker symbols (e.g., ['AAPL', 'GOOGL'])
        sort_column: Column to sort by (default 'marketcap')

    Returns:
        DataFrame with data for the specified tickers
    """
    ticker_string = ','.join(ticker_list)
    ticker_url = f'https://finviz.com/screener.ashx?t={ticker_string}&{CUSTOM_TABLE_FIELDS_ON_URL}&o={sort_column}'
    return _get_screener_data(full_query_url=ticker_url)


# Backward compatibility aliases
def get_filters(sub_category=None, raw=False):
    """Legacy function name - use get_available_filters instead."""
    return get_available_filters(sub_category, raw)


def get_by_earnings_date(scope, print_url=False):
    """Legacy function name - use get_stocks_by_earnings_date instead."""
    return get_stocks_by_earnings_date(scope, print_url)


def get_by_tickers(tickers, order='marketcap'):
    """Legacy function name - use get_stocks_by_tickers instead."""
    return get_stocks_by_tickers(tickers, order)
