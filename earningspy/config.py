import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY', 
                                                    'not provided')
        self.PRE_EARNINGS_KEEP_LAST_NAME = "earnings_before-all-keep_last.csv"
        self.PRE_EARNINGS_KEEP_FIRST_NAME = "earnings_before-all-keep_first.csv"
        self.POST_EARNINGS_KEEP_FIRST_NAME = "earnings_after-all-keep_first.csv"
        self.REPORTED_FILENAME = None
        self.BEFORE_EARNINGS_DATA_FILENAME = None
        self.S3_BUCKET_NAME = None
        self.S3_BUCKET_KEY = None
        self.EARNINGS_CALENDAR_FOLDER = None
