import pandas as pd
from earningspy.generators.finviz.screener import Screener
from pprint import pprint as pp
from earningspy.generators.finviz.constants import (
    CUSTOM_TABLE_ALL_FIELDS_NEW,    
    CUSTOM_TABLE_FIELDS_ON_URL,
    TICKER_KEY,
    VALID_SCOPES_EARNING_SCOPES
)
from earningspy.generators.finviz.utils import finviz_data_preprocessor


FINVIZ_URL = "https://finviz.com/screener.ashx?v=152&f={}{}&o={}"


def get_filters(sub_category=None, raw=False):
    filters = Screener.load_filter_dict()
    if raw:
        pp(Screener.load_filter_dict())
        return
    if not sub_category:
        for category in Screener.load_filter_dict().keys():
            print(f'{category}')
        return
    return filters.get(sub_category)


def _get_screener_data(filters=None, order='marketcap', query=None):

    if not query:
        query = FINVIZ_URL.format(filters, CUSTOM_TABLE_FIELDS_ON_URL, order)

    stock_list = Screener.init_from_url(query)
    data = pd.DataFrame(index=CUSTOM_TABLE_ALL_FIELDS_NEW)
    for stock in stock_list:
        ticker = stock.get(TICKER_KEY)
        ticker_data = pd.DataFrame(index=CUSTOM_TABLE_ALL_FIELDS_NEW)
        for key, value in stock.items():
            if key in CUSTOM_TABLE_ALL_FIELDS_NEW:
                ticker_data.loc[key, ticker] = value
        data = pd.concat([data, ticker_data], axis=1)
    return finviz_data_preprocessor(data)


def get_by_earnings_date(scope):
    if scope not in VALID_SCOPES_EARNING_SCOPES:
        raise Exception(f"Invalid scope. Use {VALID_SCOPES_EARNING_SCOPES} instead")
    
    if scope == 'last_week':
        filters = 'earningsdate_prevweek'
    elif scope == 'this_week':
        filters = 'earningsdate_thisweek'
    elif scope == 'next_week':
        filters = 'earningsdate_nextweek'
    elif scope == 'today_bmo':
        filters = 'earningsdate_todaybefore'
    elif scope == 'yesterday_amc':
        filters = 'earningsdate_yesterdayafter'
    elif scope == 'today':
        filters = 'earningsdate_today'
    elif scope == 'this_month':
        filters = 'earningsdate_thismonth'

    return _get_screener_data(filters)


def get_by_tickers(tickers, order='marketcap'):
    tickers = ','.join(tickers)
    ticker_query = f'https://finviz.com/screener.ashx?t={tickers}' + CUSTOM_TABLE_FIELDS_ON_URL + f"&o={order}"
    return _get_screener_data(query=ticker_query)
