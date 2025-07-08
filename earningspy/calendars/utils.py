from datetime import datetime
import pandas as pd
from earningspy.common.constants import (
    FIELDS_ORDER
)


def calendar_pre_formatter(data):

    data.columns = data.columns.str.replace(' ', '_')
    data.columns = data.columns.str.upper()
    data.columns = data.columns.str.strip()

    data = data.convert_dtypes().infer_objects()

    data = data.round(4)
    data = data[FIELDS_ORDER]
    return data


def days_left(row):
    if isinstance(row.name, pd._libs.tslibs.nattype.NaTType) or pd.isna(row.name) or row.name is None:
        return None
    
    earnings_date = row.name

    if hasattr(earnings_date, "date"):
        earnings_date = earnings_date.date()

    today = datetime.today().date()
    diff = (earnings_date - today).days
    return diff
