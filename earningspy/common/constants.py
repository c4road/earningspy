LOCAL_EARNINGS_CALENDAR_FOLDER = './local_data'

DATA_FOLDER = '/Users/administrador/Documents/DataScience/Projects/Finviz/_Data'
FINVIZ_DATA_CALENDAR_FOLDER = '/FinvizDataCalendars'
FINVIZ_RAW_DATA_FOLDER = '/FinvizRawData'
# Example: (1, 3)  One day before, Three days after
DEFAULT_BEFORE_EARNINGS_DATE_DAYS=1
DEFAULT_AFTER_EARNINGS_DATE_DAYS=5
# Default ranges to calculate pct and diff (days_before, days_after)
RANGES = [(1, 3), (1, 30), (1, 60)]
DEFAULT_IF_ALPHA_WINDOW = 60


ALL_STOCK_INDUSTRIES = [
    "Exchange Traded Fund",
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

TRACKED_INDUSTRIES = [
    'Gold',
    'Internet Retail',
    'Tobacco',
    'Telecom Services',
    'Credit Services',
    'Department Stores', 
    'Computer Hardware',
    'Mortgage Finance',
    'Biotechnology',
    'Capital Markets',
    # 'Restaurants'

]

TRACKED_REITS = [
    "REIT - Diversified",
    "REIT - Healthcare Facilities",
    "REIT - Hotel & Motel",
    "REIT - Industrial",
    "REIT - Mortgage",
    "REIT - Office",
    "REIT - Residential",
    "REIT - Retail",
    "REIT - Specialty"
]

TRACKED_OIL = [
    "Oil & Gas Drilling",
    "Oil & Gas E&P",
    "Oil & Gas Equipment & Services",
    "Oil & Gas Integrated",
    "Oil & Gas Midstream",
    "Oil & Gas Refining & Marketing",
]

TRACKED_FINANCIAL = [
    "Banks - Diversified",
    "Banks - Regional",
    "Capital Markets",
    "Credit Services",
    "Financial Conglomerates",
    "Insurance Brokers",
    "Insurance - Diversified",
    "Insurance - Life",
    "Insurance - Property & Casualty",
    "Insurance - Reinsurance",
    "Insurance - Specialty",
    "Mortgage Finance"
]

TRACKED_TECH = [
    "Software - Application",
    "Software - Infrastructure",
    "Information Technology Services",
    "Biotechnology",
    "Computer Hardware",
    "Engineering & Construction",
]

DEFAULT_TABLE = 'Custom'
EARNINGS_DATE_KEY = 'reportDate'
TICKER_KEY = 'Ticker'
TICKER_KEY_CAPITAL = 'TICKER'
COMPANY_KEY = 'Company'
COMPANY_KEY_CAPITAL = 'COMPANY'
DEFAULT_DATE_FORMAT="%Y-%m-%d"
DAYS_TO_EARNINGS_KEY_CAPITAL='DAYS_LEFT'
DAYS_TO_EARNINGS_KEY_BEFORE_FORMAT='days_left'
IS_ANOMALY_KEY = f"{RANGES[0][0]}-{RANGES[0][1]} pct"
IS_ALPHA_KEY = f"{RANGES[1][0]}-{RANGES[1][1]} pct"
IS_STRONG_KEY = "is_strong"
DEFAULT_DAYS_PRE_EARNINGS = 5

MARKET_DATA_TICKERS = ['^GSPC', '^TNX', '^RUT', '^VIX']
TBILL_10_YEAR = '^TNX'

EARNINGS_DATE_KEY = 'reportDate'
DAYS_TO_EARNINGS_KEY='days_left'  # in lower case betcause this is used before formatting
SYMBOL_KEY = 'symbol'
