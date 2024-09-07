import os
class Config:
    def __init__(self):
        self.ALPHA_VANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", None)
        self.LOCAL_HISTORIC_EARNINGS_CALENDAR = "from-Feb2023EarningsCalendar.csv"
        self.PRE_EARNINGS_KEEP_LAST_NAME = "earnings_before-all-keep_last.csv"
        self.PRE_EARNINGS_KEEP_FIRST_NAME = "earnings_before-all-keep_first.csv"
        self.POST_EARNINGS_KEEP_FIRST_NAME = "earnings_after-all-keep_first.csv"
        self.REPORTED_FILENAME = None
        self.BEFORE_EARNINGS_DATA_FILENAME = None
        self.S3_BUCKET_NAME = None
        self.S3_BUCKET_KEY = None
        self.EARNINGS_CALENDAR_FOLDER = None

class QA:
    pass

class Production:
    pass