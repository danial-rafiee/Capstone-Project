"""Gap filling, preserved measurements and transaction safety for demo history."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from smart_energy.analytics import Building, Meter, Reading, EnergySettings
from smart_energy.analytics.demo_history import DemoHistoryGenerator, DemoHistorySeeder
from smart_energy.analytics.period_analytics import PeriodAnalyticsService
from smart_energy.analytics.time_window import TimeWindow
from seed_demo_history_b import load_database_env, resolve_end


@pytest.fixture
def sample():
    building = Building(1, "Demo Office")
    meter = Meter(101, building, "Main Meter")
    end = datetime(2026, 11, 12, 10, tzinfo=timezone.utc)
    window = TimeWindow(end-timedelta(days=60), end)
    rows = []
    for day, energies in ((3, ("3", "4")), (4, ("2", "3"))):
        start = datetime(2026, 11, day, 7, tzinfo=timezone.utc)
        rows.extend([Reading(meter, start, start+timedelta(hours=1), Decimal(energies[0])),
                     Reading(meter, start+timedelta(hours=1), start+timedelta(hours=2), Decimal(energies[1]))])
    start = datetime(2026, 11, 4, 9, tzinfo=timezone.utc)
    rows.extend([Reading(meter, start, start+timedelta(minutes=5), Decimal("3")),
                 Reading(meter, start+timedelta(minutes=5), start+timedelta(minutes=10), Decimal("2"))])
    return meter, window, rows


def test_fills_partial_hour_remainder_and_preserves_all_existing_rows(sample):
    meter, window, rows = sample
    original = [(r.get_interval(), r.get_energy_kwh()) for r in rows]
    generator = DemoHistoryGenerator()
    new = generator.plan(meter, rows, window)
    assert [(r.get_interval(), r.get_energy_kwh()) for r in rows] == original
    assert any(r.get_interval() == (
        datetime(2026,11,4,9,10,tzinfo=timezone.utc),
        datetime(2026,11,4,10,tzinfo=timezone.utc)) for r in new)
    analytics = PeriodAnalyticsService(EnergySettings(meter.get_building(), Decimal('.3'),
                                                     Decimal('.4'), Decimal('.1')), generator.schedule)
    assert analytics.summarize(meter, rows+new, window)["coverage_fraction"] == 1


def test_all_three_current_and_reference_periods_are_complete_and_scenario_survives(sample):
    meter, window, rows = sample
    generator = DemoHistoryGenerator()
    combined = rows + generator.plan(meter, rows, window)
    analytics = PeriodAnalyticsService(EnergySettings(meter.get_building(), Decimal('.3'),
                                                     Decimal('.4'), Decimal('.1')), generator.schedule)
    for days in (1, 7, 30):
        now = TimeWindow(window.end-timedelta(days=days), window.end)
        before = TimeWindow(now.start-timedelta(days=days), now.start)
        result = analytics.compare(meter, combined, combined, now, before)
        assert result["comparison"]["status"] == result["score_inputs_status"] == "ready"
        assert result["current"]["coverage_fraction"] == result["reference"]["coverage_fraction"] == 1
    now = TimeWindow(datetime(2026,11,4,7,tzinfo=timezone.utc), datetime(2026,11,4,9,tzinfo=timezone.utc))
    before = TimeWindow(now.start-timedelta(days=1), now.end-timedelta(days=1))
    assert analytics.compare(meter, combined, combined, now, before)["score_inputs"] == {
        "current_energy": Decimal(5), "reference_energy": Decimal(7), "off_hours_energy": Decimal(2)}


def test_rerun_is_idempotent_and_deterministic(sample):
    meter, window, rows = sample
    generator = DemoHistoryGenerator()
    a = generator.plan(meter, rows, window)
    b = generator.plan(meter, list(reversed(rows)), window)
    assert [(r.get_interval(),r.get_energy_kwh()) for r in a] == [
        (r.get_interval(),r.get_energy_kwh()) for r in b]
    assert generator.plan(meter, rows+a, window) == []


def test_existing_overlaps_are_rejected_instead_of_silently_merged(sample):
    meter, window, rows = sample
    with pytest.raises(ValueError, match="overlapping"):
        DemoHistoryGenerator().plan(meter, rows+[rows[0]], window)


def test_subsecond_gaps_and_existing_spanning_boundaries_remain_exact(sample):
    meter, window, _ = sample
    rows = [Reading(meter, window.start-timedelta(hours=1),
                    window.end-timedelta(microseconds=1), Decimal("100"))]
    new = DemoHistoryGenerator().plan(meter, rows, window)
    assert len(new) == 1
    assert new[0].get_interval() == (window.end-timedelta(microseconds=1), window.end)
    assert new[0].get_energy_kwh().as_tuple().exponent == -6


def test_business_hour_profile_and_dst_follow_local_calendar(sample):
    meter, _, _ = sample
    generator = DemoHistoryGenerator()
    # October's DST transition is traversed in unambiguous UTC hours.
    start = datetime(2026,10,23,tzinfo=timezone.utc)
    rows = generator.plan(meter, [], TimeWindow(start,start+timedelta(days=5)))
    assert len(rows) == 120
    def energy(day,hour):
        return next(r.get_energy_kwh() for r in rows
                    if r.get_interval()[0] == datetime(2026,10,day,hour,tzinfo=timezone.utc))
    assert energy(23,7) > energy(23,5)  # 09:00 summer local.
    assert energy(26,8) > energy(26,6)  # 09:00 winter local.
    assert energy(24,10) < Decimal('1')  # Saturday base load.


def connection_fixture(sample):
    meter, window, rows = sample
    cursor = Mock()
    cursor.fetchone.side_effect = [(1,"Main Meter"),("Demo Office",)]
    cursor.fetchall.return_value = [
        (r.get_interval()[0].replace(tzinfo=None),r.get_interval()[1].replace(tzinfo=None),r.get_energy_kwh())
        for r in rows]
    connection = Mock()
    connection.cursor.return_value = cursor
    database = Mock()
    database.connect.return_value = connection
    return database, connection, cursor, window


def test_preview_never_inserts_or_commits(sample):
    database, connection, cursor, window = connection_fixture(sample)
    result = DemoHistorySeeder(database).run(1,101,window)
    assert result["mode"] == "preview_no_writes"
    assert result["inserted_readings"] == 0
    assert result["projected_coverage"] == 1
    cursor.executemany.assert_not_called()
    connection.commit.assert_not_called()
    connection.rollback.assert_called_once()


def test_apply_locks_meter_inserts_only_gaps_and_commits_once(sample):
    database, connection, cursor, window = connection_fixture(sample)
    result = DemoHistorySeeder(database).run(1,101,window,apply=True)
    assert "FOR UPDATE" in cursor.execute.call_args_list[0].args[0]
    assert result["inserted_readings"] == result["proposed_new_readings"] > 0
    assert "INSERT INTO readings" in cursor.executemany.call_args.args[0]
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()


def test_insert_failure_rolls_back_and_closes(sample):
    database, connection, cursor, window = connection_fixture(sample)
    cursor.executemany.side_effect = RuntimeError("simulated insert failure")
    with pytest.raises(RuntimeError,match="simulated insert failure"):
        DemoHistorySeeder(database).run(1,101,window,apply=True)
    connection.commit.assert_not_called()
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()
    cursor.close.assert_called_once()


def test_unknown_meter_does_not_create_or_insert_records(sample):
    database, connection, cursor, window = connection_fixture(sample)
    cursor.fetchone.side_effect = [None]
    from smart_energy.analytics.errors import AnalyticsError
    with pytest.raises(AnalyticsError,match="not found"):
        DemoHistorySeeder(database).run(1,101,window,apply=True)
    cursor.executemany.assert_not_called()
    connection.commit.assert_not_called()


def test_explicit_env_file_loads_database_values_not_root_secret(tmp_path):
    path=tmp_path/".env"
    path.write_text("SMART_ENERGY_DB_PASSWORD='demo value # literal'\nMYSQL_ROOT_PASSWORD=never_export\n")
    import os
    with patch.dict(os.environ, {}, clear=True):
        load_database_env(path)
        assert os.environ["SMART_ENERGY_DB_PASSWORD"] == "demo value # literal"
        assert os.environ["SMART_ENERGY_DB_PORT"] == "3307"
        assert "MYSQL_ROOT_PASSWORD" not in os.environ


def test_invalid_short_window_rejected_without_connecting(sample):
    _,window,_=sample
    database=Mock()
    with pytest.raises(ValueError,match="at least 60"):
        DemoHistorySeeder(database).run(1,101,TimeWindow(window.start,window.start+timedelta(days=30)))
    database.connect.assert_not_called()


def test_german_clock_1140_matches_utc_1040_not_a_two_hour_lag():
    from zoneinfo import ZoneInfo
    berlin = ZoneInfo("Europe/Berlin")
    now = datetime(2026,11,13,11,40,23,tzinfo=berlin)
    hourly = resolve_end(now)
    minute = resolve_end(now,resolution="minute")
    assert hourly == datetime(2026,11,13,10,tzinfo=timezone.utc)
    assert hourly.astimezone(berlin).hour == 11
    assert minute == datetime(2026,11,13,10,40,tzinfo=timezone.utc)
    assert minute.astimezone(berlin).strftime("%H:%M") == "11:40"


def test_minute_endpoint_fills_elapsed_hour_and_remains_idempotent(sample):
    meter, window, rows = sample
    new_end=window.end+timedelta(minutes=40)
    extended=TimeWindow(window.start,new_end)
    generator=DemoHistoryGenerator()
    old=rows+generator.plan(meter,rows,window)
    additions=generator.plan(meter,old,extended)
    assert len(additions)==1
    assert additions[0].get_interval()==(window.end,new_end)
    assert generator.plan(meter,old+additions,extended)==[]


def test_preview_reports_local_start_and_end_without_shifting_stored_utc(sample):
    database, connection, cursor, window = connection_fixture(sample)
    result=DemoHistorySeeder(database).run(1,101,window)
    assert result['dashboard_end_utc']==window.end
    assert result['dashboard_end_local']=='2026-11-12T11:00:00+01:00'
    latest=result['latest_interval_in_window']
    assert latest['start_utc']==window.end-timedelta(hours=1)
    assert latest['start_local']=='2026-11-12T10:00:00+01:00'
    assert latest['end_local']=='2026-11-12T11:00:00+01:00'


def test_explicit_local_endpoint_is_respected_and_future_endpoint_rejected():
    now=datetime(2026,11,13,10,40,30,tzinfo=timezone.utc)
    assert resolve_end(now,'2026-11-13T11:35:00+01:00')==now.replace(minute=35,second=0)
    with pytest.raises(ValueError,match='Future'):
        resolve_end(now,'2026-11-13T11:41:00+01:00')
    with pytest.raises(ValueError,match='timezone'):
        resolve_end(now,'2026-11-13T11:35:00')
