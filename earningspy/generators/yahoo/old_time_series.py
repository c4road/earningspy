from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
import io
import requests
import pandas as pd
from tqdm import tqdm


HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) \
           AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'}

def get_range(range_from, end_date):

    accepted_values = ['3m', '9m', '1y', '5y', '10y']
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
    
    return start_date, end_date


def get_range_timestamps(start_date, end_date):

    residual_time = '13:33:13' # default yahoo time has 13 h 33 min 13 s
    start_date = f'{start_date} {residual_time}'
    start_date = str(dt.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        .timestamp()) \
        .replace('.0', '')

    end_date = f'{end_date} {residual_time}'
    end_date = str(dt.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        .timestamp()) \
        .replace('.0', '')

    return start_date, end_date


def get_portfolio_old_deprecated(assets, from_='3m', start_date=None, end_date=dt.now().date()):
    """
    Simulates clicking in the download button to download price history in yahoo finance
    deprecated since yahoo deleted the button and it is no longer a manual process 
    """
    if start_date:
        start, end = get_range_timestamps(start_date, end_date)
    else:
        start, end = get_range_timestamps(*get_range(range_from=from_, end_date=end_date))

    portfolio = pd.DataFrame()

    for i, asset in tqdm(enumerate(assets), total = len(assets)):
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{asset}?" \
            f"period1={start}&period2={end}&interval=1d&events=history"
        try:
            response = requests.get(url, headers=HEADERS)
        except Exception as e:
            raise 
        if response.ok:
            decoded_content = response.content.decode('utf-8')
            single_data = pd.read_csv(io.StringIO(decoded_content)).rename({'Adj Close': asset}, axis=1)
            if i == 0:
                portfolio = single_data[['Date', asset]]
                continue
            portfolio = pd.concat([portfolio, single_data[asset]], axis=1)
        else:
            print(response.text)
            raise Exception(f'Could not retrieve data:{response.status_code}')

    portfolio = portfolio.set_index('Date')
    portfolio.index = pd.to_datetime(portfolio.index)
    portfolio = portfolio.round(3)
    return portfolio
