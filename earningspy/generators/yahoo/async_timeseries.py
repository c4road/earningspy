import asyncio
import aiohttp
import random

from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
import pandas as pd
from tqdm import tqdm

# Existing functions (get_range, get_range_timestamps, prepare_data) remain unchanged
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

async def get_one_ticker_async(session, asset, from_='3m', start_date=None, end_date=dt.now().date()):
    headers = {
        'User-Agent': "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; .NET CLR 1.0.3705;)",
    }

    if start_date:
        end_date = str(end_date)
        start, end = get_range_timestamps(start_date, end_date)
    else:
        start, end = get_range(range_from=from_, end_date=end_date)
        start, end = get_range_timestamps(start, end)

    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{asset}?period1={start}&period2={end}&interval=1d&events=history"
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                df = pd.DataFrame.from_dict(data['chart']['result'][0]['indicators']['quote'][0])
                df['Date'] = data['chart']['result'][0]['timestamp']
                df['Date'] = df['Date'].apply(dt.fromtimestamp)
                df = df.set_index('Date', drop=True)
                df.index = df.index.normalize()
                return asset, df.round(2)
            else:
                # print(f"Could not retrieve data for {asset}: {response.status}")
                return asset, None
    except Exception as e:
        print(f"Error fetching data for {asset}: {str(e)}")
        return asset, None

async def get_portfolio_async(assets, from_='3m', start_date=None, end_date=dt.now().date()):
    portfolio = pd.DataFrame()
    not_found = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for asset in assets:
            tasks.append(asyncio.ensure_future(get_one_ticker_async(session, asset, from_=from_, start_date=start_date, end_date=end_date)))
        
        for future in tqdm(asyncio.as_completed(tasks), total=len(assets)):
            asset, ticker_data = await future
            if ticker_data is None:
                not_found.append(asset)
                continue
            
            close_data = prepare_data(ticker_data, asset).reset_index()
            
            if portfolio.empty:
                portfolio = close_data[['Date', asset]]
            elif asset not in portfolio.columns:
                portfolio = pd.merge(portfolio, close_data[['Date', asset]], on='Date', how='outer')
            
            # Random sleep to avoid rate limiting
            await asyncio.sleep(random.uniform(0.5, 1.0))

    portfolio = portfolio.set_index('Date')
    portfolio.index = pd.to_datetime(portfolio.index)
    portfolio = portfolio.round(3)
    if len(not_found):
        print(f"Not found assets: {len(set(not_found))}, {set(not_found)}")
    return portfolio

def prepare_data(data, ticker):
    data = data.drop(['open', 'high', 'low', 'volume'], axis=1)
    data = data.rename(columns={"close": ticker})
    return data.round(2)


def get_portfolio(assets, from_='3m', start_date=None, end_date=dt.now().date()):
    """
    Synchronous wrapper for the asynchronous get_portfolio_async function.
    """
    loop = asyncio.get_event_loop()
    portfolio = loop.run_until_complete(get_portfolio_async(assets, from_=from_, start_date=start_date, end_date=end_date))
    return portfolio
