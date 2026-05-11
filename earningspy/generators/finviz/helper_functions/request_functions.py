import logging
import os
from typing import Callable, Dict, List, Optional

import requests
import tenacity
import urllib3
from lxml import html
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from user_agent import generate_user_agent

from earningspy.generators.finviz.config import connection_settings
from earningspy.generators.finviz.constants import FINVIZ_HEADERS
from earningspy.generators.finviz.helper_functions.error_handling import ConnectionTimeout

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


FINVIZ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",

    "Sec-CH-UA": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _get_retry_strategy(total=3, backoff_factor=0.3, status_forcelist=None):
    """Create a Retry strategy with exponential backoff for rate limits and server errors."""
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]
    
    return Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_status=False,
        raise_on_redirect=False,
    )


def _create_session(timeout=10):
    """Create a requests session with connection pooling and retry strategy."""
    session = requests.Session()
    retry_strategy = _get_retry_strategy()
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=20)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def http_request_get(
    url, session=None, payload=None, parse=True, user_agent=generate_user_agent(), timeout=10
):
    """ Sends a GET HTTP request to a website and returns its HTML content and full url address.
    
    Args:
        url: Target URL
        session: Optional requests.Session for connection pooling
        payload: Query parameters
        parse: Whether to parse response as HTML
        user_agent: User-Agent header (kept for backward compatibility)
        timeout: Request timeout in seconds (default 10)
    
    Returns:
        Tuple of (content, url) where content is parsed HTML or text
        
    Raises:
        ConnectionTimeout: On timeout or connection errors
    """
    if payload is None:
        payload = {}

    try:
        if session:
            content = session.get(
                url,
                params=payload,
                verify=False,
                headers=FINVIZ_HEADERS,
                timeout=timeout,
            )
        else:
            # Fallback: create a one-off session if not provided
            fallback_session = _create_session()
            try:
                content = fallback_session.get(
                    url,
                    params=payload,
                    verify=False,
                    headers=FINVIZ_HEADERS,
                    timeout=timeout,
                )
            finally:
                fallback_session.close()

        content.raise_for_status()
        logger.debug(f"Successfully fetched {url} (status={content.status_code}, content-length={len(content.text)})")
        
        if parse:
            return html.fromstring(content.text), content.url
        else:
            return content.text, content.url
            
    except requests.exceptions.Timeout as e:
        logger.warning(f"Timeout fetching {url}: {e}")
        raise ConnectionTimeout(url)
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error fetching {url}: {e}")
        raise ConnectionTimeout(url)
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP error {e.response.status_code} fetching {url}")
        raise


def finviz_request(url: str, user_agent: str, session: Optional[requests.Session] = None, timeout: int = 10) -> Response:
    """Fetch URL with retry and timeout. Wraps http_request_get for backward compatibility.
    
    .. deprecated:: Use http_request_get directly with a session for better pooling.
    """
    logger.debug(f"Finviz request: {url}")
    try:
        content, _ = http_request_get(url, session=session, parse=False, timeout=timeout)
        return type('Response', (), {'text': content, 'status_code': 200})()
    except ConnectionTimeout as e:
        logger.error(f"Finviz request failed after retries: {url}")
        raise


def sequential_data_scrape(
    scrape_func: Callable, urls: List[str], user_agent: str, *args, session: Optional[requests.Session] = None, timeout: int = 10, **kwargs
) -> List[Dict]:
    """Scrape multiple URLs sequentially with logging progress.
    
    Args:
        scrape_func: Function to scrape response
        urls: List of URLs to scrape
        user_agent: User-Agent header
        session: Optional requests.Session for connection pooling
        timeout: Request timeout in seconds
        *args, **kwargs: Additional arguments for scrape_func
        
    Returns:
        List of scraped data
    """
    data = []
    total = len(urls)
    session = session or _create_session()
    
    try:
        for idx, url in enumerate(urls, 1):
            try:
                logger.info(f"Scraping {idx}/{total}: {url}")
                response = finviz_request(url, user_agent, session=session, timeout=timeout)
                
                # Check for empty or suspicious responses
                if not response.text or len(response.text.strip()) < 100:
                    logger.warning(f"Suspiciously short response from {url} (length: {len(response.text)}). Anti-scraping measures may be active.")
                    logger.debug(f"Response content: {response.text[:500]}...")
                
                kwargs["URL"] = url
                data.append(scrape_func(response, *args, **kwargs))
            except Exception as exc:
                logger.error(f"Failed to scrape {url}: {exc}")
                raise
    finally:
        if session:
            session.close()

    return data
