import pandas as pd

def calendar_pre_formatter(data):
    data = data.drop(['LTDebt/Eq', 'Dividend Ex-Date'], axis=1)
    data.columns = data.columns.str.replace(' ', '_')
    data.columns = data.columns.str.upper()
    data.columns = data.columns.str.strip()
    data = data.rename(columns={'VOLATILITY_W': 'VOLATILITY_HIGH', 'VOLATILITY_M': 'VOLATILITY_LOW'})

    data['LTDEBT/EQ'] = pd.to_numeric(data['LTDEBT/EQ'], errors='coerce')
    data['IS_AMC'] = data['IS_AMC'].fillna(0).astype('int64')
    data['IS_BMO'] = data['IS_BMO'].fillna(0).astype('int64')

    # drop columns that are not useful or were preprocessed
    data = data.drop([
        'FISCALDATEENDING',
        'COUNTRY',
        'INDEX', 
        'ESTIMATE',
        'EARNINGS', 
        'CURRENCY', 
        'RETURN%_1Y', 
        'DIVIDEND_EST.', 
        'DIVIDEND_TTM', 
        'OPTION/SHORT', 
        'VOLATILITY', 
        '52W_HIGH', 
        '52W_LOW', 
        '52W_RANGE'
    ], axis=1)

    # round to four decimal places
    data = data.round(4)
    return data
