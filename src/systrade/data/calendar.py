"""NYSE session calendar used to spot missing daily bars.

The rules are the standard full-day holiday schedule. One-off closures
(hurricanes, national days of mourning) are not included; ``docs/data.md``
says how to read a ``missing_session`` flag that comes from that gap.
Early closes are ordinary sessions: the market was open.
"""

from __future__ import annotations

from datetime import date, timedelta


def nyse_sessions(start: date, end: date) -> tuple[date, ...]:
    """Weekday sessions from ``start`` through ``end``, both inclusive."""
    if end < start:
        return ()
    closed: set[date] = set()
    for year in range(start.year - 1, end.year + 2):
        closed.update(nyse_holidays(year))
    sessions: list[date] = []
    day = start
    while day <= end:
        if day.weekday() < 5 and day not in closed:
            sessions.append(day)
        day += timedelta(days=1)
    return tuple(sessions)


def nyse_holidays(year: int) -> frozenset[date]:
    """Observed full-day NYSE holidays associated with ``year``.

    A Saturday 1 January is observed on 31 December of ``year - 1``, and that
    Friday is included in the set for ``year``. Callers that cover a December
    should also request the following year (``nyse_sessions`` does).
    """
    holidays = {
        _observed(date(year, 1, 1)),
        _nth_weekday(year, 2, 0, 3),  # Washington's Birthday, third Monday
        _good_friday(year),
        _last_weekday(year, 5, 0),  # Memorial Day, last Monday
        _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),  # Labor Day, first Monday
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving, fourth Thursday
        _observed(date(year, 12, 25)),
    }
    if year >= 1998:
        holidays.add(_nth_weekday(year, 1, 0, 3))  # Martin Luther King Jr. Day
    if year >= 2022:
        holidays.add(_observed(date(year, 6, 19)))  # Juneteenth
    return frozenset(holidays)


def _observed(day: date) -> date:
    """Saturday holidays move to Friday; Sunday holidays move to Monday."""
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The ``n``-th ``weekday`` in a month. Monday is 0. ``n`` is 1-based."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year, 12, 31) if month == 12 else date(year, month + 1, 1) - timedelta(days=1)
    offset = (last.weekday() - weekday) % 7
    return last - timedelta(days=offset)


def _good_friday(year: int) -> date:
    return _easter_sunday(year) - timedelta(days=2)


def _easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (Anonymous algorithm)."""
    year_mod_19 = year % 19
    century, year_in_century = divmod(year, 100)
    century_div_4, century_mod_4 = divmod(century, 4)
    leap_correction = (century + 8) // 25
    century_shift = (century - leap_correction + 1) // 3
    lunar = (19 * year_mod_19 + century - century_div_4 - century_shift + 15) % 30
    year_div_4, year_mod_4 = divmod(year_in_century, 4)
    weekday_shift = (32 + 2 * century_mod_4 + 2 * year_div_4 - lunar - year_mod_4) % 7
    extra = (year_mod_19 + 11 * lunar + 22 * weekday_shift) // 451
    month, day_index = divmod(lunar + weekday_shift - 7 * extra + 114, 31)
    return date(year, month, day_index + 1)
