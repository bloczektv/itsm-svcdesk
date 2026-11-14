# ai-generated: 60% - Claude Code drafted the cases from the slaclock.py docstrings; I chose the boundaries and checked each expectation by hand
"""Behavioural tests for slaclock.py, aimed at the boundaries its docstrings state."""

from datetime import datetime, timedelta

import pytest

import slaclock as sc


def at(day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    """Nov 2026: day 14 is a Saturday, so 16 is Monday, 20 Friday, 21 Saturday."""
    return datetime(2026, 11, day, hour, minute, second)


# priority_of ---------------------------------------------------------------

@pytest.mark.parametrize(
    "impact, urgency, expected",
    [
        (1, 1, "P1"), (1, 2, "P2"), (2, 1, "P2"),
        (1, 3, "P3"), (2, 2, "P3"), (3, 1, "P3"),
        (2, 3, "P4"), (3, 2, "P4"), (3, 3, "P4"),
    ],
)
def test_priority_matrix_every_cell(impact, urgency, expected):
    assert sc.priority_of(impact, urgency) == expected


def test_vip_lifts_p3_and_p4_to_p2_but_keeps_p1_and_p2():
    assert sc.priority_of(1, 1, vip=True) == "P1"
    assert sc.priority_of(1, 2, vip=True) == "P2"
    assert sc.priority_of(1, 3, vip=True) == "P2"
    assert sc.priority_of(3, 3, vip=True) == "P2"


@pytest.mark.parametrize("impact, urgency", [(0, 1), (4, 1), (1, 0), (1, 4), (2.0, 1), (True, 1), ("1", 1)])
def test_out_of_range_or_wrong_type_raises(impact, urgency):
    with pytest.raises(ValueError):
        sc.priority_of(impact, urgency)


# targets -------------------------------------------------------------------

def test_targets_exact_values():
    assert sc.targets("P1") == (15, 240)
    assert sc.targets("P2") == (60, 480)
    assert sc.targets("P3") == (240, 1440)
    assert sc.targets("P4") == (480, 4320)


@pytest.mark.parametrize("bad", ["p1", " P1", "P5", "", "P0"])
def test_targets_lookup_is_exact(bad):
    with pytest.raises(ValueError):
        sc.targets(bad)


# sla_state -----------------------------------------------------------------

def test_sla_state_warning_starts_at_75_percent_without_rounding():
    assert sc.sla_state(11, 15) == "ok"        # 11 < 11.25
    assert sc.sla_state(12, 15) == "warning"
    assert sc.sla_state(3, 4) == "warning"     # exactly 75 %
    assert sc.sla_state(2, 4) == "ok"
    assert sc.sla_state(0, 10) == "ok"


def test_sla_state_equality_with_target_is_warning_not_breach():
    assert sc.sla_state(15, 15) == "warning"
    assert sc.sla_state(16, 15) == "breached"
    assert sc.sla_state(481, 480) == "breached"


def test_sla_state_threshold_is_exactly_75_percent():
    assert sc.sla_state(74, 100) == "ok"
    assert sc.sla_state(75, 100) == "warning"
    assert sc.sla_state(298, 400) == "ok"       # 74.5 %
    assert sc.sla_state(300, 400) == "warning"


def test_sla_state_smallest_valid_target():
    assert sc.sla_state(0, 1) == "ok"
    assert sc.sla_state(1, 1) == "warning"
    assert sc.sla_state(2, 1) == "breached"


@pytest.mark.parametrize("elapsed, target", [(-1, 10), (5, 0), (5, -3)])
def test_sla_state_rejects_bad_input(elapsed, target):
    with pytest.raises(ValueError):
        sc.sla_state(elapsed, target)


# is_business_time ----------------------------------------------------------

def test_business_window_is_half_open_08_to_16_on_weekdays():
    assert not sc.is_business_time(at(16, 7, 59))
    assert sc.is_business_time(at(16, 8, 0))
    assert sc.is_business_time(at(16, 15, 59))
    assert not sc.is_business_time(at(16, 16, 0))
    assert not sc.is_business_time(at(16, 16, 30))
    assert not sc.is_business_time(at(16, 7, 30))
    assert not sc.is_business_time(at(16, 0, 0))


def test_weekend_is_never_business_time():
    assert not sc.is_business_time(at(21, 10, 0))  # Saturday
    assert not sc.is_business_time(at(22, 10, 0))  # Sunday
    assert sc.is_business_time(at(20, 10, 0))      # Friday


# add_business_minutes ------------------------------------------------------

def test_add_business_minutes_inside_one_day():
    assert sc.add_business_minutes(at(16, 10), 60) == at(16, 11)


def test_target_ending_exactly_at_closing_is_due_that_day():
    assert sc.add_business_minutes(at(16, 15), 60) == at(16, 16)


def test_clock_spills_into_next_business_day():
    assert sc.add_business_minutes(at(16, 15, 30), 60) == at(17, 8, 30)


def test_friday_evening_skips_the_weekend():
    assert sc.add_business_minutes(at(20, 16, 0), 60) == at(23, 9, 0)


def test_saturday_start_moves_to_monday_opening():
    assert sc.add_business_minutes(at(21, 10, 0), 30) == at(23, 8, 30)


def test_before_opening_starts_at_opening():
    assert sc.add_business_minutes(at(16, 7, 0), 0) == at(16, 8, 0)


def test_zero_minutes_inside_hours_returns_start():
    assert sc.add_business_minutes(at(16, 10, 0), 0) == at(16, 10, 0)


def test_friday_is_a_business_day():
    assert sc.add_business_minutes(at(20, 10, 0), 60) == at(20, 11, 0)


def test_start_after_closing_moves_to_next_opening():
    assert sc.add_business_minutes(at(16, 17, 0), 60) == at(17, 9, 0)
    assert sc.add_business_minutes(at(16, 16, 0), 0) == at(17, 8, 0)


def test_last_minute_before_closing():
    assert sc.add_business_minutes(at(16, 15, 59), 1) == at(16, 16, 0)
    assert sc.add_business_minutes(at(16, 15, 59), 2) == at(17, 8, 1)


def test_seconds_of_start_are_ignored():
    assert sc.add_business_minutes(at(16, 10, 0, 45), 5) == at(16, 10, 5)


def _full_days_minutes(start: datetime, days: int) -> int:
    """480 for every weekday among the `days` calendar days from start's date on (start is at 08:00)."""
    return sum(480 for offset in range(days) if (start + timedelta(days=offset)).weekday() < 5)


def test_due_date_exactly_max_days_after_start_is_accepted():
    start = datetime(2026, 1, 5, 8, 0)                 # a Monday
    due = datetime(2027, 1, 6, 9, 0)                   # 366 days later, a Wednesday
    minutes = _full_days_minutes(start, 366) + 60
    assert sc.add_business_minutes(start, minutes) == due


def test_due_date_one_day_past_max_days_raises():
    start = datetime(2026, 1, 5, 8, 0)
    minutes = _full_days_minutes(start, 367) + 60      # due 2027-01-07 09:00, 367 days later
    with pytest.raises(ValueError):
        sc.add_business_minutes(start, minutes)


def test_negative_minutes_raise():
    with pytest.raises(ValueError):
        sc.add_business_minutes(at(16, 10), -1)


def test_due_date_beyond_max_days_raises():
    with pytest.raises(ValueError):
        sc.add_business_minutes(at(16, 8), 480 * 400)


# business_minutes_between --------------------------------------------------

def test_business_minutes_between_same_day():
    assert sc.business_minutes_between(at(16, 10), at(16, 11)) == 60
    assert type(sc.business_minutes_between(at(16, 10), at(16, 11))) is int
    assert sc.business_minutes_between(at(16, 10), at(16, 10)) == 0


def test_window_clipping_before_open_and_after_close():
    assert sc.business_minutes_between(at(16, 7, 0), at(16, 9, 0)) == 60
    assert sc.business_minutes_between(at(16, 15, 0), at(16, 18, 0)) == 60
    assert sc.business_minutes_between(at(16, 16, 0), at(16, 16, 30)) == 0


def test_weekend_and_overnight_are_skipped():
    assert sc.business_minutes_between(at(20, 15, 0), at(23, 9, 0)) == 120  # Fri 15:00 to Mon 09:00
    assert sc.business_minutes_between(at(16, 15, 0), at(17, 9, 0)) == 120
    assert sc.business_minutes_between(at(16, 17, 0), at(17, 9, 0)) == 60   # Monday after closing adds nothing
    assert sc.business_minutes_between(at(21, 9, 0), at(23, 9, 0)) == 60    # Saturday start
    assert sc.business_minutes_between(at(16, 8, 0), at(23, 8, 0)) == 5 * 480


def test_seconds_are_ignored():
    assert sc.business_minutes_between(at(16, 10, 0, 59), at(16, 11, 0, 30)) == 60


def test_end_before_start_raises():
    with pytest.raises(ValueError):
        sc.business_minutes_between(at(16, 11), at(16, 10))


def test_span_limit_is_366_days_inclusive():
    start = datetime(2026, 1, 1, 9, 0)
    assert sc.business_minutes_between(start, start + timedelta(days=366)) >= 0
    with pytest.raises(ValueError):
        sc.business_minutes_between(start, start + timedelta(days=367))


@pytest.mark.parametrize("start", [at(16, 10), at(16, 15, 30), at(20, 16, 0), at(21, 9, 0)])
@pytest.mark.parametrize("minutes", [0, 1, 59, 60, 480, 500, 1000])
def test_round_trip_between_and_add(start, minutes):
    due = sc.add_business_minutes(start, minutes)
    assert sc.business_minutes_between(start, due) == minutes


# escalation_tier -----------------------------------------------------------

@pytest.mark.parametrize("priority, expected", [("P1", 1), ("P2", 1), ("P3", 0), ("P4", 0)])
def test_escalation_when_not_breached(priority, expected):
    assert sc.escalation_tier(priority, False, 0) == expected


@pytest.mark.parametrize("priority, expected", [("P1", 3), ("P2", 2), ("P3", 1), ("P4", 1)])
def test_escalation_when_breached(priority, expected):
    assert sc.escalation_tier(priority, True, 0) == expected


def test_one_reopen_adds_nothing_two_reopens_add_one():
    assert sc.escalation_tier("P3", False, 1) == 0
    assert sc.escalation_tier("P3", False, 2) == 1
    assert sc.escalation_tier("P1", False, 2) == 2
    assert sc.escalation_tier("P1", True, 2) == 3   # capped at 3
    assert sc.escalation_tier("P3", False, 3) == 1
    assert sc.escalation_tier("P2", True, 5) == 3
    assert sc.escalation_tier("P4", True, 2) == 2


@pytest.mark.parametrize("priority, reopens", [("P5", 0), ("p1", 0), ("P1", -1)])
def test_escalation_rejects_bad_input(priority, reopens):
    with pytest.raises(ValueError):
        sc.escalation_tier(priority, False, reopens)


# parse_duration ------------------------------------------------------------

@pytest.mark.parametrize(
    "text, minutes",
    [
        ("90m", 90), ("4h", 240), ("1h30m", 90), ("2d", 2880), ("1d4h", 1680),
        ("1d0h5m", 1445), ("60m", 60), ("0h60m", 60), ("1h59m", 119), (" 15m ", 15),
        ("1m", 1), ("1d", 1440), ("1h", 60), ("1d1h1m", 1501), ("0d0h1m", 1), ("120m", 120),
    ],
)
def test_parse_duration_values(text, minutes):
    assert sc.parse_duration(text) == minutes


@pytest.mark.parametrize(
    "text",
    ["", "0m", "0d", "1.5h", "30m1h", "-5m", "1 h", "1h60m", "1h61m", "1d60m", "1d99m", "1H", "5s", "0h0m"],
)
def test_parse_duration_rejects(text):
    with pytest.raises(ValueError):
        sc.parse_duration(text)
