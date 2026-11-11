"""B's off-hours allocation: local calendars, missing data and DST boundaries."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from smart_energy.analytics import Building, Meter, Reading, EnergySettings
from smart_energy.analytics.operating_schedule import OperatingSchedule
from smart_energy.analytics.period_analytics import PeriodAnalyticsService, to_json_ready
from smart_energy.analytics.time_window import TimeWindow


@pytest.fixture
def setup():
    building = Building(1, 'Office')
    meter = Meter(101, building, 'Meter')
    settings = EnergySettings(building, Decimal('.30'), Decimal('.40'), Decimal('.10'))
    schedule = OperatingSchedule('Europe/Berlin', {day: [('09:00', '17:00')] for day in range(5)})
    return meter, settings, schedule


def local(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo('Europe/Berlin'))


def summarize(setup, start, end, energy='6', schedule=None):
    meter, settings, default = setup
    service = PeriodAnalyticsService(settings, default if schedule is None else schedule)
    return service.summarize(meter, [Reading(meter, start, end, Decimal(energy))], TimeWindow(start, end))


def test_split_at_opening_boundary_conserves_energy_and_marks_estimate(setup):
    result = summarize(setup, local(2026, 11, 4, 8, 30), local(2026, 11, 4, 9, 30))
    assert result['energy_kwh'] == 6
    assert result['off_hours_energy_kwh'] == 3
    assert result['occupied_energy_kwh'] == 3
    assert result['off_hours_energy_estimated'] is True
    assert result['energy_estimated'] is False
    assert result['off_hours_status'] == 'complete'
    assert result['off_hours_coverage_fraction'] == 1


def test_close_boundary_is_off_hours_and_open_boundary_is_occupied(setup):
    occupied = summarize(setup, local(2026, 11, 4, 9), local(2026, 11, 4, 17))
    closed = summarize(setup, local(2026, 11, 4, 17), local(2026, 11, 4, 18))
    assert occupied['off_hours_energy_kwh'] == 0
    assert occupied['off_hours_coverage_fraction'] is None
    assert occupied['off_hours_energy_estimated'] is False
    assert closed['off_hours_energy_kwh'] == 6
    assert closed['occupied_energy_kwh'] == 0
    assert closed['off_hours_energy_estimated'] is False


def test_weekend_is_entirely_off_hours(setup):
    result = summarize(setup, local(2026, 11, 7, 9), local(2026, 11, 7, 17))
    assert result['off_hours_energy_kwh'] == result['energy_kwh'] == 6
    assert result['off_hours_energy_estimated'] is False


def test_explicit_closed_date_overrides_weekly_opening(setup):
    schedule = OperatingSchedule('Europe/Berlin', {2: [('09:00', '17:00')]},
                                 closed_dates=[date(2026, 11, 4)])
    result = summarize(setup, local(2026, 11, 4, 9), local(2026, 11, 4, 17), schedule=schedule)
    assert result['off_hours_energy_kwh'] == 6
    assert result['operating_schedule']['closed_dates'] == ['2026-11-04']


def test_multiple_open_intervals_leave_lunch_as_off_hours(setup):
    schedule = OperatingSchedule('Europe/Berlin', {2: [('09:00', '12:00'), ('13:00', '17:00')]})
    result = summarize(setup, local(2026, 11, 4, 11), local(2026, 11, 4, 14),
                       energy='9', schedule=schedule)
    assert result['off_hours_energy_kwh'] == 3
    assert result['occupied_energy_kwh'] == 6


@pytest.mark.parametrize('month, day, utc_open', [(1, 7, 8), (7, 1, 7)])
def test_weekly_local_opening_tracks_winter_and_summer_offsets(setup, month, day, utc_open):
    _, _, schedule = setup
    window = TimeWindow(datetime(2026, month, day, tzinfo=timezone.utc),
                        datetime(2026, month, day+1, tzinfo=timezone.utc))
    intervals = schedule.occupied_intervals(window)
    assert intervals == [(datetime(2026, month, day, utc_open, tzinfo=timezone.utc),
                          datetime(2026, month, day, utc_open+8, tzinfo=timezone.utc))]


@pytest.mark.parametrize('month, day, hours', [(3, 29, 23), (10, 25, 25)])
def test_all_day_open_schedule_measures_actual_dst_elapsed_time(month, day, hours):
    schedule = OperatingSchedule('Europe/Berlin', {6: [('00:00', '24:00')]})
    start = local(2026, month, day)
    end = local(2026, month, day+1)
    window = TimeWindow(start, end)
    assert window.seconds == hours * 3600
    assert schedule.occupied_seconds(window) == window.seconds


@pytest.mark.parametrize('month, day', [(3, 29), (10, 25)])
def test_ambiguous_or_missing_dst_boundaries_are_rejected(month, day):
    schedule = OperatingSchedule('Europe/Berlin', {6: [('02:30', '04:00')]})
    with pytest.raises(ValueError, match='timezone transition'):
        schedule.occupied_intervals(TimeWindow(local(2026, month, day), local(2026, month, day+1)))


def test_partial_off_hours_data_is_not_filled_with_zero(setup):
    meter, settings, schedule = setup
    start, end = local(2026, 11, 4, 7), local(2026, 11, 4, 9)
    readings = [Reading(meter, start, start + timedelta(hours=1), Decimal(2))]
    result = PeriodAnalyticsService(settings, schedule).summarize(meter, readings, TimeWindow(start, end))
    assert result['off_hours_status'] == result['status'] == 'partial'
    assert result['off_hours_energy_kwh'] == 2
    assert result['off_hours_coverage_fraction'] == Decimal('.5')


def test_empty_data_and_missing_calendar_have_distinct_null_results(setup):
    meter, settings, schedule = setup
    window = TimeWindow(local(2026, 11, 4, 8), local(2026, 11, 4, 9))
    missing = PeriodAnalyticsService(settings, schedule).summarize(meter, [], window)
    unconfigured = PeriodAnalyticsService(settings).summarize(meter, [], window)
    assert missing['off_hours_status'] == 'no_data'
    assert missing['off_hours_energy_kwh'] is None
    assert unconfigured['off_hours_status'] == 'not_configured'
    assert unconfigured['off_hours_energy_kwh'] is None
    assert unconfigured['operating_schedule'] is None


def test_window_clipping_and_schedule_splitting_use_original_interval_power(setup):
    meter, settings, schedule = setup
    start, end = local(2026, 11, 4, 8), local(2026, 11, 4, 10)
    result = PeriodAnalyticsService(settings, schedule).summarize(
        meter, [Reading(meter, start, end, Decimal(8))],
        TimeWindow(local(2026, 11, 4, 8, 30), local(2026, 11, 4, 9, 30)))
    assert result['energy_kwh'] == 4
    assert result['off_hours_energy_kwh'] == 2
    assert result['occupied_energy_kwh'] == 2
    assert result['energy_estimated'] and result['off_hours_energy_estimated']


def test_reference_comparison_keeps_off_hours_available_for_both_periods(setup):
    meter, settings, schedule = setup
    now = TimeWindow(local(2026, 11, 4, 8), local(2026, 11, 4, 10))
    before = TimeWindow(local(2026, 11, 3, 8), local(2026, 11, 3, 10))
    result = PeriodAnalyticsService(settings, schedule).compare(
        meter, [Reading(meter, now.start, now.end, Decimal(8))],
        [Reading(meter, before.start, before.end, Decimal(10))], now, before)
    assert result['current']['off_hours_energy_kwh'] == 4
    assert result['reference']['off_hours_energy_kwh'] == 5
    assert to_json_ready(result)['current']['operating_schedule']['timezone'] == 'Europe/Berlin'
    assert result['score_inputs'] == {
        'current_energy': Decimal(8), 'reference_energy': Decimal(10), 'off_hours_energy': Decimal(4)}
    assert result['score_allowance_share'] == Decimal('.10')
    assert result['score_inputs_status'] == 'ready'
    assert result['score_inputs_estimated'] is True


@pytest.mark.parametrize('current_energy, reference_energy', [('0', '2'), ('2', '0')])
def test_zero_energy_comparison_is_distinct_from_unavailable_score(setup, current_energy, reference_energy):
    meter, settings, schedule = setup
    now = TimeWindow(local(2026, 11, 4, 8), local(2026, 11, 4, 9))
    before = TimeWindow(local(2026, 11, 3, 8), local(2026, 11, 3, 9))
    result = PeriodAnalyticsService(settings, schedule).compare(
        meter, [Reading(meter, now.start, now.end, Decimal(current_energy))],
        [Reading(meter, before.start, before.end, Decimal(reference_energy))], now, before)
    assert result['comparison']['status'] == 'ready'
    assert result['score_inputs_status'] == 'unavailable'
    assert result['score_inputs'] is None


def test_no_schedule_does_not_supply_fake_zero_off_hours_to_scoring(setup):
    meter, settings, _ = setup
    now = TimeWindow(local(2026, 11, 4, 8), local(2026, 11, 4, 9))
    before = TimeWindow(local(2026, 11, 3, 8), local(2026, 11, 3, 9))
    result = PeriodAnalyticsService(settings).compare(
        meter, [Reading(meter, now.start, now.end, Decimal(2))],
        [Reading(meter, before.start, before.end, Decimal(3))], now, before)
    assert result['comparison']['status'] == 'ready'
    assert result['score_inputs'] is None


def test_missing_off_hours_measurements_disable_score_inputs(setup):
    meter, settings, schedule = setup
    now = TimeWindow(local(2026, 11, 4, 8), local(2026, 11, 4, 10))
    before = TimeWindow(local(2026, 11, 3, 8), local(2026, 11, 3, 10))
    result = PeriodAnalyticsService(settings, schedule).compare(
        meter, [Reading(meter, local(2026, 11, 4, 9), now.end, Decimal(2))],
        [Reading(meter, before.start, before.end, Decimal(3))], now, before)
    assert result['current']['off_hours_energy_kwh'] == 0
    assert result['current']['off_hours_coverage_fraction'] == 0
    assert result['score_inputs_status'] == 'unavailable'
    assert result['score_inputs'] is None


def test_adjacent_full_day_shifts_merge_across_midnight():
    schedule = OperatingSchedule('UTC', {0: [('00:00', '24:00')], 1: [('00:00', '24:00')]})
    start = datetime(2026, 11, 2, tzinfo=timezone.utc)
    window = TimeWindow(start, start + timedelta(days=2))
    assert schedule.occupied_intervals(window) == [(window.start, window.end)]


def test_schedule_isolated_from_caller_mutation():
    source = {2: [['09:00', '17:00']]}
    schedule = OperatingSchedule('Europe/Berlin', source)
    source[2][0][0] = '00:00'
    exported = schedule.to_dict()
    exported['weekly_hours']['2'][0][0] = '00:00'
    assert schedule.to_dict()['weekly_hours']['2'][0][0] == '09:00'


@pytest.mark.parametrize('hours', [
    {True: [('09:00', '17:00')]}, {7: []}, {2: [('17:00', '09:00')]},
    {2: [('09:00', '13:00'), ('12:00', '17:00')]},
    {2: [('9:00', '17:00')]}, {2: [('09:00', '24:01')]},
])
def test_invalid_schedules_are_rejected(hours):
    with pytest.raises(ValueError):
        OperatingSchedule('Europe/Berlin', hours)


def test_unknown_timezone_is_validation_error():
    with pytest.raises(ValueError, match='timezone'):
        OperatingSchedule('Not_A_Real_Timezone', {})
