from datetime import date

import pytest

from systrade.data.calendar import nyse_sessions


def test_weekend_is_not_a_session() -> None:
    assert nyse_sessions(date(2024, 6, 8), date(2024, 6, 9)) == ()


def test_reversed_range_is_empty() -> None:
    assert nyse_sessions(date(2024, 6, 5), date(2024, 6, 3)) == ()


def test_inclusive_weekday() -> None:
    monday = date(2024, 6, 3)
    assert nyse_sessions(monday, monday) == (monday,)


@pytest.mark.parametrize(
    "closed",
    [
        date(2024, 1, 1),  # New Year's Day
        date(2024, 1, 15),  # MLK
        date(2024, 2, 19),  # Washington's Birthday
        date(2024, 3, 29),  # Good Friday
        date(2024, 5, 27),  # Memorial Day
        date(2024, 6, 19),  # Juneteenth
        date(2024, 7, 4),  # Independence Day
        date(2024, 9, 2),  # Labor Day
        date(2024, 11, 28),  # Thanksgiving
        date(2024, 12, 25),  # Christmas
        date(2020, 7, 3),  # Independence Day observed, Saturday the 4th
        date(2021, 7, 5),  # Independence Day observed, Sunday the 4th
        date(2021, 12, 24),  # Christmas observed
        date(2021, 12, 31),  # New Year 2022 observed
        date(2022, 6, 20),  # Juneteenth observed (the 19th was a Sunday)
        date(2023, 1, 2),  # New Year observed
        date(2023, 4, 7),  # Good Friday
    ],
)
def test_standard_holidays_are_closed(closed: date) -> None:
    assert nyse_sessions(closed, closed) == ()


@pytest.mark.parametrize(
    "open_day",
    [
        date(2024, 11, 29),  # day after Thanksgiving is an early close, not a closure
        date(2021, 6, 21),  # Juneteenth was not an NYSE holiday yet
        date(2020, 7, 2),
        date(2021, 7, 6),
        date(2024, 6, 18),
    ],
)
def test_nearby_weekdays_stay_open(open_day: date) -> None:
    assert nyse_sessions(open_day, open_day) == (open_day,)


@pytest.mark.parametrize(
    ("year", "good_friday"),
    [
        (2020, date(2020, 4, 10)),
        (2021, date(2021, 4, 2)),
        (2022, date(2022, 4, 15)),
        (2023, date(2023, 4, 7)),
        (2024, date(2024, 3, 29)),
        (2025, date(2025, 4, 18)),
        (2026, date(2026, 4, 3)),
    ],
)
def test_good_friday(year: int, good_friday: date) -> None:
    assert good_friday.year == year
    assert nyse_sessions(good_friday, good_friday) == ()
