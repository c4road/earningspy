LOCAL_EARNINGS_CALENDAR_FOLDER = './local_data'

DATA_FOLDER = '/Users/administrador/Documents/DataScience/Projects/Finviz/_Data'
FINVIZ_DATA_CALENDAR_FOLDER = '/FinvizDataCalendars'
FINVIZ_RAW_DATA_FOLDER = '/FinvizRawData'
# Example: (1, 3)  One day before, Three days after
DEFAULT_BEFORE_EARNINGS_DATE_DAYS=1
DEFAULT_AFTER_EARNINGS_DATE_DAYS=5
# Default ranges to calculate pct and diff (days_before, days_after)
RANGES = [(1, 3), (1, 30), (1, 60)]
DEFAULT_IF_ALPHA_WINDOW = 60

TICKER_KEY = 'Ticker'
TICKER_KEY_CAPITAL = 'TICKER'
COMPANY_KEY = 'Company'
COMPANY_KEY_CAPITAL = 'COMPANY'
DEFAULT_DATE_FORMAT="%Y-%m-%d"
DAYS_TO_EARNINGS_KEY_CAPITAL='DAYS_LEFT'
DAYS_TO_EARNINGS_KEY_BEFORE_FORMAT='days_left'
IS_ANOMALY_KEY = f"{RANGES[0][0]}-{RANGES[0][1]} pct"
IS_ALPHA_KEY = f"{RANGES[1][0]}-{RANGES[1][1]} pct"
IS_STRONG_KEY = "is_strong"
DEFAULT_DAYS_PRE_EARNINGS = 5

MARKET_DATA_TICKERS = ['^GSPC', '^TNX', '^RUT', '^VIX']
TBILL_10_YEAR = '^TNX'

ALPHAVANTAGE_EARNINGS_DATE_KEY = 'reportDate'
DAYS_TO_EARNINGS_KEY='days_left'  # in lower case betcause this is used before formatting
SYMBOL_KEY = 'symbol'

FINVIZ_EARNINGS_DATE_KEY = 'EARNINGS_DATE'
DAYS_LEFT_KEY = 'DAYS_LEFT'
ALLOWED_CAPITALIZATIONS = ['micro', 'small', 'medium']
