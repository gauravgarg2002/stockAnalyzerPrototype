import pytest

from app.formatting import (format_count, format_date, format_days, format_inr, format_months, format_pct, format_pct_change, format_price,
                            format_times, format_unit, format_years, group_indian)

INR = [(0, "₹0"), (999, "₹999"), (42350.75, "₹42,351"), (99999.4, "₹99,999"), (99999.6, "₹1 lakh"), (120000, "₹1.2 lakh"), (1243500, "₹12.4 lakh"),
       (1250000, "₹12.5 lakh"), (9999999, "₹1 crore"), (34000000, "₹3.4 crore"), (8453000000, "₹845.3 crore"), (19321000000000, "₹19,32,100 crore"),
       (-45000, "-₹45,000")]


@pytest.mark.parametrize("x,exp", INR)
def test_inr(x, exp):
    assert format_inr(x) == exp


@pytest.mark.parametrize("x,exp", [(2410.5, "₹2,410.50"), (2.675, "₹2.68"), (1234567.891, "₹12,34,567.89")])
def test_price(x, exp):
    assert format_price(x) == exp


@pytest.mark.parametrize("fn,x,exp", [
    (format_pct, 12.345, "12.3%"), (format_pct, 0.05, "0.1%"), (format_pct, 1.25, "1.3%"), (format_pct, -2.34, "-2.3%"),
    (format_pct_change, 14.25, "+14.3%"), (format_pct_change, -4.1, "-4.1%"), (format_pct_change, 0, "0.0%"),
    (format_times, 24.06, "24.1x"), (format_count, 1234567, "12,34,567"),
    (format_years, 1, "1 year"), (format_years, 3, "3 years"), (format_years, 7.25, "7.3 years"),
    (format_days, 1, "1 day"), (format_days, 143, "143 days"), (format_months, 1, "1 month"), (format_months, 2, "2 months"),
])
def test_other_units(fn, x, exp):
    assert fn(x) == exp


def test_date():
    assert format_date("2026-10-30") == "30 Oct 2026"
    assert format_date("2026-01-05") == "5 Jan 2026"


def test_none_and_unit_dispatch():
    assert format_unit(None, "INR") == "Not available"
    assert format_unit("Yes", "TEXT") == "Yes"
    assert format_unit(3925.4, "INR_PRICE") == "₹3,925.40"
    assert format_unit(6, "COUNT") == "6"


def test_grouping():
    assert group_indian("1234567") == "12,34,567"
    assert group_indian("999") == "999"
    assert group_indian("1000") == "1,000"


def test_tiny_negative_has_no_minus_zero():
    assert format_pct(-0.04) == "0.0%"
    assert format_pct_change(-0.04) == "0.0%"
    assert format_inr(-0.3) == "₹0"
