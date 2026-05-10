# Finviz Module Debugging Guide

This guide helps troubleshoot common issues with the Finviz screener scraper.

## Quick Start

Enable debug logging to see detailed scraper activity:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('earningspy.generators.finviz')
logger.setLevel(logging.DEBUG)
```

_Note: Code examples for debug logging configuration are also available in the module docstrings of `data.py` and `__init__.py`._

## Common Issues & Solutions

### 1. Function Hangs or Times Out

**Symptoms**: Scraping stops responding, eventually crashes with timeout.

**Debug Steps**:

1. Check logs for the last URL being scraped:

   ```bash
   grep "Scraping.*:" logs/finviz.log | tail -5
   ```

2. Enable debug logging to see request details:

   ```bash
   grep "Successfully fetched\|Timeout fetching\|Connection error" logs/finviz.log
   ```

3. Test individual URLs manually:
   ```python
   from earningspy.generators.finviz.helper_functions.request_functions import http_request_get
   response, url = http_request_get("https://finviz.com/screener.ashx?v=111&f=ind_solar")
   print(f"Status: {len(response)} chars")
   ```

**Common Causes**:

- Network issues (check internet connection)
- Finviz rate limiting (wait and retry)
- DNS resolution problems

### 2. Empty or Short Responses (Anti-Scraping)

**Symptoms**: Functions return no data, or crash with parsing errors.

**Debug Steps**:

1. Look for suspicious response warnings:

   ```bash
   grep "Suspiciously short response" logs/finviz.log
   ```

2. Check response content in debug logs:

   ```bash
   grep "Response content:" logs/finviz.log
   ```

3. Test headers manually:

   ```python
   import requests
   from earningspy.generators.finviz.constants import FINVIZ_HEADERS

   response = requests.get("https://finviz.com/screener.ashx?v=111", headers=FINVIZ_HEADERS)
   print(f"Status: {response.status_code}")
   print(f"Length: {len(response.text)}")
   print(f"Content: {response.text[:500]}")
   ```

**Solutions**:

- Update `FINVIZ_HEADERS` in `constants.py` with fresh User-Agent
- Check if Finviz added new anti-bot measures
- Consider using residential proxies if needed

### 3. HTML Structure Changes

**Symptoms**: Functions return empty data, no crashes but no results.

**Debug Steps**:

1. Check for selector failure warnings:

   ```bash
   grep "No.*found with selector" logs/finviz.log
   ```

2. Look at page structure debug info:

   ```bash
   grep "Page.*contains:\|Page text snippet" logs/finviz.log
   ```

3. Inspect current Finviz HTML manually:

   ```python
   import requests
   from earningspy.generators.finviz.constants import FINVIZ_HEADERS

   response = requests.get("https://finviz.com/screener.ashx?v=111&f=ind_solar", headers=FINVIZ_HEADERS)
   print(response.text[:2000])  # Inspect HTML structure
   ```

4. Test selectors manually:

   ```python
   from lxml import html
   from earningspy.generators.finviz.constants import SCRAPING_SELECTORS

   response = requests.get("https://finviz.com/screener.ashx?v=111&f=ind_solar", headers=FINVIZ_HEADERS)
   parsed = html.fromstring(response.text)

   # Test table rows selector
   rows = parsed.cssselect(SCRAPING_SELECTORS['table_rows'])
   print(f"Found {len(rows)} table rows")

   # Test pagination
   pages = parsed.cssselect(SCRAPING_SELECTORS['page_options'])
   print(f"Found {len(pages)} page options")
   ```

**Solutions**:

- Update selectors in `SCRAPING_SELECTORS` dictionary in `constants.py`
- Check Finviz website directly to see new HTML structure
- Update `total_rows_patterns` if pagination text changed

## Updating Selectors

When Finviz changes their HTML:

1. **Inspect the new HTML**:

   ```python
   # Get current HTML
   response = requests.get("https://finviz.com/screener.ashx?v=111&f=ind_solar", headers=FINVIZ_HEADERS)
   print(response.text)
   ```

2. **Find new selectors**:
   - Table rows: Look for `<tr>` elements containing stock data
   - Pagination: Look for `<option>` elements with page numbers
   - Headers: Look for `<th>` elements with column names

3. **Update constants.py**:

   ```python
   SCRAPING_SELECTORS = {
       'table_rows': 'tr.new-selector-here',
       'page_options': 'option.new-pagination-selector',
       # etc.
   }
   ```

4. **Test the changes**:
   ```python
   from earningspy.generators.finviz.data import get_by_earnings_date
   result = get_by_earnings_date('next_week')
   print(f"Found {len(result)} stocks")
   ```

## Logging Levels

- **INFO**: Normal operation progress
- **WARNING**: Potential issues (empty responses, selector failures)
- **ERROR**: Failures that stop operation
- **DEBUG**: Detailed internal state (enable for troubleshooting)

## Test Commands

Run specific tests to verify fixes:

```bash
# Test basic functionality
python -m pytest tests/generators/test_finviz.py::test_get_screener_data -v

# Test with debug logging
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
import pytest
pytest.main(['-v', 'tests/generators/test_finviz.py'])
"
```

## Emergency Fixes

If everything breaks:

1. **Check Finviz website**: Visit https://finviz.com manually to see if it's working
2. **Update User-Agent**: Get latest browser User-Agent and update `FINVIZ_HEADERS`
3. **Use different filters**: Test with simpler queries first
4. **Check network**: Ensure no VPN/proxy issues

## Monitoring

Add to production logging:

```python
# In production code
import logging
finviz_logger = logging.getLogger('earningspy.generators.finviz')
finviz_logger.setLevel(logging.WARNING)  # Only log warnings/errors

# Or for full monitoring
finviz_logger.setLevel(logging.INFO)
```

## Contact

If issues persist, check:

- Finviz terms of service changes
- Network/firewall blocking
- Python dependencies updates
- Finviz API changes (rare but possible)</content>
  <parameter name="filePath">/Users/administrador/Documents/Devs/earningspy/earningspy/generators/finviz/DEBUG.md
