import datetime
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import numpy as np
from earningspy.generators.finviz.constants import (
    PERCENTAJE_COLUMNS,
    MONEY_COLUMNS,
    NUMERIC_COLUMNS,
    FINVIZ_DROP_COLUMNS
)

FINVIZ_URL = "https://finviz.com/screener.ashx?v=152&f={}{}&o={}"


def round_half_up(value):
    if value is None or pd.isna(value):
        return np.nan
    return int(Decimal(str(value)).quantize(0, rounding=ROUND_HALF_UP))


def _process_money_value(value):
    if isinstance(value, np.float64):
        return value
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



def _format_percent(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan

    # Handle strings like "3%", " 3.5 % ", "-"
    if isinstance(value, str):
        value = value.strip()
        if value in {"", "-", "—"}:
            return np.nan
        value = value.replace("%", "")
        try:
            value = float(value)
        except ValueError:
            return np.nan

    # At this point value should be numeric
    try:
        value = float(value)
    except Exception:
        return np.nan

    # If value looks like a percentage (>1), convert to decimal
    if abs(value) > 1:
        value = value / 100

    return value


def _convert_percent_columns(data): 

    for col in PERCENTAJE_COLUMNS:
        try:
            data.loc[col] = data.loc[col].apply(_format_percent)
        except Exception as e:
            print('Unable to transform this column: {} - {} - {}'.format(col, e, e.__class__))
    return data


def _process_money_columns(df):

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


def _process_52_high_low(data, drop=False):
    
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


def _calculate_normalized_52w(row):
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
        print(f"Error processing 52W Range {range52}: {e}")
        return np.nan
    else:
        return np.round(normalized_indicator, 4)


def _process_index(row, index): 

    if isinstance(row['Index'], int):
        return row['Index']
    indexes = row['Index'].replace(' ', '').split(',')
    if index in indexes:
        return 1

    return 0


def _process_earnings_time(row, time):

    if isinstance(row['Earnings'], int):
        return row['Earnings']
    earnings_time = row['Earnings'].split('/')
    if earnings_time == ['-']:
        return np.nan
    try:
        earnings_time = earnings_time[1]
    except IndexError:
        return np.nan
    else:
        if earnings_time == time:
            return 1
        else:
            return 0


def _process_free_cash_flow(row):
    try:
        market_cap = row['Market Cap']
        pfcf = row['P/FCF']

        # Guard against invalid inputs
        if pd.isna(market_cap) or pd.isna(pfcf):
            return np.nan
        if pfcf == 0:
            return np.nan

        value = market_cap / pfcf

        # Catch inf / -inf / nan
        if not np.isfinite(value):
            return np.nan

        return round_half_up(value)

    except Exception:
        print("Error trying to compute FCF")
        return np.nan


def _process_ebitda(row):
    try:
        ev = row['Enterprise Value']
        ev_ebitda = row['EV/EBITDA']

        # Guard against invalid inputs
        if pd.isna(ev) or pd.isna(ev_ebitda):
            return np.nan
        if ev_ebitda == 0:
            return np.nan

        value = ev / ev_ebitda

        # Catch inf / -inf / nan
        if not np.isfinite(value):
            return np.nan

        return round_half_up(value)

    except Exception:
        print("Error trying to compute ebitda")
        return np.nan
    

def _process_ebit(row):
    try:
        oper_margin = row['Oper M']
        sales = row['Sales']
        if pd.isna(oper_margin) or pd.isna(sales) or sales == 0:
            return np.nan
        value = oper_margin * sales
        return round_half_up(value) if np.isfinite(value) else np.nan
    except KeyError:
        print("Error trying to compute ebitda")
        raise
    except Exception:
        print("Error trying to compute ebit")
        return np.nan
    

def _process_ex_dividend(row):

    value = row['Dividend Ex Date']
    if isinstance(value, datetime.date):
        return value
    if pd.isna(value):
        return np.nan
    if value.strip() == '-':
        return np.nan
    try:
        date = pd.to_datetime(value, format="%m/%d/%Y").date()
    except:
        return np.nan
    else:
        return date


def _process_yes_columns(row, col_name):

    if row[col_name] == 'Yes':
        return 1
    return 0


def _process_country(row):
    value = row['Country']
    try:
        if value.strip().lower() == 'usa':
            return 1
    except Exception:
        return np.nan
        
    return 0


def _process_volume(value):
    if isinstance(value, float):
        return value
    elif isinstance(value, str):
        if value == '-':
            return 0.0
        value = value.replace(',','')
        return float(value)
    else:
        return value


def _process_numeric_columns(data):
    for col in NUMERIC_COLUMNS:
        try:
            data.loc[col] = data.loc[col].apply(_process_volume)
        except Exception as e:
            print('Unable to transform this column: {} - {}'.format(col, e))
            data.loc[col] = np.nan
    return data


def _process_report_date(row): 
    value = row['Earnings']
    date_list = value.split('/')
    if len(date_list) == 1 and type(date_list[0]) == str and date_list[0] != '-':
        date = date_list[0] + f" {datetime.datetime.now().year}"
        date = pd.to_datetime(date, format='%b %d %Y')
    elif len(date_list) == 2:
        date = date_list[0].split(' ')
        date = date_list[0] + f" {datetime.datetime.now().year}"
        date = pd.to_datetime(date, format='%b %d %Y')
    else:
        date = np.nan
    return date


def _process_remaning_columns(data):

    data = data.T
    data.loc[:,'52W_NORM'] = data.apply(lambda row: _calculate_normalized_52w(row), axis=1)

    # Index data
    data.loc[:,'IS_S&P500'] = data.apply(lambda row: _process_index(row, index='S&P500'), axis=1)
    data.loc[:,'IS_RUSSELL'] = data.apply(lambda row: _process_index(row, index='RUT'), axis=1)
    data.loc[:,'IS_NASDAQ'] = data.apply(lambda row: _process_index(row, index='NDX'), axis=1)
    data.loc[:,'IS_DOW_JONES'] = data.apply(lambda row: _process_index(row, index='DJIA'), axis=1)

    # After Market close or Before Market Opens
    data.loc[:,'IS_AMC'] = data.apply(lambda row: _process_earnings_time(row, time='a'), axis=1)
    data.loc[:,'IS_BMO'] = data.apply(lambda row: _process_earnings_time(row, time='b'), axis=1)

    # Dividend data
    data.loc[:,'Dividend Ex Date'] = data.apply(lambda row: _process_ex_dividend(row), axis=1)

    # Options data
    data.loc[:,'Optionable'] = data.apply(lambda row: _process_yes_columns(row, col_name='Optionable'), axis=1)
    data.loc[:,'Shortable'] = data.apply(lambda row: _process_yes_columns(row, col_name='Shortable'), axis=1)

    # Is US company and earnings date
    data.loc[:,'IS_USA'] = data.apply(lambda row: _process_country(row), axis=1)
    data.loc[:,'EARNINGS_DATE'] = data.apply(lambda row: _process_report_date(row), axis=1)

    # Value investing data
    data.loc[:, 'FCF'] = data.apply(lambda row: _process_free_cash_flow(row), axis=1)
    data.loc[:, 'EBITDA'] = data.apply(lambda row: _process_ebitda(row), axis=1)
    data.loc[:, 'EBIT'] = data.apply(lambda row: _process_ebit(row), axis=1)

    # Data fetched on this date 
    data.loc[:, 'DATADATE'] = pd.to_datetime(datetime.datetime.now().date())

    return data.T


def finviz_data_preprocessor(df):
    
    df = _convert_percent_columns(df)
    df = _process_money_columns(df)
    df = _process_numeric_columns(df)
    df = _process_52_high_low(df)
    df = _process_remaning_columns(df)
    df = df.drop(FINVIZ_DROP_COLUMNS, axis=0, errors='ignore')

    df = df.infer_objects()

    return df.T
