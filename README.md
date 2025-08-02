
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
