from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
import io
import requests
import pandas as pd
from tqdm import tqdm

# Fixing this problem: https://www.reddit.com/r/sheets/comments/1farvxr/broken_yahoo_finance_url/


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
    
    return str(start_date), str(end_date)


def get_range_timestamps(start_date, end_date):

    start_date = str(dt.strptime(start_date, "%Y-%m-%d")
        .timestamp()) \
        .replace('.0', '')

    end_date = str(dt.strptime(end_date, "%Y-%m-%d")
        .timestamp()) \
        .replace('.0', '')

    return start_date, end_date


def get_portfolio(assets, from_='3m', start_date=None, end_date=dt.now().date()):

    portfolio = pd.DataFrame()

    for i, asset in tqdm(enumerate(assets), total = len(assets)):
        ticker_data = get_one_ticker(asset, from_=from_, start_date=start_date, end_date=end_date)
        close_data = prepare_data(ticker_data, asset).reset_index()
        if i == 0:
            portfolio = close_data[['Date', asset]]
            continue
        portfolio = pd.concat([portfolio, close_data[asset]], axis=1)

    portfolio = portfolio.set_index('Date')
    portfolio.index = pd.to_datetime(portfolio.index)
    portfolio = portfolio.round(3)
    return portfolio


def get_one_ticker(asset, from_='3m', start_date=None, end_date=dt.now().date()):
    
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) \
           AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'}
    if start_date:
        end_date = str(end_date)
        start, end = get_range_timestamps(start_date, end_date)
    else:
        start, end = get_range(range_from=from_, end_date=end_date)
        start, end = get_range_timestamps(start, end)

    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{asset}?" \
          f"period1={start}&period2={end}&interval=1d&events=history"
    
    try:
        response = requests.get(url, headers=headers)
    except Exception as e:
        raise 
    if response.ok:
        data = pd.DataFrame.from_dict(response.json()['chart']['result'][0]['indicators']['quote'][0])
        data['Date'] = response.json()['chart']['result'][0]['timestamp']
        data['Date'] = data['Date'].apply(dt.fromtimestamp)
        data = data.set_index('Date', drop=True)
        data.index = data.index.normalize()
        return data.round(2)
    else:
        print(response.text)
        raise Exception(f'Could not retrieve data:{response.status_code}')
    
def prepare_data(data, ticker):
    data = data.drop(['open', 'high', 'low', 'volume'], axis=1)
    data = data.rename(columns={"close": ticker})
    return data.round(2)
