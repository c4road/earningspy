import datetime
import logging
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import numpy as np
from earningspy.generators.finviz.constants import (
    PERCENTAJE_COLUMNS,
    MONEY_COLUMNS,
    NUMERIC_COLUMNS,
    FINVIZ_DROP_COLUMNS,
    FINVIZ_COLUMN_RENAMES,
)

logger = logging.getLogger(__name__)

FINVIZ_URL = "https://finviz.com/screener.ashx?v=152&f={}{}&o={}"


def round_half_up(value):
    """
    Round a numeric value to the nearest integer using half-up rounding.

    This function uses the Decimal module to ensure accurate rounding behavior,
    particularly for financial calculations where precision is important.

    Args:
        value: Numeric value to round. Can be None, NaN, or any numeric type.

    Returns:
        int: Rounded integer value, or np.nan if input is None or NaN.

    Examples:
        >>> round_half_up(3.5)
        4
        >>> round_half_up(3.4)
        3
        >>> round_half_up(None)
        nan
    """
    if value is None or pd.isna(value):
        return np.nan
    return int(Decimal(str(value)).quantize(0, rounding=ROUND_HALF_UP))


def _process_money_value(value):
    """
    Process monetary values from Finviz, converting abbreviated formats to full numeric values.

    Handles various formats including:
    - Raw numeric values (int, float, np.float64)
    - Abbreviated values with suffixes: 'B' (billions), 'M' (millions), 'K' (thousands)
    - Dash '-' indicating zero or missing value

    Args:
        value: The monetary value to process. Can be numeric, string, or None.

    Returns:
        float: Processed numeric value, or original value if already numeric.

    Examples:
        >>> _process_money_value("1.5B")
        1500000000.0
        >>> _process_money_value("500M")
        500000000.0
        >>> _process_money_value("10K")
        10000.0
        >>> _process_money_value("-")
        0.0
    """
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
    """
    Format and normalize percentage values from Finviz data.

    Handles various input formats:
    - String percentages like "3%", " 3.5 % "
    - Raw numeric values
    - Missing values indicated by "-", "—", or empty strings
    - Converts percentages > 1 to decimal form (e.g., 50% -> 0.5)

    Args:
        value: The percentage value to format. Can be string, numeric, or None.

    Returns:
        float: Normalized percentage as decimal (0.0-1.0 range), or np.nan for invalid inputs.

    Examples:
        >>> _format_percent("50%")
        0.5
        >>> _format_percent("3.5")
        0.035
        >>> _format_percent("-")
        nan
    """
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
    """
    Convert all percentage columns in the dataset to normalized decimal format.

    Iterates through all columns defined in PERCENTAJE_COLUMNS and applies
    percentage formatting to each value in those columns.

    Args:
        data (pd.DataFrame): DataFrame containing Finviz data with percentage columns.

    Returns:
        pd.DataFrame: DataFrame with percentage columns converted to decimal format.

    Note:
        Any columns that cannot be processed will be logged as warnings but won't
        stop the processing of other columns.
    """
    for col in PERCENTAJE_COLUMNS:
        try:
            data.loc[col] = data.loc[col].apply(_format_percent)
        except Exception as e:
            logger.warning(f'Unable to transform percentage column: {col} - {e} - {type(e).__name__}')
    return data


def _process_money_columns(df):
    """
    Process all monetary columns in the DataFrame, converting abbreviated values.

    Iterates through all columns defined in MONEY_COLUMNS and applies
    monetary value processing to convert abbreviations (B, M, K) to full numeric values.

    Args:
        df (pd.DataFrame): DataFrame containing Finviz data with monetary columns.

    Returns:
        pd.DataFrame: DataFrame with monetary columns converted to full numeric values.
    """
    for col in MONEY_COLUMNS:
        if col in df.index:
            df.loc[col] = df.loc[col].apply(_process_money_value)

    return df


def _process_52_high(value):
    """
    Extract the 52-week high value from a range string.

    Parses a 52-week range string in format "low - high" and returns the high value.

    Args:
        value: The 52-week range value. Can be float (already processed) or string.

    Returns:
        float: The 52-week high value, or 0.0 if high is "-", or np.nan for invalid input.

    Examples:
        >>> _process_52_high("10.5 - 15.2")
        15.2
        >>> _process_52_high("10.5 - -")
        0.0
    """
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
    """
    Extract the 52-week low value from a range string.

    Parses a 52-week range string in format "low - high" and returns the low value.

    Args:
        value: The 52-week range value. Can be float (already processed) or string.

    Returns:
        float: The 52-week low value, or 0.0 if low is "-", or np.nan for invalid input.

    Examples:
        >>> _process_52_low("10.5 - 15.2")
        10.5
        >>> _process_52_low("- - 15.2")
        0.0
    """
    if isinstance(value, float):
        return value
    high_low = value.split(' - ')
    if high_low[0] == '-':
        return float(0.0)
    elif high_low[0] != '-':
        return float(high_low[0])
    return np.nan


def _process_52_high_low(data, drop=False):
    """
    Process 52-week range data by splitting into separate high and low columns.

    Takes the '52W Range' column and creates '52W Low' and '52W High' columns.
    Optionally drops the original '52W Range' column.

    Args:
        data (pd.DataFrame): DataFrame containing the '52W Range' column.
        drop (bool): Whether to drop the original '52W Range' column after processing.

    Returns:
        pd.DataFrame: DataFrame with added '52W Low' and '52W High' columns.
    """
    col_name = '52W Range'
    low_col_name = '52W Low'
    high_col_name = '52W High'

    if not col_name in data.index:
        logger.warning('No 52W Range field found in data')
        return data

    data.loc[low_col_name] = data.loc[col_name].apply(_process_52_low)
    data.loc[high_col_name] = data.loc[col_name].apply(_process_52_high)
    if drop:
        data.drop(col_name, inplace=True)

    return data


def _calculate_normalized_52w(row):
    """
    Calculate the normalized indicator for price within a 52-week range.

    Computes where the current price falls within the 52-week range on a scale
    from -1 to 1, where -1 is at the low, 0 is at the midpoint, and 1 is at the high.

    Args:
        row (pd.Series): DataFrame row containing '52W Range' and 'Price' columns.

    Returns:
        float: Normalized position within the 52-week range (-1 to 1), or np.nan for invalid data.

    Note:
        Formula: (price - midpoint) / (range_width / 2)
        Where midpoint = (high + low) / 2 and range_width = high - low
    """
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
        logger.warning(f"Error processing 52W Range {range52}: {e}")
        return np.nan
    else:
        return np.round(normalized_indicator, 4)


def _process_index(row, index):
    """
    Check if a stock belongs to a specific market index.

    Parses the 'Index' column which contains comma-separated index codes
    and checks if the specified index is present.

    Args:
        row (pd.Series): DataFrame row containing the 'Index' column.
        index (str): Index code to check for (e.g., 'S&P500', 'RUT', 'NDX', 'DJIA').

    Returns:
        int: 1 if the stock belongs to the specified index, 0 otherwise.

    Examples:
        >>> row = pd.Series({'Index': 'S&P500,RUT'})
        >>> _process_index(row, 'S&P500')
        1
        >>> _process_index(row, 'NDX')
        0
    """
    if isinstance(row['Index'], int):
        return row['Index']
    indexes = row['Index'].replace(' ', '').split(',')
    if index in indexes:
        return 1

    return 0


def _process_earnings_time(row, time):
    """
    Check if earnings are reported at a specific time (AMC/BMO).

    Parses the 'Earnings' column to determine if earnings are reported
    After Market Close (AMC) or Before Market Opens (BMO).

    Args:
        row (pd.Series): DataFrame row containing the 'Earnings' column.
        time (str): Time indicator to check ('a' for AMC, 'b' for BMO).

    Returns:
        int or float: 1 if earnings match the specified time, 0 if not, np.nan for missing data.

    Examples:
        >>> row = pd.Series({'Earnings': 'Jan 15/b'})
        >>> _process_earnings_time(row, 'b')
        1
        >>> _process_earnings_time(row, 'a')
        0
    """
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
    """
    Calculate Free Cash Flow (FCF) from market cap and P/FCF ratio.

    FCF is calculated as: Market Cap / P/FCF Ratio

    Args:
        row (pd.Series): DataFrame row containing 'Market Cap' and 'P/FCF' columns.

    Returns:
        float: Calculated Free Cash Flow value, or np.nan for invalid/missing data.

    Note:
        Returns np.nan if either input is missing, or if P/FCF is zero (division by zero).
        Also returns np.nan for infinite or NaN results.
    """
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
        logger.warning("Error trying to compute Free Cash Flow")
        return np.nan


def _process_ebitda(row):
    """
    Calculate EBITDA from Enterprise Value and EV/EBITDA ratio.

    EBITDA is calculated as: Enterprise Value / EV/EBITDA Ratio

    Args:
        row (pd.Series): DataFrame row containing 'Enterprise Value' and 'EV/EBITDA' columns.

    Returns:
        float: Calculated EBITDA value, or np.nan for invalid/missing data.

    Note:
        Returns np.nan if either input is missing, or if EV/EBITDA is zero (division by zero).
        Also returns np.nan for infinite or NaN results.
    """
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
        logger.warning("Error trying to compute EBITDA")
        return np.nan
    

def _process_ebit(row):
    """
    Calculate EBIT (Earnings Before Interest and Taxes) from operating margin and sales.

    EBIT is calculated as: Operating Margin × Sales

    Args:
        row (pd.Series): DataFrame row containing 'Oper M' (Operating Margin) and 'Sales' columns.

    Returns:
        float: Calculated EBIT value, or np.nan for invalid/missing data.

    Note:
        Returns np.nan if either input is missing or if Sales is zero.
        Also returns np.nan for infinite or NaN results.
    """
    try:
        oper_margin = row['Oper M']
        sales = row['Sales']
        if pd.isna(oper_margin) or pd.isna(sales) or sales == 0:
            return np.nan
        value = oper_margin * sales
        return round_half_up(value) if np.isfinite(value) else np.nan
    except KeyError:
        logger.error("Error trying to compute EBIT: missing required columns")
        raise
    except Exception:
        logger.warning("Error trying to compute EBIT")
        return np.nan
    

def _process_ex_dividend(row):
    """
    Process ex-dividend date from string format to datetime.date.

    Converts Finviz ex-dividend date strings (format: "MM/DD/YYYY") to datetime.date objects.

    Args:
        row (pd.Series): DataFrame row containing 'Dividend Ex Date' column.

    Returns:
        datetime.date or np.nan: Parsed ex-dividend date, or np.nan for missing/invalid data.

    Examples:
        >>> row = pd.Series({'Dividend Ex Date': '01/15/2023'})
        >>> _process_ex_dividend(row)
        datetime.date(2023, 1, 15)
    """
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
    """
    Convert "Yes" values to binary indicators.

    Converts Finviz "Yes" string values to 1, everything else to 0.
    Used for columns like 'Optionable' and 'Shortable'.

    Args:
        row (pd.Series): DataFrame row containing the column to process.
        col_name (str): Name of the column to check for "Yes" values.

    Returns:
        int: 1 if the value is "Yes", 0 otherwise.

    Examples:
        >>> row = pd.Series({'Optionable': 'Yes'})
        >>> _process_yes_columns(row, 'Optionable')
        1
        >>> row = pd.Series({'Optionable': 'No'})
        >>> _process_yes_columns(row, 'Optionable')
        0
    """
    if row[col_name] == 'Yes':
        return 1
    return 0


def _process_country(row):
    """
    Check if a company is based in the USA.

    Converts country names to a binary indicator where USA = 1, others = 0.

    Args:
        row (pd.Series): DataFrame row containing the 'Country' column.

    Returns:
        int or np.nan: 1 for USA-based companies, 0 for others, np.nan for invalid data.

    Examples:
        >>> row = pd.Series({'Country': 'USA'})
        >>> _process_country(row)
        1
        >>> row = pd.Series({'Country': 'Canada'})
        >>> _process_country(row)
        0
    """
    value = row['Country']
    try:
        if value.strip().lower() == 'usa':
            return 1
    except Exception:
        return np.nan

    return 0


def _process_volume(value):
    """
    Process volume values, converting formatted strings to numeric values.

    Handles volume values that may include commas as thousands separators,
    and converts "-" to 0 for missing volume data.

    Args:
        value: The volume value to process. Can be float, string, or other numeric.

    Returns:
        float: Processed volume value, or original value if already numeric.

    Examples:
        >>> _process_volume("1,234,567")
        1234567.0
        >>> _process_volume("-")
        0.0
        >>> _process_volume(1234567)
        1234567
    """
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
    """
    Process all numeric columns in the dataset.

    Applies volume processing to all columns defined in NUMERIC_COLUMNS,
    then renames columns according to FINVIZ_COLUMN_RENAMES mapping.

    Args:
        data (pd.DataFrame): DataFrame containing Finviz data with numeric columns.

    Returns:
        pd.DataFrame: DataFrame with processed numeric columns and renamed columns.

    Note:
        Columns that cannot be processed will be set to np.nan and logged as warnings.
    """
    for col in NUMERIC_COLUMNS:
        try:
            data.loc[col] = data.loc[col].apply(_process_volume)
        except Exception as e:
            logger.warning(f'Unable to transform numeric column: {col} - {e}')
            data.loc[col] = np.nan
    data = data.rename(index=FINVIZ_COLUMN_RENAMES)
    return data


def _process_report_date(row):
    """
    Process earnings report date from Finviz format to datetime.

    Parses various Finviz earnings date formats and converts them to datetime objects.
    Handles formats like "Jan 15" (adds current year) and "Jan 15 2023".

    Args:
        row (pd.Series): DataFrame row containing the 'Earnings' column.

    Returns:
        datetime or np.nan: Parsed earnings date, or np.nan for missing/invalid data.

    Examples:
        >>> row = pd.Series({'Earnings': 'Jan 15/a'})
        >>> _process_report_date(row)
        Timestamp('2023-01-15 00:00:00')  # with current year
    """
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
    """
    Process remaining columns that require complex transformations.

    This function handles various derived columns including:
    - 52-week normalized indicator
    - Index membership flags (S&P 500, Russell, NASDAQ, Dow Jones)
    - Earnings timing flags (AMC/BMO)
    - Dividend ex-date processing
    - Options and shorting availability flags
    - Country indicators (USA)
    - Earnings date processing
    - Financial calculations (FCF, EBITDA, EBIT)
    - Data timestamp

    Args:
        data (pd.DataFrame): DataFrame with processed basic columns.

    Returns:
        pd.DataFrame: DataFrame with all additional derived columns added.
    """
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
    """
    Main preprocessing pipeline for Finviz screener data.

    Applies a complete series of transformations to raw Finviz data:
    1. Convert percentage columns to decimal format
    2. Process monetary columns (B, M, K suffixes)
    3. Process numeric columns (volume, etc.)
    4. Split 52-week range into high/low columns
    5. Add derived columns (normalized indicators, index flags, etc.)
    6. Drop unnecessary columns
    7. Infer data types

    Args:
        df (pd.DataFrame): Raw DataFrame from Finviz screener data.

    Returns:
        pd.DataFrame: Fully processed DataFrame ready for analysis.

    Note:
        This function performs comprehensive data cleaning and feature engineering
        to prepare Finviz data for quantitative analysis and modeling.
    """
    df = _convert_percent_columns(df)
    df = _process_money_columns(df)
    df = _process_numeric_columns(df)
    df = _process_52_high_low(df)
    df = _process_remaning_columns(df)
    df = df.drop(FINVIZ_DROP_COLUMNS, axis=0, errors='ignore')

    df = df.infer_objects()

    return df.T
