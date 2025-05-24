import pandas as pd
from earningspy.generators.finviz.screener import Screener
from pprint import pprint as pp
from earningspy.generators.finviz.constants import (
    CUSTOM_TABLE_ALL_FIELDS_NEW,    
    CUSTOM_TABLE_FIELDS_ON_URL,
    TICKER_KEY,
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
    # stock_list = stock_list.get_ticker_details()
    data = pd.DataFrame(index=CUSTOM_TABLE_ALL_FIELDS_NEW)
    for stock in stock_list:
        ticker = stock.get(TICKER_KEY)
        ticker_data = pd.DataFrame(index=CUSTOM_TABLE_ALL_FIELDS_NEW)
        for key, value in stock.items():
            if key in CUSTOM_TABLE_ALL_FIELDS_NEW:
                ticker_data.loc[key, ticker] = value
        data = pd.concat([data, ticker_data], axis=1)
    return finviz_data_preprocessor(data)
    # return stock_list


def get_by_tickers(tickers, order='marketcap'):
    tickers = ','.join(tickers)
    ticker_query = f'https://finviz.com/screener.ashx?t={tickers}' + CUSTOM_TABLE_FIELDS_ON_URL + f"&o={order}"
    return _get_screener_data(ticker_query)


def get_by_industry(industry=None):

    filters = get_filters('Industry').get(industry)
    if not filters:
        raise Exception("Unable to get Industry: Invalid industry code")

    return _get_screener_data(filters)


def get_micro_caps():

    micro_caps_filter = 'cap_micro'
    data = _get_screener_data(micro_caps_filter)
    data.loc['Index'] = 'Micro'
    return data


def get_small_caps():
    
    small_caps_filter = 'cap_small'
    data = _get_screener_data(small_caps_filter)
    data.loc['Index'] = 'Small'
    return data


def get_medium_caps():

    medium_caps_filter = 'cap_mid'
    data = _get_screener_data(medium_caps_filter)
    data.loc['Index'] = 'Medium'
    return data


def get_by_index(index=None):
    filters = get_filters('Index').get(index)
    if not filters:
        raise Exception("Unable to get Index: Invalid index code")
    return _get_screener_data(filters)


def get_by_sector(sector=None, 
                            order='marketcap'):

    filters = get_filters('Sector').get(sector)
    if not filters:
        raise Exception("Unable to get sector: Invalid sector code")

    data = _get_screener_data(filters, order=order)
    return data


def get_by_exchange(exchange=None):
    filters = get_filters('Exchange').get(exchange)
    if not filters:
        raise Exception("Unable to get exchange: Invalid exchange code")
    return _get_screener_data(filters)
