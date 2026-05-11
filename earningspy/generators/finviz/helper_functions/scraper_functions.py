import datetime
import logging
import os
import time

import requests
from lxml import etree, html

from earningspy.generators.finviz.constants import SCRAPING_SELECTORS

logger = logging.getLogger(__name__)


def get_table(page_html: requests.Response, headers, rows=None, **kwargs):
    """ Private function used to return table data inside a list of dictionaries. """
    if isinstance(page_html, str):
        page_parsed = html.fromstring(page_html)
    else:
        page_parsed = html.fromstring(page_html.text)
    
    logger.debug(f"Parsing table from page content (length: {len(page_html.text if hasattr(page_html, 'text') else page_html)})")
    
    # When we call this method from Portfolio we don't fill the rows argument.
    # Conversely, we always fill the rows argument when we call this method from Screener.
    # Also, in the portfolio page, we don't need the last row - it's redundant.
    if rows is None:
        rows = -2  # We'll increment it later (-1) and use it to cut the last row

    data_sets = []
    # Select the HTML of the rows and append each column text to a list
    all_rows = [
        column.xpath("td//text()")
        for column in page_parsed.cssselect(SCRAPING_SELECTORS['table_rows'])
    ]
    
    logger.debug(f"Found {len(all_rows)} table rows using selector '{SCRAPING_SELECTORS['table_rows']}'")
    if not all_rows:
        logger.warning(f"No table rows found with selector '{SCRAPING_SELECTORS['table_rows']}'. Finviz may have changed their HTML structure.")
        # Log some debug info about the page structure
        body = page_parsed.cssselect('body')
        if body:
            logger.debug(f"Page body contains: {body[0].text_content()[:500]}...")
    
    # If rows is different from -2, this function is called from Screener
    if rows != -2:
        for row_number, row_data in enumerate(all_rows, 1):
            data_sets.append(dict(zip(headers, row_data)))
            if row_number == rows:  # If we have reached the required end
                break
    else:
        # Zip each row values to the headers and append them to data_sets
        [data_sets.append(dict(zip(headers, row))) for row in all_rows]

    logger.debug(f"Extracted {len(data_sets)} data rows from table")
    return data_sets


def get_total_rows(page_content):
    """ Returns the total number of rows(results). """
    logger.debug("Extracting total rows from page content")
    
    page_text = str(html.tostring(page_content))
    for option_beg, option_end in SCRAPING_SELECTORS['total_rows_patterns']:
        if option_beg in page_text:
            total_number = page_text.split(option_beg)[1].split(option_end)[0]
            try:
                total = int(total_number)
                logger.debug(f"Found total rows: {total} using pattern '{option_beg}'")
                return total
            except ValueError:
                logger.warning(f"Failed to parse total rows number '{total_number}' from pattern '{option_beg}'")
                return 0
    
    logger.warning("No total rows pattern matched. Finviz may have changed their pagination HTML.")
    logger.debug(f"Page text snippet around pagination: {page_text[page_text.find('count-text'):page_text.find('count-text')+200] if 'count-text' in page_text else 'No count-text found'}")
    return 0


def get_page_urls(page_content, rows, url):
    """ Returns a list containing all of the page URL addresses. """
    logger.debug(f"Extracting page URLs for {rows} rows")
    
    page_options = page_content.cssselect(SCRAPING_SELECTORS['page_options'])
    if not page_options:
        logger.warning(f"No page options found with selector '{SCRAPING_SELECTORS['page_options']}'. Finviz may have changed pagination.")
        return [url]  # fallback to single page
    
    total_pages = int(page_options[0].text.split("/")[1])
    logger.debug(f"Found {total_pages} total pages")
    
    urls = []
    for page_number in range(1, total_pages + 1):
        sequence = 1 + (page_number - 1) * 20
        if sequence - 20 <= rows < sequence:
            break
        urls.append(url + f"&r={str(sequence)}")

    logger.debug(f"Generated {len(urls)} page URLs")
    return urls


def download_chart_image(page_content: requests.Response, **kwargs):
    """ Downloads a .png image of a chart into the "charts" folder. """
    file_name = f"{kwargs['URL'].split('t=')[1]}_{int(time.time())}.png"

    if not os.path.exists("charts"):
        os.mkdir("charts")

    with open(os.path.join("charts", file_name), "wb") as handle:
        handle.write(page_content.content)


def get_analyst_price_targets_for_export(
    ticker=None, page_content=None, last_ratings=5
):
    analyst_price_targets = []
    logger.debug(f"Extracting analyst ratings for {ticker}")

    try:
        table = page_content.cssselect(SCRAPING_SELECTORS['analyst_ratings_table'])
        if not table:
            logger.warning(f"No analyst ratings table found with selector '{SCRAPING_SELECTORS['analyst_ratings_table']}' for {ticker}")
            return analyst_price_targets
        
        table = table[0]
        ratings_list = [row.xpath("td//text()") for row in table]
        ratings_list = [
            [val for val in row if val != "\n"] for row in ratings_list
        ]  # remove new line entries

        logger.debug(f"Found {len(ratings_list)} analyst rating rows for {ticker}")
        
        headers = [
            "ticker",
            "date",
            "category",
            "analyst",
            "rating",
            "price_from",
            "price_to",
        ]  # header names
        count = 0

        for row in ratings_list:
            if count == last_ratings:
                break

            price_from, price_to = (
                0,
                0,
            )  # default values for len(row) == 4 , that is there is NO price information
            if len(row) == 5:
                strings = row[4].split("→")
                if len(strings) == 1:
                    price_to = (
                        strings[0].strip(" ").strip("$")
                    )  # if only ONE price is available then it is 'price_to' value
                else:
                    price_from = (
                        strings[0].strip(" ").strip("$")
                    )  # both '_from' & '_to' prices available
                    price_to = strings[1].strip(" ").strip("$")

            elements = [
                ticker,
                datetime.datetime.strptime(row[0], "%b-%d-%y").strftime("%Y-%m-%d"),
            ]
            elements.extend(row[1:3])
            elements.append(row[3].replace("→", "->"))
            elements.append(price_from)
            elements.append(price_to)
            data = dict(zip(headers, elements))
            analyst_price_targets.append(data)
            count += 1
            
        logger.debug(f"Extracted {len(analyst_price_targets)} analyst ratings for {ticker}")
    except Exception as e:
        logger.warning(f"Failed to extract analyst ratings for {ticker}: {e}")

    return analyst_price_targets


def download_ticker_details(page_content: requests.Response, **kwargs):
    data = {}
    ticker = kwargs["URL"].split("=")[1]
    page_parsed = html.fromstring(page_content.text)

    all_rows = [
        row.xpath("td//text()")
        for row in page_parsed.cssselect('tr[class="table-dark-row"]')
    ]

    for row in all_rows:
        for column in range(0, 11):
            if column % 2 == 0:
                data[row[column]] = row[column + 1]

    if len(data) == 0:
        raise Exception(f"No data found for ticker: {ticker}")

    return {ticker: [data, get_analyst_price_targets_for_export(ticker, page_parsed)]}
