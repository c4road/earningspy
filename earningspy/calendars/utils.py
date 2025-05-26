import numpy as np
from datetime import datetime
import pandas as pd


def calendar_pre_formatter(data):
    
    data.columns = data.columns.str.replace(' ', '_')
    data.columns = data.columns.str.upper()
    data.columns = data.columns.str.strip()

    data['IS_AMC'] = data['IS_AMC'].fillna(0).astype('int64')
    data['IS_BMO'] = data['IS_BMO'].fillna(0).astype('int64')

    data = data.round(4)
    return data


def days_left(row):
    if isinstance(row.name, pd._libs.tslibs.nattype.NaTType) or pd.isna(row.name) or row.name is None:
        # print(f"NaTType found in row: {row.name}")
        return None  
    earnings_date = row.name
    today = datetime.today()
    diff = earnings_date - today
    return int(diff.days)
