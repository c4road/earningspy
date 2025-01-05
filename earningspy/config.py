import os
class Config:
    def __init__(self):
        self.ALPHA_VANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
        self.EARNINGS_CALENDAR_PATH = os.getenv("EARNINGS_CALENDAR_PATH", 'test_earning_calendar.csv')
        self.PRE_EARNINGS_DATA_PATH = os.getenv("PRE_EARNINGS_DATA_PATH")
        self.POST_EARNINGS_DATA_PATH = os.getenv("POST_EARNINGS_DATA_PATH") 
        self.TRAINING_DATA_PATH = os.getenv("TRAINING_DATA_PATH")

class QA:
    pass

class Production:
    pass