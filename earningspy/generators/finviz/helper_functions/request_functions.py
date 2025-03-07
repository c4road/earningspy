import asyncio
import os
from typing import Callable, Dict, List
import random

import aiohttp
import requests
import tenacity
import urllib3
from lxml import html
from requests import Response
from tqdm import tqdm
from user_agent import generate_user_agent

from earningspy.generators.finviz.config import connection_settings
from earningspy.generators.finviz.helper_functions.error_handling import ConnectionTimeout

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def http_request_get(
    url, session=None, payload=None, parse=True, user_agent=generate_user_agent()
):
    """ Sends a GET HTTP request to a website and returns its HTML content and full url address. """

    if payload is None:
        payload = {}

    try:
        if session:
            content = session.get(
                url,
                params=payload,
                verify=False,
                headers={"User-Agent": user_agent},
            )
        else:
            content = requests.get(
                url,
                params=payload,
                verify=False,
                headers={"User-Agent": user_agent},
            )

        content.raise_for_status()  # Raise HTTPError for bad requests (4xx or 5xx)
        if parse:
            return html.fromstring(content.text), content.url
        else:
            return content.text, content.url
    except (asyncio.TimeoutError, requests.exceptions.Timeout):
        raise ConnectionTimeout(url)


@tenacity.retry(wait=tenacity.wait_exponential())
def finviz_request(url: str, user_agent: str) -> Response:
    response = requests.get(url, headers={"User-Agent": user_agent})
    if response.text == "Too many requests.":
        raise Exception("Too many requests.")
    return response


def sequential_data_scrape(
    scrape_func: Callable, urls: List[str], user_agent: str, *args, **kwargs
) -> List[Dict]:
    data = []

    for url in tqdm(urls, disable="DISABLE_TQDM" in os.environ):
        try:
            response = finviz_request(url, user_agent)
            kwargs["URL"] = url
            data.append(scrape_func(response, *args, **kwargs))
        except Exception as exc:
            raise exc

    return data


class Connector:
    """ Used to make asynchronous HTTP requests. """

    def __init__(
        self,
        scrape_function: Callable,
        urls: List[str],
        user_agent: str,
        *args,
        css_select: bool = False
    ):
        self.scrape_function = scrape_function
        self.urls = urls
        self.user_agent = user_agent
        self.arguments = args
        self.css_select = css_select
        self.data = []

    async def __http_request__async(
        self,
        url: str,
        session: aiohttp.ClientSession,
        *args,
        **kwargs
    ):
        """ Sends asynchronous http request to URL address and scrapes the webpage. """
        semaphore = asyncio.Semaphore(3)
        USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0",
        ]

        try:
            async with semaphore:
                asyncio.sleep(random.uniform(1, 3)) 
                async with session.get(
                    url, headers={"User-Agent": random.choice(USER_AGENTS)}
                ) as response:
                    page_html = await response.read()

                    if page_html.decode("utf-8") == "Too many requests.":
                        raise Exception("Too many requests.")
                    
                    if (page_html.decode("utf-8") == "This IP address has performed an unusual high number of " 
                                                     "requests and has been temporarily rate limited. If you " 
                                                     "believe this to be in error, please contact us."):
                        raise Exception("Unusual high number of requests")
    
                    if self.css_select:
                        return self.scrape_function(
                            html.fromstring(page_html), *self.arguments, **kwargs
                        )
                    return self.scrape_function(page_html.decode("utf-8"), *self.arguments, **kwargs)
        except (asyncio.TimeoutError, requests.exceptions.Timeout):
            raise ConnectionTimeout(url)

    async def __async_scraper(self, *args, **kwargs):
        """ Adds a URL's into a list of tasks and requests their response asynchronously. """

        async_tasks = []
        conn = aiohttp.TCPConnector(
            limit_per_host=connection_settings["CONCURRENT_CONNECTIONS"]
        )
        timeout = aiohttp.ClientTimeout(total=connection_settings["CONNECTION_TIMEOUT"])

        async with aiohttp.ClientSession(
            connector=conn, timeout=timeout, headers={"User-Agent": self.user_agent}
        ) as session:
            for url in self.urls:
                kwargs['URL'] = url
                async_tasks.append(self.__http_request__async(url, session, *args, **kwargs))

            self.data = await asyncio.gather(*async_tasks)

    def run_connector(self):
        """ Starts the asynchronous loop and returns the scraped data. """
        asyncio.set_event_loop(asyncio.SelectorEventLoop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.__async_scraper())
        return self.data
