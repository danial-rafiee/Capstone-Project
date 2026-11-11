"""B-only tests: period boundaries, data quality and reference comparisons."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from smart_energy.analytics import Building, Meter, Reading, EnergySettings
from smart_energy.analytics.database import Database
from smart_energy.analytics.period_analytics import PeriodAnalyticsService, to_json_ready
from smart_energy.analytics.reading_repository import ReadingRepository
from smart_energy.analytics.time_window import TimeWindow


@pytest.fixture
def case():
    building = Building(1, "Office")
    meter = Meter(101, building, "Meter")
    service = PeriodAnalyticsService(EnergySettings(
        building, Decimal("0.30"), Decimal("0.40"), Decimal("0.10")))
    start = datetime(2026, 11, 4, 9, tzinfo=timezone.utc)
    def reading(offset, minutes, energy):
        a = start + timedelta(minutes=offset)
        return Reading(meter, a, a + timedelta(minutes=minutes), Decimal(energy))
    return meter, service, start, reading


def test_full_period_totals_and_series_are_chronological(case):
    meter, service, start, make = case
    result = service.summarize(meter, [make(5, 5, '2'), make(0, 5, '3')],
                               TimeWindow(start, start + timedelta(minutes=10)))
    assert result['status'] == 'complete'
    assert result['energy_kwh'] == Decimal('5')
    assert result['estimated_cost_eur'] == Decimal('1.50')
    assert result['estimated_co2_kg'] == Decimal('2.00')
    assert result['coverage_fraction'] == 1
    assert result['gaps'] == []
    assert result['series'][0]['start'] == start
    assert result['series'][0]['average_power_kw'] == Decimal('36')
    assert result['energy_estimated'] is False


def test_crossing_interval_is_prorated_and_marked_estimated(case):
    meter, service, start, make = case
    source = make(0, 10, '10')
    result = service.summarize(meter, [source], TimeWindow(
        start + timedelta(minutes=2), start + timedelta(minutes=7)))
    assert result['energy_kwh'] == Decimal('5')
    assert result['energy_estimated'] is True
    assert result['status'] == 'complete'
    assert source.get_energy_kwh() == Decimal('10')
    assert source.get_interval() == (start, start + timedelta(minutes=10))


def test_gaps_do_not_get_filled_or_extrapolated(case):
    meter, service, start, make = case
    result = service.summarize(meter, [make(2, 2, '3'), make(6, 2, '1')],
                               TimeWindow(start, start + timedelta(minutes=10)))
    assert result['status'] == 'partial'
    assert result['energy_kwh'] == Decimal('4')
    assert result['coverage_fraction'] == Decimal('0.4')
    assert [(g['start'], g['end']) for g in result['gaps']] == [
        (start, start + timedelta(minutes=2)),
        (start + timedelta(minutes=4), start + timedelta(minutes=6)),
        (start + timedelta(minutes=8), start + timedelta(minutes=10))]


def test_half_open_boundaries_exclude_adjacent_outside_readings(case):
    meter, service, start, make = case
    result = service.summarize(meter, [make(-5, 5, '9'), make(0, 5, '2'), make(5, 5, '9')],
                               TimeWindow(start, start + timedelta(minutes=5)))
    assert result['reading_count'] == 1
    assert result['energy_kwh'] == Decimal('2')


def test_no_data_is_null_and_distinct_from_measured_zero(case):
    meter, service, start, make = case
    window = TimeWindow(start, start + timedelta(minutes=5))
    missing = service.summarize(meter, [], window)
    zero = service.summarize(meter, [make(0, 5, '0')], window)
    assert missing['status'] == 'no_data' and missing['energy_kwh'] is None
    assert missing['estimated_cost_eur'] is None and missing['estimated_co2_kg'] is None
    assert zero['status'] == 'complete' and zero['energy_kwh'] == 0


def test_duplicate_or_overlapping_readings_still_fail(case):
    meter, service, start, make = case
    with pytest.raises(ValueError, match='overlapping'):
        service.summarize(meter, [make(0, 5, '2'), make(3, 5, '1')],
                          TimeWindow(start, start + timedelta(minutes=10)))


def test_wrong_meter_is_rejected_even_with_same_building(case):
    meter, service, start, _ = case
    other = Meter(102, meter.get_building(), 'Other')
    with pytest.raises(ValueError, match='supplied Meter'):
        service.summarize(meter, [Reading(other, start, start + timedelta(minutes=5), Decimal(1))],
                          TimeWindow(start, start + timedelta(minutes=5)))


def test_wrong_building_is_rejected_even_when_no_readings(case):
    _, service, start, _ = case
    other = Meter(102, Building(2, 'Other'), 'Other')
    with pytest.raises(ValueError, match='same Building'):
        service.summarize(other, [], TimeWindow(start, start + timedelta(minutes=5)))


def test_window_normalizes_offsets_and_preserves_microseconds(case):
    _, _, start, _ = case
    offset = timezone(timedelta(hours=2))
    window = TimeWindow(start.astimezone(offset), start + timedelta(microseconds=1))
    assert window.start == start
    assert window.start.tzinfo is timezone.utc
    assert window.seconds == Decimal('0.000001')


@pytest.mark.parametrize('end_delta', [timedelta(0), timedelta(seconds=-1)])
def test_window_rejects_reversed_or_empty_intervals(case, end_delta):
    _, _, start, _ = case
    with pytest.raises(ValueError, match='later'):
        TimeWindow(start, start + end_delta)


def test_window_requires_aware_datetimes(case):
    _, _, start, _ = case
    with pytest.raises(ValueError, match='timezones'):
        TimeWindow(start.replace(tzinfo=None), start + timedelta(minutes=5))


def test_reference_comparison_reports_signed_savings(case):
    meter, service, start, make = case
    current_window = TimeWindow(start, start + timedelta(minutes=5))
    reference_window = TimeWindow(start - timedelta(minutes=5), start)
    result = service.compare(meter, [make(0, 5, '3')], [make(-5, 5, '2')],
                             current_window, reference_window)['comparison']
    assert result['status'] == 'ready'
    assert result['energy_saved_kwh'] == Decimal('-1')
    assert result['cost_saved_eur'] == Decimal('-0.30')
    assert result['co2_saved_kg'] == Decimal('-0.40')
    assert result['energy_saved_percent'] == Decimal('-50')


def test_missing_reference_disables_comparison(case):
    meter, service, start, make = case
    result = service.compare(meter, [make(0, 5, '3')], [],
                             TimeWindow(start, start + timedelta(minutes=5)),
                             TimeWindow(start - timedelta(minutes=5), start))
    assert result['comparison']['status'] == 'unavailable'
    assert result['comparison']['energy_saved_kwh'] is None


def test_zero_reference_has_no_percentage(case):
    meter, service, start, make = case
    result = service.compare(meter, [make(0, 5, '1')], [make(-5, 5, '0')],
                             TimeWindow(start, start + timedelta(minutes=5)),
                             TimeWindow(start - timedelta(minutes=5), start))
    assert result['comparison']['status'] == 'ready'
    assert result['comparison']['energy_saved_kwh'] == -1
    assert result['comparison']['energy_saved_percent'] is None


def test_comparison_requires_equal_duration_and_earlier_reference(case):
    meter, service, start, _ = case
    window = TimeWindow(start, start + timedelta(minutes=5))
    with pytest.raises(ValueError, match='equal durations'):
        service.compare(meter, [], [], window, TimeWindow(start-timedelta(minutes=10), start))
    with pytest.raises(ValueError, match='before or at'):
        service.compare(meter, [], [], window, window)


def test_json_output_keeps_exact_decimal_null_and_timestamps(case):
    meter, service, start, _ = case
    result = to_json_ready(service.summarize(meter, [], TimeWindow(start, start + timedelta(minutes=5))))
    assert result['energy_kwh'] is None
    assert result['coverage_fraction'] == '0'
    assert result['start'] == '2026-11-04T09:00:00+00:00'
    assert result['energy_estimated'] is False


def test_period_query_uses_parameters_and_rebuilds_shared_meter(case):
    meter, _, start, _ = case
    database = MagicMock(spec=Database)
    connection = database.connect.return_value
    cursor = connection.cursor.return_value
    cursor.fetchall.return_value = [(start.replace(tzinfo=None),
                                     (start + timedelta(minutes=5)).replace(tzinfo=None), Decimal('3'))]
    readings = ReadingRepository(database).list_for_period(meter, start, start + timedelta(minutes=5))
    sql, params = cursor.execute.call_args.args
    assert 'start_utc < %s AND end_utc > %s' in sql
    assert params == (101, (start + timedelta(minutes=5)).replace(tzinfo=None), start.replace(tzinfo=None))
    assert readings[0].get_meter() is meter
    assert readings[0].get_interval()[0].tzinfo is timezone.utc
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_invalid_query_window_does_not_open_database(case):
    meter, _, start, _ = case
    database = MagicMock(spec=Database)
    with pytest.raises(ValueError):
        ReadingRepository(database).list_for_period(meter, start, start)
    database.connect.assert_not_called()
