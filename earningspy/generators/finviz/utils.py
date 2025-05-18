import datetime
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


def get_dataframe_by_tickers(tickers, order='marketcap'):
    tickers = ','.join(tickers)
    order = f"&o={order}"
    query = f'https://finviz.com/screener.ashx?t={tickers}' + CUSTOM_TABLE_FIELDS_ON_URL
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


def get_micro_caps_data(order='marketcap'):

    micro_caps_filter = 'cap_micro'
    data = _get_data_frame_with_custom_fields(micro_caps_filter, order=order)
    data.loc['Index'] = 'Micro'
    return data


def get_small_caps_data(order='marketcap'):
    
    small_caps_filter = 'cap_small'
    data = _get_data_frame_with_custom_fields(small_caps_filter, order=order)
    data.loc['Index'] = 'Small'
    return data


def get_medium_caps_data(order='marketcap'):

    medium_caps_filter = 'cap_mid'
    data = _get_data_frame_with_custom_fields(medium_caps_filter, order=order)
    data.loc['Index'] = 'Medium'
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

    if isinstance(value, float):
        return value
    elif isinstance(value, str):
        high_low = value.split(' - ')
        if high_low[1] == '-':
            return float(0.0)
        elif high_low[1] != '-':
            return float(high_low[1])
    return np.nan

def _process_52_low(value):
    if isinstance(value, float):
        return value
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

def calculate_normalized_52w(row):
    """Calculates the normalized indicator for price within a 52-week range."""

    if isinstance(row['52W Range'], float):
        return row['52W Range']

    range52 = row['52W Range'].split('-')
    if not len(range52):
        return np.nan
    try:
        low_52w, high_52w = range52
        low_52w, high_52w = float(low_52w.strip()), float(high_52w.strip())

        midpoint = (high_52w + low_52w) / 2
        range_width = high_52w - low_52w
        normalized_indicator = (row['Price'] - midpoint) / (range_width / 2)
    except Exception as e:
        print(f"Error processing 52W Range {row['52W Range']}: {e}")
        return np.nan
    else:
        return np.round(normalized_indicator, 4)

def process_ltdebt_eq(row):

    if isinstance(row['LTDebt/Eq'], float):
        return row['LTDebt/Eq']
    
    if isinstance(row['LTDebt/Eq'], str):
        if row['LTDebt/Eq'].strip() == '-':
            return np.nan
        try:
            value = float(row['LTDebt/Eq'])
        except:
            value = np.nan
    else:
        value = np.nan
    
    return value

def process_dividend(row, row_name):
    
    if isinstance(row[row_name], float):
        return row[row_name]
    dividend_yield = np.nan
    value = row[row_name].strip()
    if value == '-':
        return dividend_yield
    else:
        value = value.split(' ')
        if len(value[1]) > 1:
            dividend_yield = np.round(float(value[1].strip('(').strip(')').replace('%', '')) / 100, 4)

    return dividend_yield

def process_index(row, index): 

    if isinstance(row['Index'], int):
        return row['Index']
    indexes = row['Index'].replace(' ', '').split(',')
    if index in indexes:
        return 1

    return 0

def process_earnings_time(row, time):

    if isinstance(row['Earnings'], int):
        return row['Earnings']
    earnings_time = row['Earnings'].split(' ')
    if earnings_time == ['-']:
        return np.nan
    try:
        earnings_time = earnings_time[2]
    except IndexError:
        return np.nan
    else:
        if earnings_time == time:
            return 1
    return 0

def process_ex_dividend(row):

    value = row['Dividend Ex-Date']
    if isinstance(value, datetime.date):
        return value
    if pd.isna(value):
        return np.nan
    if value.strip() == '-':
        return np.nan
    try:
        date = pd.to_datetime(value, format='%b %d, %Y').date()
    except:
        return np.nan
    else:
        return date

def process_optionable_shortable(row, type_='option'): 
    value = row['Option/Short']
    if isinstance(value, int):
        return value
    if value.strip() == '-':
        return np.nan
    value = value.split(" / ")
    if len(value) <= 1:
        return np.nan
    if value[0] == "Yes" and type_ == 'option':
        return 1
    elif value[1] == "Yes" and type_ == 'short':
        return 1
    return 0


def process_volatility_range(row):
    value = row['Volatility']
    if value == '-':
        return np.nan
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    value = value.split(' ')
    if len(value) != 2:
        return np.nan
    try:
        range_ = [float(v.replace('%', '')) / 100 for v in value]
    except ValueError as e:
        # print(f"Error processing Volatility Range {value}: {e}")
        return np.nan
    return range_[0] - range_[1]


def process_country(row):
    value = row['Country']
    try:
        if value.strip().lower() == 'usa':
            return 1
    except Exception:
        return np.nan
        
    return 0

def process_remaning_columns(data):

    data = data.T
    data.loc[:,'52W_NORM'] = data.apply(lambda row: calculate_normalized_52w(row), axis=1)
    data.loc[:,'LTDEBT/EQ'] = data.apply(lambda row: process_ltdebt_eq(row), axis=1)
    data.loc[:,'DIVIDEND_YIELD_EST'] = data.apply(lambda row: process_dividend(row, row_name='Dividend Est.'), axis=1)
    data.loc[:,'DIVIDEND_YIELD_TTM'] = data.apply(lambda row: process_dividend(row, row_name='Dividend TTM'), axis=1)
    data.loc[:,'IS_S&P500'] = data.apply(lambda row: process_index(row, index='S&P500'), axis=1)
    data.loc[:,'IS_RUSSELL'] = data.apply(lambda row: process_index(row, index='RUT'), axis=1)
    data.loc[:,'IS_NASDAQ'] = data.apply(lambda row: process_index(row, index='NDX'), axis=1)
    data.loc[:,'IS_AMC'] = data.apply(lambda row: process_earnings_time(row, time='AMC'), axis=1)
    data.loc[:,'IS_BMO'] = data.apply(lambda row: process_earnings_time(row, time='BMO'), axis=1)
    data.loc[:,'DIVIDEND_EX-DATE'] = data.apply(lambda row: process_ex_dividend(row), axis=1)
    data.loc[:,'IS_OPTIONABLE'] = data.apply(lambda row: process_optionable_shortable(row, type_='option'), axis=1)
    data.loc[:,'IS_SHORTABLE'] = data.apply(lambda row: process_optionable_shortable(row, type_='short'), axis=1)
    data.loc[:,'VOLATILITY_RANGE'] = data.apply(lambda row: process_volatility_range(row), axis=1)
    data.loc[:,'IS_USA'] = data.apply(lambda row: process_country(row), axis=1)

    return data.T


def _process_dataframe(df):
    
    df = convert_percent_columns(df)
    df = process_money_columns(df)
    df = process_numeric_columns(df)
    df = process_52_high_low(df)
    df = process_report_date(df)
    df = process_remaning_columns(df)

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
