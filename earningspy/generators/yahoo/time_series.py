import pandas as pd
from datetime import datetime as dt
import requests
import io


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

def get_portfolio(assets, start_date, end_date):

    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'}

    start, end = get_range_timestamps(start_date, end_date)
    portfolio = pd.DataFrame()

    for i, asset in enumerate(assets):
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{asset}?" \
            f"period1={start}&period2={end}&interval=1d&events=history"
        try:
            response = requests.get(url, headers=headers)
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

# usage
# from datetime import datetime
# end = datetime.now().date()
# start = end - relativedelta(months=3)

# final_data = get_yahoo_finance_data(tickers, start_date=str(start), end_date=str(end))