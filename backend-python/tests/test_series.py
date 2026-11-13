from datetime import date, timedelta

import pytest

from app.engines import series as sr


def mk(vals, start=date(2024, 1, 1)):
    return [(start + timedelta(days=i), v) for i, v in enumerate(vals)]


def test_on_or_before():
    s = mk([1, 2, 3])
    assert sr.on_or_before(s, date(2024, 1, 2)) == (date(2024, 1, 2), 2)
    assert sr.on_or_before(s, date(2024, 1, 10)) == (date(2024, 1, 3), 3)
    assert sr.on_or_before(s, date(2023, 12, 31)) is None


def test_pct_change_and_cagr():
    assert sr.pct_change(100, 110) == pytest.approx(10.0)
    assert sr.pct_change(0, 5) is None
    assert sr.cagr(100, 121, 2) == pytest.approx(10.0)
    assert sr.cagr(-5, 10, 2) is None
    assert sr.cagr(100, 150, 0) is None


def test_drawdown_recovery():
    s = mk([100, 120, 90, 80, 100, 121, 110])
    dd = sr.max_drawdown(s)
    assert dd["peak"] == 120 and dd["trough"] == 80
    assert dd["fall_pct"] == pytest.approx((80 / 120 - 1) * 100)
    assert dd["trough_date"] == date(2024, 1, 4)
    assert dd["recovery_date"] == date(2024, 1, 6)  # first close >= 120
    assert dd["recovery_days"] == 2


def test_drawdown_not_recovered_and_monotonic():
    dd = sr.max_drawdown(mk([100, 90, 95]))
    assert dd["recovery_date"] is None and dd["recovery_days"] is None
    assert sr.max_drawdown(mk([1, 2, 3])) is None


def test_top_drawdowns_sorted():
    s = mk([100, 90, 100, 70, 100, 95, 101])
    tops = sr.top_drawdowns(s, 5)
    assert [round(t["fall_pct"]) for t in tops] == [-30, -10, -5]


def test_weekly_resample_last_point_is_last_date():
    s = [(date(2026, 10, 26) + timedelta(days=i), float(i)) for i in range(5)]  # Mon..Fri
    s += [(date(2026, 11, 2), 9.0)]
    w = sr.weekly_resample(s)
    assert w[0] == (date(2026, 10, 30), 4.0) and w[-1] == (date(2026, 11, 2), 9.0)


def test_rebase_and_calendar_returns():
    s = [(date(2023, 12, 29), 100.0), (date(2024, 12, 31), 110.0), (date(2025, 12, 31), 99.0)]
    out = sr.calendar_year_returns(s, [2024, 2025, 2026])
    assert out[2024] == pytest.approx(10.0) and out[2025] == pytest.approx(-10.0) and out[2026] is None
    rb = sr.rebase(s, [d for d, _ in s], 50.0)
    assert rb[0][1] == 50.0 and rb[1][1] == pytest.approx(55.0)


def test_avg_daily_traded_value():
    pts = [(date(2024, 1, 1) + timedelta(days=i), 10.0, 100) for i in range(25)]
    assert sr.avg_daily_traded_value(pts, 20) == 1000.0
    assert sr.avg_daily_traded_value(pts[:5], 20) is None
    assert sr.avg_daily_traded_value([(d, c, None) for d, c, _ in pts], 20) is None


def test_years_before_leap_day():
    assert sr.years_before(date(2024, 2, 29), 1) == date(2023, 2, 28)


def test_median():
    assert sr.median([3, 1, 2]) == 2 and sr.median([1, 2, 3, 4]) == 2.5 and sr.median([]) is None
