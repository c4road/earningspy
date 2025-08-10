
| [![Run Tests](https://github.com/c4road/earningspy/actions/workflows/run-tests.yml/badge.svg)](https://github.com/c4road/earningspy/actions/workflows/run-tests.yml) | [![Bump Version on Merge](https://github.com/c4road/earningspy/actions/workflows/bump-version.yml/badge.svg)](https://github.com/c4road/earningspy/actions/workflows/bump-version.yml) | [![Publish Wheel to PyPi](https://github.com/c4road/earningspy/actions/workflows/publish-wheel.yml/badge.svg)](https://github.com/c4road/earningspy/actions/workflows/publish-wheel.yml) |
|----------|----------|----------|


# EarningsPy 📈

EarningsPy is the elegant Python alternative for studying Post Earnings Announcement Drift (PEAD) in financial markets. Designed for quant researchers, data scientists, and finance professionals, this package provides robust tools to analyze earnings calendars, automate data collection, and perform advanced event studies with ease.

## Features

- 🗓️ **Earnings Calendar Access**: Effortlessly retrieve earnings dates by sector, industry, index, or market capitalization.
- 🚀 **PEAD Analysis**: Built-in utilities to compute post-earnings drift and related statistics.
- 🏦 **Data Integration**: Seamless integration with Finviz for comprehensive earnings and 20 min delayed market data.
- 🔍 **Flexible Filtering**: Filter earnings events by week, month, or custom criteria.
- 🛠️ **Quant-Friendly API**: Pandas-based workflows for easy integration into quant research pipelines.
- 📊 **Excel-Ready Data**: Generate profiled, ready-to-use datasets for calculations and modeling directly in Excel.


## Installation

```bash
pip install earningspy
```

## Usage (WIP)

### Fetch next week earnings
```python
from earningspy.calendars.earnings import EarningSpy
EarningSpy.get_next_week_earnings()
```

### Fetch earnings by ticker
```python
from earningspy.calendars.earnings import EarningSpy
EarningSpy.get_by_tickers(['AAPL', 'MSFT', 'GOOGL'])
```

### Inspect PEAD anomaly with after-earnings data

This is useful to build timeseries, dashboards and graphs to study historical information, not suitable to train models because you will have look ahead bias. The data fetched using this approach will contain post earning information. Meaning, it will contain the fundamentals lastly reported.

#### First time (create your local calendar file)
```python
from earningspy.calendars.earnings import EarningSpy
from earningspy.inspectors.pead import PEADInspector
import nest_asyncio  # Only if ran on a notebook
nest_asyncio.apply()

# Get after earning data
previous_week = EarningSpy.get_this_week_earnings()
inspector = PEADInspector(
    calendar=previous_week
)

# Inspect on stocks with three days passed from the earnings
# dry_run=True shows the list of stocks to be processed without inspecting
inspector.inspect(days=3, dry_run=True, post_earnings=True)

# dry_run=False gets timeseries data to calculate anomaly metrics (CAPM, CAR, BHAR, VIX, etc)
inspector.inspect(days=3, dry_run=False, post_earnings=True)

# check new columns created
inspector.calendar

# Store in a safe place
inspector.calendar.to_csv('post_earnings.csv')
```

#### Second time (load local calendar and append new information) 

```python
from earningspy.calendars.earnings import EarningSpy
from earningspy.inspectors.pead import PEADInspector
import nest_asyncio  # Only if ran on a notebook
nest_asyncio.apply()

# Get after earning data
# Use .get_this_week_earnings() if the week has not ended
# Use .get_previous_week_earnings() if the week already passed
previous_week = EarningSpy.get_this_week_earnings()
inspector = PEADInspector(
    calendar=previous_week
)

# load local storage
storage = pd.read_csv('post_earnings.csv', index_col=0, parse_dates=True)

# join new calendar with local storage
merged = pead.join(storage, type_='post')

# you can see the data that is going to be processed without processing it on a given days window
inspector.inspect(days=3, dry_run=True, post_earnings=True)

# you can chain the inspector this will calculate metrics for 60, 30, and 3 event windows
inspector = inspector.inspect(days=60, post_earnings=True) \
                     .inspect(days=30, post_earnings=True) \
                     .inspect(days=3, post_earnings=True)

# Put the updated calendar back on local storage
inspector.calendar.to_csv('post_earnings.csv')
```

Then you can use the local storge with your preferable BI tool (PowerBI, Tableau, Excel)

### Inspect PEAD anomaly with before-earnings data (WIP)

This is useful to train models and perform statistical regressions, it could also be used to build dashboards and graphs but bear in mind that the data fetched using this approach will contain pre earning information. Meaning, the date will point to fundamentals 1 to 5 days before the earnings. For example, if you plot a timeseries over the EPS you will see the EPS previous to the one reported on that given date. 

#### First time (create your local calendar file)

```python
from earningspy.calendars.earnings import EarningSpy
from earningspy.inspectors.pead import PEADInspector
import nest_asyncio  # Only if ran on a notebook
nest_asyncio.apply()

# Get before earning data
# Use .get_next_week_earnings() because you are seeking before earnings information
next_week = EarningSpy.get_next_week_earnings()
inspector = PEADInspector(
    calendar=previous_week
)

# nothing to inspect here because the earnings did not come yet
inspector.calendar.to_csv('post_earnings.csv')
```

#### Second time (load local calendar and append new information) 

```python
from earningspy.calendars.earnings import EarningSpy
from earningspy.inspectors.pead import PEADInspector
import nest_asyncio  # Only if ran on a notebook
nest_asyncio.apply()

# Get before earning data
previous_week = EarningSpy.get_next_week_earnings()
inspector = PEADInspector(
    calendar=previous_week
)

# load local storage
storage = pd.read_csv('pre_earnings.csv', index_col=0, parse_dates=True)

# join new calendar with local storage
merged = pead.join(storage, type_='pre')

# you can see the data that is going to be processed without processing it on a given days window
inspector.inspect(days=3, dry_run=True)
inspector.inspect(days=30, dry_run=True)
inspector.inspect(days=60, dry_run=True)

# you can chain the inspector this will calculate metrics for 60, 30, and 3 event windows
inspector = inspector.inspect(days=60) \
                     .inspect(days=30) \
                     .inspect(days=3)

# Put the updated calendar back on local storage
inspector.calendar.to_csv('pre_earnings.csv')
```

Then you can use the local storge with your preferable BI tool (PowerBI, Tableau, Excel).
At this point you should already have anomaly metrics.
