from earningspy.generators.finviz.screener import Screener
import pandas as pd
from pprint import pprint as pp
import numpy as np
from earningspy.generators.finviz.constants import (
    PERFORMANCE_TABLE_ALL_FIELDS,
    CUSTOM_TABLE_ALL_FIELDS,
    CUSTOM_TABLE_FIELDS_ON_URL,
    PERCENTAJE_COLUMNS,
    MONEY_COLUMNS,
    NUMERIC_COLUMNS,
    BOOLEAN_COLUMNS
)

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


def _get_dataframe(filters, table, order, details):
    stock_list = Screener(filters=[filters], table=table, order=order)
    if details:
        stock_list = stock_list.get_ticker_details()
    data = pd.DataFrame(index=PERFORMANCE_TABLE_ALL_FIELDS)
    for stock in stock_list:
        ticker = stock.get('Ticker')
        ticker_data = pd.DataFrame(index=CUSTOM_TABLE_ALL_FIELDS)
        for key, value in stock.items():
            if key in PERFORMANCE_TABLE_ALL_FIELDS:
                ticker_data.loc[key, ticker] = value
        data = pd.concat([data, ticker_data], axis=1)
    return _process_dataframe(data)

def _get_data_frame_with_custom_fields(filters, order):
    
    order = f"&o={order}"
    query = f"https://finviz.com/screener.ashx?v=152&f={filters}" + CUSTOM_TABLE_FIELDS_ON_URL + order
    stock_list = Screener.init_from_url(query)
    stock_list = stock_list.get_ticker_details()
    data = pd.DataFrame(index=CUSTOM_TABLE_ALL_FIELDS)
    for stock in stock_list:
        ticker = stock.get('Ticker')
        ticker_data = pd.DataFrame(index=CUSTOM_TABLE_ALL_FIELDS)
        for key, value in stock.items():
            if key in CUSTOM_TABLE_ALL_FIELDS:
                ticker_data.loc[key, ticker] = value
        data = pd.concat([data, ticker_data], axis=1)
    return _process_dataframe(data)

def get_dataframe_by_industry(industry=None, 
                              table='Performance', 
                              order='marketcap', 
                              details=True):
    if not industry:
        pp(get_filters('Industry'))
        return
    filters = get_filters('Industry').get(industry)
    if not filters:
        raise Exception("Unable to get Industry: Invalid industry code")
    if table == 'Custom':
        data = _get_data_frame_with_custom_fields(filters, order=order)
    else:
        print("the table is not custom")
        data = _get_dataframe(filters, table=table, order=order, details=details)
        data.loc['Industry'] = industry
    return data

def get_dataframe_by_index(index=None, 
                           table='Performance', 
                           order='marketcap', 
                           details=True):
    if not index:
        pp(get_filters('Index'))
        return
    filters = get_filters('Index').get(index)
    if not filters:
        raise Exception("Unable to get Index: Invalid index code")
    if table == 'Custom':
        data = _get_data_frame_with_custom_fields(filters, order=order)
    else:
        data = _get_dataframe(filters, table=table, order=order, details=details)
        data.loc['Index'] = index
    return data

def get_dataframe_by_sector(sector=None, 
                            table='Performance', 
                            order='marketcap', 
                            details=True):
    if not sector:
        pp(get_filters('Sector'))
        return
    filters = get_filters('Sector').get(sector)
    if not filters:
        raise Exception("Unable to get sector: Invalid sector code")
    if table == 'Custom':
        data = _get_data_frame_with_custom_fields(filters, order=order)
    else:
        data = _get_dataframe(filters, table=table, order=order, details=details)
        data.loc['Sector'] = sector
    return data

def get_dataframe_by_exchange(exchange=None, table='Performance', order='marketcap', details=True):
    if not exchange:
        pp(get_filters('Exchange'))
        return
    filters = get_filters('Exchange').get(exchange)
    if not filters:
        raise Exception("Unable to get exchange: Invalid exchange code")
    return _get_dataframe(filters, table=table, order=order, details=details)

def _process_money_value(value):
    if type(value) == float:
        return value
    elif type(value) == int:
        return float(value)
    else:
        if value.endswith('B'):
            value = float(value.strip('B'))
            value = value * 1000000000
            return value
        elif value.endswith('M'):
            value = float(value.strip('M'))
            value = value * 1000000
            return value
        elif value.endswith('K'):
            value = float(value.strip('K'))
            value = value * 1000
            return value
        elif value == '-':
            return float(0.0)
        else:
            return value

def format_percent(percent):
    if isinstance(percent, str):
        if percent == '-':
            return 0.0
        try:
            percent = float(percent.strip('%'))
        except:
            percent = 0.0
    elif isinstance(percent, int) or isinstance(percent, float): 
        percent = float(percent)
    else:
        raise Exception('WARNING: Receiving weird type on percentaje: {}'.format(percent))
    
    return percent / 100

def convert_percent_columns(data): 

    for col in PERCENTAJE_COLUMNS:
        try:
            data.loc[col] = data.loc[col].apply(format_percent)
        except Exception as e:
            print('Unable to transform this column: {} - {} - {}'.format(col, e, e.__class__))
    return data

def process_money_columns(df):

    for col in MONEY_COLUMNS:
        if col in df.index:
            df.loc[col] = df.loc[col].apply(_process_money_value)
        
    return df

def _process_52_high(value):

    high_low = value.split(' - ')
    if high_low[1] == '-':
        return float(0.0)
    elif high_low[1] != '-':
        return float(high_low[1])
    return np.nan

def _process_52_low(value):
    high_low = value.split(' - ')
    if high_low[0] == '-':
        return float(0.0)
    elif high_low[0] != '-':
        return float(high_low[0])
    return np.nan
    
def process_52_high_low(data, drop=False):
    
    col_name = '52W Range'
    low_col_name = '52W Low'
    high_col_name = '52W High'
    
    if not col_name in data.index:
        print('No 52W Range field')
        return data 
    
    data.loc[low_col_name] = data.loc[col_name].apply(_process_52_low)
    data.loc[high_col_name] = data.loc[col_name].apply(_process_52_high)
    if drop:
        data.drop(col_name, inplace=True)
        
    return data


def _process_dataframe(df):
    
    df = convert_percent_columns(df)
    df = process_money_columns(df)
    df = process_numeric_columns(df)
    df = process_52_high_low(df)
    # df = process_boolean_columns(df)
    df = process_report_date(df)

    return df


def process_volume(value):
    if isinstance(value, float):
        return value
    elif isinstance(value, str):
        if value == '-':
            return 0.0
        value = value.replace(',','')
        return float(value)
    else:
        return value

def process_numeric_columns(data):
    for col in NUMERIC_COLUMNS:
        try:
            data.loc[col] = data.loc[col].apply(process_volume)
        except Exception as e:
            print('Unable to transform this column: {} - {}'.format(col, e))
    return data

def transform_booleans(value):
    
    if isinstance(value, str):
        if value == 'Yes':
            return 1
        elif value == 'No':
            return 0
        else:
            return np.nan
    else:
        return np.nan

def process_boolean_columns(data):

    for col in BOOLEAN_COLUMNS:
        try:
            data.loc[col] = data.loc[col].apply(transform_booleans)
        except Exception as e:
            print('Unable to transform this column: {} - {}'.format(col, e))
    return data


def _parse_earnings_time(value):
        
    if value == '-':
        return np.nan
    else:
        value = value.split()
        if len(value) == 3:
            return value[2]
    return np.nan


def process_report_date(data): 
    
    column_name = 'Earnings'
    new_column_name = 'Earnings Time'
    if column_name in data.index:
        data.loc[new_column_name] = data.loc[column_name].apply(_parse_earnings_time)
    
    return data
