"""
Finviz Data Visualization Module

This module provides interactive Plotly-based visualizations for financial data
from the Finviz screener. Uses Plotly for creating interactive charts that
can be displayed in web browsers or Jupyter notebooks.

Features:
- Scatter plots for financial ratios (P/E vs P/B, etc.)
- Market cap distributions
- Sector/industry breakdowns
- Performance comparisons
- Volatility analysis
- Interactive filtering and zooming

Usage:
    from earningspy.generators.finviz.visualization import create_pe_pb_scatter
    from earningspy.generators.finviz.data import get_stocks_by_earnings_date

    # Get data
    df = get_stocks_by_earnings_date('next_week')

    # Create interactive scatter plot
    fig = create_pe_pb_scatter(df)
    fig.show()  # Opens in browser

    # Or save as HTML
    fig.write_html('pe_pb_analysis.html')
"""

import logging
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio

logger = logging.getLogger(__name__)

# Set default template for consistent styling
pio.templates.default = "plotly_white"

# Color schemes for financial data
FINANCIAL_COLORS = {
    'positive': '#00C853',      # Green for positive values
    'negative': '#D32F2F',      # Red for negative values
    'neutral': '#FFC107',       # Yellow/amber for neutral
    'background': '#F5F5F5',    # Light gray background
    'grid': '#E0E0E0',          # Light grid lines
    'text': '#212121'           # Dark text
}

# Common chart dimensions
CHART_CONFIG = {
    'width': 1000,
    'height': 600,
    'font_size': 12,
    'title_font_size': 16
}


def create_pe_pb_scatter(df, color_by='Sector', size_by='Market Cap', hover_data=None):
    """
    Create an interactive scatter plot of P/E vs P/B ratios.

    This is a fundamental value investing visualization that shows the relationship
    between price-to-earnings and price-to-book ratios, commonly used to identify
    potentially undervalued or overvalued stocks.

    Args:
        df (pd.DataFrame): DataFrame with financial data including 'P/E' and 'P/B' columns
        color_by (str): Column to color points by (default: 'Sector')
        size_by (str): Column to size points by (default: 'Market Cap')
        hover_data (list): Additional columns to show in hover tooltip

    Returns:
        plotly.graph_objects.Figure: Interactive scatter plot figure

    Example:
        >>> df = get_stocks_by_earnings_date('next_week')
        >>> fig = create_pe_pb_scatter(df)
        >>> fig.show()
    """
    # Prepare data
    plot_df = df.copy()

    # Clean and prepare P/E and P/B columns
    plot_df['P/E'] = pd.to_numeric(plot_df['P/E'], errors='coerce')
    plot_df['P/B'] = pd.to_numeric(plot_df['P/B'], errors='coerce')

    # Remove rows with missing values
    plot_df = plot_df.dropna(subset=['P/E', 'P/B'])

    # Filter out extreme outliers (optional, but helps with visualization)
    plot_df = plot_df[
        (plot_df['P/E'] > 0) & (plot_df['P/E'] < 200) &
        (plot_df['P/B'] > 0) & (plot_df['P/B'] < 50)
    ]

    # Prepare hover data
    default_hover = ['Ticker', 'Company', 'Sector', 'Market Cap', 'Price']
    if hover_data is None:
        hover_data = default_hover

    # Filter hover_data to only include columns that exist in the dataframe
    available_columns = plot_df.columns.tolist()
    hover_data = [col for col in hover_data if col in available_columns]

    if color_by not in plot_df.columns:
        logger.warning("Color column '%s' not found in data; falling back to no color grouping.", color_by)
        color_by = None

    if size_by not in plot_df.columns:
        logger.warning("Size column '%s' not found in data; falling back to default marker size.", size_by)
        size_by = None

    # Create the scatter plot
    fig = px.scatter(
        plot_df,
        x='P/E',
        y='P/B',
        color=color_by,
        size=size_by,
        hover_data=hover_data,
        title='P/E vs P/B Ratio Analysis',
        labels={
            'P/E': 'Price-to-Earnings Ratio',
            'P/B': 'Price-to-Book Ratio',
            'Market Cap': 'Market Capitalization'
        }
    )

    # Update layout for better readability
    fig.update_layout(
        width=CHART_CONFIG['width'],
        height=CHART_CONFIG['height'],
        font=dict(size=CHART_CONFIG['font_size']),
        title_font=dict(size=CHART_CONFIG['title_font_size']),
        xaxis=dict(
            title='Price-to-Earnings Ratio',
            gridcolor=FINANCIAL_COLORS['grid']
        ),
        yaxis=dict(
            title='Price-to-Book Ratio',
            gridcolor=FINANCIAL_COLORS['grid']
        ),
        plot_bgcolor=FINANCIAL_COLORS['background']
    )

    # Add reference lines for value investing zones
    fig.add_hline(y=1, line_dash="dash", line_color="red", annotation_text="P/B = 1")
    fig.add_vline(x=15, line_dash="dash", line_color="red", annotation_text="P/E = 15")

    logger.info(f"Created P/E vs P/B scatter plot with {len(plot_df)} data points")
    return fig


def create_market_cap_distribution(df, bins=20, color_by='Sector'):
    """
    Create a histogram showing market capitalization distribution.

    Useful for understanding the size distribution of stocks in a dataset
    and identifying large-cap, mid-cap, and small-cap opportunities.

    Args:
        df (pd.DataFrame): DataFrame with 'Market Cap' column
        bins (int): Number of histogram bins (default: 20)
        color_by (str): Column to color bars by (default: 'Sector')

    Returns:
        plotly.graph_objects.Figure: Interactive histogram figure
    """
    plot_df = df.copy()

    # Clean market cap data
    plot_df['Market Cap'] = pd.to_numeric(plot_df['Market Cap'], errors='coerce')
    plot_df = plot_df.dropna(subset=['Market Cap'])

    # Convert to billions for better readability
    plot_df['Market Cap (B)'] = plot_df['Market Cap'] / 1e9

    if color_by not in plot_df.columns:
        logger.warning("Color column '%s' not found in market cap data; using no color grouping.", color_by)
        color_by = None

    fig = px.histogram(
        plot_df,
        x='Market Cap (B)',
        color=color_by,
        nbins=bins,
        title='Market Capitalization Distribution',
        labels={'Market Cap (B)': 'Market Cap ($ Billions)'}
    )

    fig.update_layout(
        width=CHART_CONFIG['width'],
        height=CHART_CONFIG['height'],
        font=dict(size=CHART_CONFIG['font_size']),
        title_font=dict(size=CHART_CONFIG['title_font_size']),
        xaxis=dict(gridcolor=FINANCIAL_COLORS['grid']),
        yaxis=dict(gridcolor=FINANCIAL_COLORS['grid']),
        plot_bgcolor=FINANCIAL_COLORS['background']
    )

    logger.info(f"Created market cap distribution histogram with {len(plot_df)} data points")
    return fig


def create_sector_performance_heatmap(df, metric='Perf Year', normalize=True):
    """
    Create a heatmap showing sector performance across different metrics.

    Args:
        df (pd.DataFrame): DataFrame with sector and performance data
        metric (str): Performance metric column (default: 'Perf Year')
        normalize (bool): Whether to normalize values within each sector

    Returns:
        plotly.graph_objects.Figure: Interactive heatmap figure
    """
    plot_df = df.copy()

    # Clean the metric column
    plot_df[metric] = pd.to_numeric(plot_df[metric], errors='coerce')
    plot_df = plot_df.dropna(subset=[metric, 'Sector'])

    # Group by sector and calculate statistics
    sector_stats = plot_df.groupby('Sector')[metric].agg(['mean', 'median', 'count']).round(2)

    if normalize:
        # Normalize within each sector for relative comparison
        sector_stats['normalized'] = (sector_stats['mean'] - sector_stats['mean'].min()) / \
                                   (sector_stats['mean'].max() - sector_stats['mean'].min())

    # Create heatmap data
    sectors = sector_stats.index.tolist()
    values = sector_stats['mean'].tolist()

    fig = go.Figure(data=go.Heatmap(
        z=[values],
        x=sectors,
        y=[metric],
        colorscale='RdYlGn',
        text=[[f'{val:.2f}' for val in values]],
        texttemplate='%{text}',
        textfont={"size": 10},
        hoverongaps=False
    ))

    fig.update_layout(
        title=f'Sector Performance Heatmap - {metric}',
        width=CHART_CONFIG['width'],
        height=400,
        font=dict(size=CHART_CONFIG['font_size']),
        title_font=dict(size=CHART_CONFIG['title_font_size'])
    )

    logger.info(f"Created sector performance heatmap for {len(sectors)} sectors")
    return fig


def create_volatility_analysis(df, color_by='Sector'):
    """
    Create a scatter plot analyzing volatility metrics.

    Shows the relationship between beta (market volatility) and other
    volatility measures like ATR and standard deviation.

    Args:
        df (pd.DataFrame): DataFrame with volatility columns
        color_by (str): Column to color points by

    Returns:
        plotly.graph_objects.Figure: Interactive volatility analysis figure
    """
    plot_df = df.copy()

    # Clean volatility columns
    vol_cols = ['Beta', 'ATR', 'Volatility W', 'Volatility M']
    for col in vol_cols:
        if col in plot_df.columns:
            plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')

    if 'Beta' not in plot_df.columns or 'Volatility M' not in plot_df.columns:
        logger.warning("Missing required volatility columns; returning empty volatility figure.")
        return go.Figure()

    plot_df = plot_df.dropna(subset=['Beta', 'Volatility M'])

    hover_columns = [col for col in ['Ticker', 'Company', 'Price'] if col in plot_df.columns]
    if color_by not in plot_df.columns:
        logger.warning("Color column '%s' not found in volatility data; using default color grouping.", color_by)
        color_by = None

    fig = px.scatter(
        plot_df,
        x='Beta',
        y='Volatility M',
        color=color_by,
        size='Market Cap' if 'Market Cap' in plot_df.columns else None,
        hover_data=hover_columns,
        title='Volatility Analysis: Beta vs Monthly Volatility',
        labels={
            'Beta': 'Beta (Market Volatility)',
            'Volatility M': 'Monthly Volatility (%)'
        }
    )

    # Add reference lines
    fig.add_vline(x=1, line_dash="dash", line_color="gray", annotation_text="Beta = 1 (Market)")
    fig.add_hline(y=plot_df['Volatility M'].mean(), line_dash="dash", line_color="blue",
                  annotation_text=f"Avg Volatility: {plot_df['Volatility M'].mean():.1f}%")

    fig.update_layout(
        width=CHART_CONFIG['width'],
        height=CHART_CONFIG['height'],
        font=dict(size=CHART_CONFIG['font_size']),
        title_font=dict(size=CHART_CONFIG['title_font_size']),
        xaxis=dict(gridcolor=FINANCIAL_COLORS['grid']),
        yaxis=dict(gridcolor=FINANCIAL_COLORS['grid']),
        plot_bgcolor=FINANCIAL_COLORS['background']
    )

    logger.info(f"Created volatility analysis plot with {len(plot_df)} data points")
    return fig


def create_financial_dashboard(df):
    """
    Create a comprehensive financial dashboard with multiple charts.

    Combines several key visualizations into a single interactive dashboard
    for comprehensive financial analysis.

    Args:
        df (pd.DataFrame): DataFrame with complete financial data

    Returns:
        plotly.graph_objects.Figure: Multi-panel dashboard figure
    """
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('P/E vs P/B Analysis', 'Market Cap Distribution',
                       'Sector Performance', 'Volatility Analysis'),
        specs=[[{'type': 'scatter'}, {'type': 'histogram'}],
               [{'type': 'heatmap'}, {'type': 'scatter'}]]
    )

    # P/E vs P/B scatter
    pe_pb_data = df.dropna(subset=['P/E', 'P/B'])
    pe_pb_data = pe_pb_data[(pe_pb_data['P/E'] > 0) & (pe_pb_data['P/E'] < 200) &
                           (pe_pb_data['P/B'] > 0) & (pe_pb_data['P/B'] < 50)]

    fig.add_trace(
        go.Scatter(
            x=pe_pb_data['P/E'],
            y=pe_pb_data['P/B'],
            mode='markers',
            name='P/E vs P/B',
            marker=dict(
                size=6,
                color=pe_pb_data.get('Market Cap', 1e9) / 1e9,  # Size by market cap
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Market Cap (B)", x=0.45, y=0.8)
            ),
            text=pe_pb_data['Ticker'],
            hovertemplate='<b>%{text}</b><br>P/E: %{x:.2f}<br>P/B: %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )

    # Market cap histogram
    mc_data = df.dropna(subset=['Market Cap'])
    mc_data['Market Cap (B)'] = mc_data['Market Cap'] / 1e9

    fig.add_trace(
        go.Histogram(
            x=mc_data['Market Cap (B)'],
            name='Market Cap Distribution',
            nbinsx=20
        ),
        row=1, col=2
    )

    # Sector performance heatmap
    if 'Sector' in df.columns and 'Perf Year' in df.columns:
        sector_perf = df.dropna(subset=['Sector', 'Perf Year']).groupby('Sector')['Perf Year'].mean()
        sectors = sector_perf.index.tolist()
        values = sector_perf.values.tolist()

        fig.add_trace(
            go.Heatmap(
                z=[values],
                x=sectors,
                y=['Perf Year'],
                colorscale='RdYlGn',
                name='Sector Performance'
            ),
            row=2, col=1
        )

    # Volatility scatter
    vol_data = df.dropna(subset=['Beta', 'Volatility M'])

    fig.add_trace(
        go.Scatter(
            x=vol_data['Beta'],
            y=vol_data['Volatility M'],
            mode='markers',
            name='Volatility Analysis',
            marker=dict(size=6, color='lightblue'),
            text=vol_data['Ticker'],
            hovertemplate='<b>%{text}</b><br>Beta: %{x:.2f}<br>Volatility: %{y:.1f}%<extra></extra>'
        ),
        row=2, col=2
    )

    # Update layout
    fig.update_layout(
        title='Financial Analysis Dashboard',
        width=1200,
        height=800,
        font=dict(size=CHART_CONFIG['font_size']),
        title_font=dict(size=CHART_CONFIG['title_font_size']),
        showlegend=False
    )

    # Update axes
    fig.update_xaxes(title_text="P/E Ratio", row=1, col=1)
    fig.update_yaxes(title_text="P/B Ratio", row=1, col=1)
    fig.update_xaxes(title_text="Market Cap ($B)", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=1, col=2)
    fig.update_xaxes(title_text="Beta", row=2, col=2)
    fig.update_yaxes(title_text="Monthly Volatility (%)", row=2, col=2)

    logger.info("Created comprehensive financial dashboard")
    return fig


def save_visualization(fig, filename, format='html'):
    """
    Save a visualization to file.

    Args:
        fig (plotly.graph_objects.Figure): Plotly figure to save
        filename (str): Output filename (without extension)
        format (str): Output format ('html', 'png', 'svg', 'pdf')

    Returns:
        str: Path to saved file
    """
    if format.lower() == 'html':
        output_file = f"{filename}.html"
        fig.write_html(output_file)
    else:
        output_file = f"{filename}.{format}"
        fig.write_image(output_file)

    logger.info(f"Saved visualization to {output_file}")
    return output_file


# Convenience functions for common use cases
def analyze_value_stocks(df, save_path=None):
    """
    Create a comprehensive value investing analysis.

    Args:
        df (pd.DataFrame): Financial data DataFrame
        save_path (str, optional): Path to save HTML file

    Returns:
        plotly.graph_objects.Figure: Value analysis dashboard
    """
    fig = create_pe_pb_scatter(df, color_by='Sector', size_by='Market Cap')
    if save_path:
        save_visualization(fig, save_path, 'html')
    return fig


def analyze_growth_stocks(df, save_path=None):
    """
    Create analysis focused on growth metrics.

    Args:
        df (pd.DataFrame): Financial data DataFrame
        save_path (str, optional): Path to save HTML file

    Returns:
        plotly.graph_objects.Figure: Growth analysis dashboard
    """
    # Focus on growth metrics like EPS growth, sales growth, etc.
    fig = create_sector_performance_heatmap(df, metric='EPS Next 5Y')
    if save_path:
        save_visualization(fig, save_path, 'html')
    return fig
