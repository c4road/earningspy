from time import sleep
import requests
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
import pandas as pd
from tqdm import tqdm

# Fixing this problem: https://www.reddit.com/r/sheets/comments/1farvxr/broken_yahoo_finance_url/


def get_range(range_from, end_date):

    accepted_values = ['3m', '9m', '1y', '5y', '10y', '20y', '30y']
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
    if range_from == '20y':
        start_date = end_date - relativedelta(years=20)
    if range_from == '30y':
        start_date = end_date - relativedelta(years=30)

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
    portfolio = None
    not_found = []

    for asset in tqdm(assets):
        ticker_data = get_one_ticker(asset, from_=from_, start_date=start_date, end_date=end_date)
        if ticker_data is None or ticker_data.empty:
            not_found.append(asset)
            continue

        close_data = prepare_data(ticker_data, asset)
        if close_data.index.name != 'Date':
            close_data.index.name = 'Date'

        close_data = close_data.reset_index()

        if 'Date' not in close_data.columns or asset not in close_data.columns:
            print(f"Skipping {asset}: malformed data")
            not_found.append(asset)
            continue

        if portfolio is None:
            portfolio = close_data[['Date']].copy()

        if asset in portfolio.columns:
            continue

        portfolio = pd.merge(portfolio, close_data[['Date', asset]], on='Date', how='outer')

        sleep(0.7)

    if portfolio is None or portfolio.empty:
        raise ValueError("No valid assets found — portfolio is empty")


    portfolio = portfolio.set_index('Date')
    portfolio.index = pd.to_datetime(portfolio.index)
    portfolio = portfolio.round(3)

    print(f"Not found assets: {len(set(not_found))}, {set(not_found)}")
    return portfolio


def get_one_ticker(asset, from_='3m', start_date=None, end_date=dt.now().date()):
    
    headers = {
        'User-Agent': "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; .NET CLR 1.0.3705;)",
    }

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
        try:
            data = pd.DataFrame.from_dict(response.json()['chart']['result'][0]['indicators']['quote'][0])
            data['Date'] = response.json()['chart']['result'][0]['timestamp']
            data['Date'] = data['Date'].apply(dt.fromtimestamp)
        except KeyError:
            return None
        data = data.set_index('Date', drop=True)
        data.index = data.index.normalize()

        data.index.name = 'Date'

        return data.round(2)
    else:
        return None

    
def prepare_data(data, ticker):
    data = data.drop(['open', 'high', 'low', 'volume'], axis=1)
    data = data.rename(columns={"close": ticker})
    return data.round(2)
