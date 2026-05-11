"""
Finviz Module for Stock Data and Screening

This module provides tools to fetch stock data, news, and screener information from Finviz.com.

Debug Logging Setup:
For troubleshooting scraping issues, enable debug logging:

    import logging
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('earningspy.generators.finviz').setLevel(logging.DEBUG)

    from earningspy.generators.finviz import Screener
    # Now all finviz operations will show detailed debug logs
"""

from earningspy.generators.finviz.main_func import (get_all_news, get_analyst_price_targets,
                              get_insider, get_news, get_stock)
from earningspy.generators.finviz.data import (get_available_filters, get_stocks_by_earnings_date,
                             get_stocks_by_tickers, get_filters, get_by_earnings_date,
                             get_by_tickers)
from earningspy.generators.finviz.portfolio import Portfolio
from earningspy.generators.finviz.screener import Screener
from earningspy.generators.finviz.visualization import (
    create_pe_pb_scatter, create_market_cap_distribution, create_sector_performance_heatmap,
    create_volatility_analysis, create_financial_dashboard, save_visualization,
    analyze_value_stocks, analyze_growth_stocks
)
