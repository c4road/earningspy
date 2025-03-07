DEFAULT_REQUEST_METHOD = "sequential"
CUSTOM_TABLE_FIELDS_ON_URL = """&c=0,1,2,3,4,5,6,7,8,9,10,11,13,75,14,15,16,
77,17,18,19,21,23,22,82,78,127,128,24,25,85,26,27,28,29,30,31,84,32,33,34,37,
38,40,41,43,44,46,47,48,49,50,51,57,58,59,68,76,62,63,64,67,65,66,120"""

CUSTOM_TABLE_ALL_FIELDS = [
    # Market Metadata
    'Ticker',
    'Company',

    # Categorical Data
    'Country',
    'Sector',
    'Industry',
    'Index',

    # Comparables per Sector or Industry
    'Market Cap',                       # Market Cap = Total number of shares * market price
    'P/E',                              # P/E = Average Common Stock Price / Net Income Per Share
    'PEG',                              # PEG = (P/E) / Annual EPS Growth
    'P/S',                              # P/S = Current Market Price / Total Revenues Per Share
    'P/B',                              # P/B = Current Market Price / (Total Assets - Total Liabilities)
    'P/FCF',                            # P/FCF = Current Market Price / Cash Flow per Share
    'Payout Ratio',
    'EPS',                              # EPS = (Net Income - Dividends On Preferred Stock) / Average Outstanding Shares
    'EPS this Y',
    'EPS past 5Y',
    'EPS next 5Y',
    'EPS Y/Y TTM',
    'EPS (ttm)',
    'Sales past 5Y',
    'Sales Q/Q',
    'EPS Q/Q',
    'Book/sh',
    'Cash/sh',
    'P/C',

    # Expectations
    'EPS next Q',
    'EPS next Y',
    'Fwd P/E',                          # Forward P/E = Current Market Price / Forecasted Earnings Per Share
    'Forward P/E',
    'EPS Surprise',
    'Revenue Surprise',
    'Sales Surprise',
    'Recom',     # Analyst Recommendation 1.0 Strong Buy, 2.0 Buy, 3.0 Hold, 4.0 Sell, 5.0 Strong Sell

    # Credit Score
    'LTDebt/Eq',
    'Debt/Eq',                          # Debt/Equity = Current Liabilities / (Share Holder's Equity)
                                        # Debt/Equity = Current Liabilities / (Total Assets - Total Liabilities)
                                        # Debt/Equity = Current Liabilities / (Book Value)
    'Current Ratio',                    # Current Ratio = Current Assets / Current Liabilities
    'LT Debt/Eq',                       # LT Debt/Equity = Long Term Debt / (Share Holder's Equity)
                                        # LT Debt/Equity = Long Term Debt / (Total Assets - Total Liabilities)
                                        # LT Debt/Equity = Long Term Debt / (Book Value)

    # Liquidity
    'Quick Ratio',                      # Quick Ratio = (Current Assets - Inventories) / Current Liabilities    

    # Dividend
    'Dividend',
    'Dividend Est.',
    'Dividend TTM',
    'Dividend Ex-Date',
    'Payout',

    # Agent Performance
    'ROA',                              # ROA = Annual Earnings / Total Assets
    'ROE',                              # ROE = Annual Net Income / Share Holder's Equity
    'ROI',                              # ROI = (Gain from Investment - Cost of Investment) / Cost of Investment.
    'Employees',

    # Technicals
    'Perf Week',                        # Last 5 trading days
    'Perf Month',                       # Last 21 trading days
    'Perf Quart',                       # Last 63 trading days
    'Perf Year',                        # Last 252 trading days
    'Perf YTD',
    'Perf Quarter',
    'Perf Half Y',                      # Last 126 trading days
    'SMA20',
    'SMA50',
    'SMA200',
    '52W High',
    '52W Low',
    'RSI',                              # Indicates oversold (buy signal) and overbought (sell signal) price levels for given stock.
    '52W Range',

    # Volatility
    'Beta',                             # (5 years) Calculated on monthly returns 
    'ATR',
    'ATR (14)',
    'Volatility',                       # Return daily high/low % range.
    'Volatility M',
    'Volatility W',
    'RSI (14)',


    # Accounting
    'Sales',
    'Sales Y/Y TTM',
    'Income',
    'Earnings',
    'Oper M',
    'Profit M',
    'Oper. Margin',                     # Operating Margin = Operating Income / Net Sales
    'Profit Margin',                    # Net Profit Margin = Net Income / Revenues
    'Gross Margin',                     # Gross Margin = (Total Sales - Costs) / Total Sales

    # Market Dept
    'Volume',
    'Avg Volume',
    'Rel Volume',
    'Outstanding',
    'Shs Outstand',                     # Shares Outstanding = Total Number Of Shares - Shares Held In Treasury
    'Float',
    'Float %',
    'Insider Own',
    'Insider Trans',
    'Inst Own',
    'Inst Trans',
    'Float Short',                      # The number of shares short divided by total amount of shares float, expressed in %.

    # Short 
    'Short Ratio',                      # The number of shares held short divided by the stock's average daily trading volume
    'Short Interest',                   # Short interest indicates how many company shares are sold short and not yet covered.
    'Shs Float',                        # Shares Float = Shares Outstanding - Insider Shares - Above 5% Owners - Rule 144 Shares
    'Short Float',                      # The number of shares short divided by total amount of shares float, expressed in %.

                       
    'Price',
    'Change',
    'Return% 1Y',

    'Target Price',
    'Option/Short',

    'Prev Close',
]

PERFORMANCE_TABLE_ALL_FIELDS = [
    'Ticker',
    'Perf Week',
    'Perf Month',
    'Perf Quart',
    'Perf Half',
    'Perf Year',
    'Perf YTD',
    'Volatility W',
    'Volatility M',
    'Recom',
    'Avg Volume',
    'Rel Volume',
    'Price',
    'Change',
    'Volume',
    'Index',
    'P/E',
    'EPS (ttm)',
    'Insider Own',
    'Shs Outstand',
    'Market Cap',
    'Forward P/E',
    'EPS next Y',
    'Insider Trans',
    'Shs Float',
    'Income',
    'PEG',
    'EPS next Q',
    'Inst Own',
    'Short Float',
    'Perf Quarter',
    'Sales',
    'P/S',
    'EPS this Y',
    'Inst Trans',
    'Short Ratio',
    'Perf Half Y',
    'Book/sh',
    'P/B',
    'ROA',
    'Short Interest',
    'Cash/sh',
    'P/C',
    'EPS next 5Y',
    'ROE',
    '52W Range',
    'Dividend Est.',
    'P/FCF',
    'EPS past 5Y',
    'ROI',
    '52W High',
    'Beta',
    'Dividend TTM',
    'Quick Ratio',
    'Sales past 5Y',
    'Gross Margin',
    '52W Low',
    'ATR (14)',
    'Dividend Ex-Date',
    'Current Ratio',
    'EPS Y/Y TTM',
    'Oper. Margin',
    'RSI (14)',
    'Volatility',
    'Employees',
    'Debt/Eq',
    'Sales Y/Y TTM',
    'Profit Margin',
    'Target Price',
    'Option/Short',
    'LT Debt/Eq',
    'EPS Q/Q',
    'Payout',
    'Prev Close',
    'Sales Surprise',
    'EPS Surprise',
    'Sales Q/Q',
    'Earnings',
    'SMA20',
    'SMA50',
    'SMA200'
]

MONEY_COLUMNS = [
    'Avg Volume', 
    'Shs Outstand',
    'Market Cap',
    'Shs Float',
    'Income',
    'Sales',
    'Short Interest',
    'Outstanding',
    'Float'
]

PERCENTAJE_COLUMNS = [
    'Perf Week', 
    'Perf Month', 
    'Perf Quart', 
    'Perf Year', 
    'Perf YTD', 
    'Volatility W', 
    'Volatility M', 
    'Change', 
    'Insider Own',
    'EPS next Y',
    'Insider Trans',
    'Inst Own',
    'Perf Quarter',
    'EPS this Y',
    'Inst Trans',
    'Perf Half Y',
    'ROA',
    'EPS next 5Y',
    'ROE',
    'EPS past 5Y',
    'ROI',
    '52W High',
    'Sales past 5Y',
    'Gross Margin',
    '52W Low',
    'Sales Q/Q',
    'Oper. Margin',
    'EPS Q/Q',
    'Profit Margin',
    'Payout',
    'SMA20',
    'SMA50',
    'SMA200',
    'Dividend',
    'Payout Ratio',
    'EPS Surprise',
    'Revenue Surprise',
    'Float %',
    'Float Short',
    'Oper M',
    'Profit M',
    'Short Float',
    'EPS Y/Y TTM',
    'Sales Y/Y TTM',
    'Sales Surprise',
]

NUMERIC_COLUMNS = [
    'P/FCF',
    'Beta',
    'Quick Ratio',
    'ATR',
    'Employees',
    'Current Ratio',
    'RSI (14)',
    'Debt/Eq',
    'LT Debt/Eq',
    'Recom',
    'Rel Volume',
    'Price',
    'Volume',
    'P/E',
    'EPS (ttm)',
    'Forward P/E',
    'PEG',
    'P/S',
    'Book/sh',
    'P/B',
    'Target Price',
    'Cash/sh',
    'P/C',
    'EPS next Q',
    'Fwd P/E',
    'EPS',
    'Short Ratio',
    'Short Interest',
    'RSI',
    'Avg Volume',
    'Return% 1Y',
    'Shs Outstand',
    'Shs Float',
    'ATR (14)',
    'Prev Close',
]

BOOLEAN_COLUMNS = [
    'Optionable',
    'Shortable'
]

ALLOWED_INDUSTRIES = [
    "Advertising Agencies",
    "Aerospace & Defense",
    "Agricultural Inputs",
    "Airlines",
    "Airports & Air Services",
    "Aluminum",
    "Apparel Manufacturing",
    "Apparel Retail",
    "Asset Management",
    "Auto Manufacturers",
    "Auto Parts",
    "Auto & Truck Dealerships",
    "Banks - Diversified",
    "Banks - Regional",
    "Beverages - Brewers",
    "Beverages - Non-Alcoholic",
    "Beverages - Wineries & Distilleries",
    "Biotechnology",
    "Broadcasting",
    "Building Materials",
    "Building Products & Equipment",
    "Business Equipment & Supplies",
    "Capital Markets",
    "Chemicals",
    "Coking Coal",
    "Communication Equipment",
    "Computer Hardware",
    "Confectioners",
    "Conglomerates",
    "Consulting Services",
    "Consumer Electronics",
    "Copper",
    "Credit Services",
    "Department Stores",
    "Diagnostics & Research",
    "Discount Stores",
    "Drug Manufacturers - General",
    "Drug Manufacturers - Specialty & Generic",
    "Education & Training Services",
    "Electrical Equipment & Parts",
    "Electronic Components",
    "Electronic Gaming & Multimedia",
    "Electronics & Computer Distribution",
    "Engineering & Construction",
    "Entertainment",
    "Farm & Heavy Construction Machinery",
    "Farm Products",
    "Financial Conglomerates",
    "Financial Data & Stock Exchanges",
    "Food Distribution",
    "Footwear & Accessories",
    "Furnishings, Fixtures & Appliances",
    "Gambling",
    "Gold",
    "Grocery Stores",
    "Healthcare Plans",
    "Health Information Services",
    "Home Improvement Retail",
    "Household & Personal Products",
    "Industrial Distribution",
    "Information Technology Services",
    "Infrastructure Operations",
    "Insurance Brokers",
    "Insurance - Diversified",
    "Insurance - Life",
    "Insurance - Property & Casualty",
    "Insurance - Reinsurance",
    "Insurance - Specialty",
    "Integrated Freight & Logistics",
    "Internet Content & Information",
    "Internet Retail",
    "Leisure",
    "Lodging",
    "Lumber & Wood Production",
    "Luxury Goods",
    "Marine Shipping",
    "Medical Care Facilities",
    "Medical Devices",
    "Medical Distribution",
    "Medical Instruments & Supplies",
    "Metal Fabrication",
    "Mortgage Finance",
    "Oil & Gas Drilling",
    "Oil & Gas E&P",
    "Oil & Gas Equipment & Services",
    "Oil & Gas Integrated",
    "Oil & Gas Midstream",
    "Oil & Gas Refining & Marketing",
    "Other Industrial Metals & Mining",
    "Other Precious Metals & Mining",
    "Packaged Foods",
    "Packaging & Containers",
    "Paper & Paper Products",
    "Personal Services",
    "Pharmaceutical Retailers",
    "Pollution & Treatment Controls",
    "Publishing",
    "Railroads",
    "Real Estate - Development",
    "Real Estate - Diversified",
    "Real Estate Services",
    "Recreational Vehicles",
    "REIT - Diversified",
    "REIT - Healthcare Facilities",
    "REIT - Hotel & Motel",
    "REIT - Industrial",
    "REIT - Mortgage",
    "REIT - Office",
    "REIT - Residential",
    "REIT - Retail",
    "REIT - Specialty",
    "Rental & Leasing Services",
    "Residential Construction",
    "Resorts & Casinos",
    "Restaurants",
    "Scientific & Technical Instruments",
    "Security & Protection Services",
    "Semiconductor Equipment & Materials",
    "Semiconductors",
    "Shell Companies",
    "Silver",
    "Software - Application",
    "Software - Infrastructure",
    "Solar",
    "Specialty Business Services",
    "Specialty Chemicals",
    "Specialty Industrial Machinery",
    "Specialty Retail",
    "Staffing & Employment Services",
    "Steel",
    "Telecom Services",
    "Textile Manufacturing",
    "Thermal Coal",
    "Tobacco",
    "Tools & Accessories",
    "Travel Services",
    "Trucking",
    "Uranium",
    "Utilities - Diversified",
    "Utilities - Independent Power Producers",
    "Utilities - Regulated Electric",
    "Utilities - Regulated Gas",
    "Utilities - Regulated Water",
    "Utilities - Renewable",
    "Waste Management"
]

def calculate_z_stat(observed_freq, expected_freq, total_count):

    if total_count == 0 or expected_freq == 0:
        return 0

    standard_error = np.sqrt(expected_freq * (1 - expected_freq) / total_count)
    if standard_error == 0:
        return 0

    return (observed_freq - expected_freq) / standard_error