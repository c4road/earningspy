from earningspy.generators.finviz.helper_functions.request_functions import _loggable_url


SCREENER_URL = (
    "https://finviz.com/screener.ashx?v=152&t=AAPL%2CMSFT&f=earningsdate_thisweek"
    "&o=-marketcap&c=0%2C1%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10&r=21"
)


def test_loggable_url_strips_column_selector_and_keeps_other_params():
    result = _loggable_url(SCREENER_URL)

    assert "c=" not in result
    assert "r=21" in result
    assert "f=earningsdate_thisweek" in result
    assert "v=152" in result
    assert "t=AAPL%2CMSFT" in result
    assert "o=-marketcap" in result
    assert result.startswith("https://finviz.com/screener.ashx?")


def test_loggable_url_preserves_parameter_order():
    result = _loggable_url(SCREENER_URL)

    assert result == (
        "https://finviz.com/screener.ashx?v=152&t=AAPL%2CMSFT"
        "&f=earningsdate_thisweek&o=-marketcap&r=21"
    )


def test_loggable_url_is_noop_without_column_param():
    url = "https://finviz.com/screener.ashx?v=152&r=41"

    assert _loggable_url(url) == url


def test_loggable_url_falls_back_to_original_on_bad_input():
    class Weird:
        def __str__(self):
            return "weird"

    weird = Weird()

    assert _loggable_url(weird) is weird
