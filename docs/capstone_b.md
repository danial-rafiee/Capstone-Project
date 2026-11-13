# Capstone - Danial's selected-period data contract

Branch: `capstone-danial-b`. This document describes B's selected-period data
layer and its contract with A/C. In the current checkout, the Flask dashboard
uses `PeriodAnalyticsService` and `OperatingSchedule` for the 24h, 7d and 30d
presets, then passes the comparison payload to C's `evaluate_period`. B owns
energy/cost/carbon calculations and E/R/O inputs; A owns dashboard presentation,
and C owns sustainability scoring and AI advice. The standalone B demos and
Docker runner verify the data layer separately from the complete web application.

## Scope and compatibility

- Existing `AnalyticsService.totals()` and its output keys remain unchanged.
- Existing `ReadingRepository.list_for_meter()` and `add()` remain unchanged.
- New `list_for_period(meter, start, end)` retrieves only intervals overlapping
  the selected half-open period. SQL parameters are bound separately.
- New `TimeWindow(start, end)` requires aware datetimes and normalizes to UTC.
- New `PeriodAnalyticsService(settings)` calculates single-meter period totals,
  coverage, chronological interval series and an optional reference comparison.
- No schema changes, database writes or credentials are needed for the new
  read-only MySQL demonstration. Existing local credentials still apply.
- Optional `OperatingSchedule` enables off-hours energy and E/R/O scoring inputs.
  `requirements-capstone-b.txt` adds IANA `tzdata` for systems without timezone
  data (notably Windows and minimal containers).

The new classes use the same Building/Meter/Reading objects as B's original
contract. Retrieve one building, pass that object to the meter repository, and
use it for EnergySettings too. Each summary accepts readings for that one meter.
Do not combine main and submeter consumption and double-count the same loads.

## For Saeid: selected-period flow

Reuse your existing repositories and caller-supplied `EnergySettings`. Convert
the selected UI bounds to timezone-aware datetimes before calling B. B's UTC
window is separate from A's `TimeRange` presentation object.

```python
from smart_energy.analytics.time_window import TimeWindow
from smart_energy.analytics.period_analytics import PeriodAnalyticsService, to_json_ready

# building, meter, settings and reading_repository come from your existing setup.
window = TimeWindow(start, end)
readings = reading_repository.list_for_period(meter, window.start, window.end)
service = PeriodAnalyticsService(settings)
summary = service.summarize(meter, readings, window)
payload = to_json_ready(summary)  # jsonify(payload) in your Flask route
```

Numeric values are `Decimal` internally. `to_json_ready` returns exact decimal
strings, UTC ISO timestamps, booleans and JSON nulls. A can convert decimal
strings to plotting numbers at the display boundary and round money for display.
Do not calculate from rounded display values.

| Field | Meaning |
| --- | --- |
| `status` | `complete`, `partial`, or `no_data` |
| `coverage_fraction` | Covered seconds divided by requested seconds, from 0 to 1 |
| `energy_kwh` | Energy over measured portions within the selected window |
| `estimated_cost_eur` | Energy times supplied constant tariff; not a utility bill |
| `estimated_co2_kg` | Energy times supplied constant carbon factor |
| `energy_estimated` | True if an interval crossing a window bound was prorated |
| `series` | Ordered interval start/end, energy, average power and estimation flag |
| `gaps` | Explicit intervals without measurement coverage |

`no_data` returns null energy/cost/carbon and an empty series. A measured zero
returns zero with actual coverage. `partial` returns only the available measured
energy; label it partial and do not present it as a complete period total.
Full temporal coverage is not proof of device accuracy or source authenticity.

Measurements crossing a selected boundary are allocated by duration assuming
constant average power throughout that measurement interval. The service marks
these values as estimated. It does not alter the original Reading or MySQL row.

## Reference comparison and savings

Choose an explicit earlier reference period with the same duration in UTC.
For example, compare two complete ten-minute samples. Do not invent a reference
or compare a ten-minute sample with an entire day. Across DST transitions, local
calendar days can have unequal elapsed durations and will be rejected by this
API; decide the reference definition explicitly in the UI.

```python
reference_window = TimeWindow(reference_start, reference_end)
reference_readings = reading_repository.list_for_period(
    meter, reference_window.start, reference_window.end
)
comparison = service.compare(
    meter, readings, reference_readings, window, reference_window
)
payload = to_json_ready(comparison)
```

Savings = reference energy minus current energy. Increased consumption produces
negative savings. Cost/carbon differences use the same supplied factors for both
periods; they do not represent historical tariff changes or causal AI savings.
If either period has gaps/no data, comparison is unavailable and savings are
null. With measured zero reference energy, percentage savings are null, while
absolute differences are still available. Boundary-prorated comparisons carry
an estimation flag and must be labelled accordingly.

## For Hananeh: scoring boundary

- For a complete current period, `current["energy_kwh"]` is the E input.
- For an explicit complete reference period, `reference["energy_kwh"]` is R.
- Do not convert `no_data`/`partial` to measured zero or display a ready score
  for a full period when its inputs are missing.
- When an `OperatingSchedule` is explicitly supplied, current-period
  `off_hours_energy_kwh` is O. It is based on local weekly hours/closed dates,
  not an arbitrary percentage of E. Without a schedule it remains null.
- `compare()` now includes `score_inputs`, `score_inputs_status`,
  `score_inputs_estimated` and `score_allowance_share`. Use the ready E/R/O
  inputs directly in C before JSON serialization. Missing/partial periods,
  absent schedule or non-positive E/R give unavailable/null scoring inputs.
- [Off-hours configuration and the final C handoff](capstone_b_off_hours.md)
  describe the calendar and exact input names. Actual scoring remains C's job.
- Score, penalties, AI context and OpenAI calls remain C's responsibility.
- `off_hours_share` still belongs to EnergySettings; pass the same agreed value
  to C's calculator. The demonstrator's 0.10 is illustrative configuration.

## Demonstration and checks

```bash
python -m pip install -r requirements-capstone-b.txt -r requirements-web.txt
python demo_capstone_b.py
python demo_off_hours_b.py
python -m pytest tests/test_period_analytics.py -v
python -m pytest tests -q
```

The simulated demo shows complete, partial and absent data and compares 5 kWh
with an explicit 7 kWh reference: 2 kWh, EUR 0.60 and 0.80 kg lower consumption
equivalents under the sample factors. The source and fixed factors are labelled.

After configuring your local MySQL environment, this reads existing building 1,
meter 101 readings for 4 November 2026, 09:00-09:10 UTC without changing data:

```bash
python demo_capstone_b.py --mysql
python demo_capstone_b.py --mysql --schedule-demo
```

If your local root account has an empty password, set
`SMART_ENERGY_DB_PASSWORD` to an explicitly empty environment value for this run.
Do not change the database password or commit local credentials.

An earlier increment verification recorded 62 passing tests. The current local
checkout passed all 79 tests with `python -m pytest tests -q` on 2026-11-13;
this run does not verify a live MySQL connection or an external AI provider.
The read-only MySQL run returned two readings, 5 kWh, EUR 1.50 and 2 kg CO2.
With `--schedule-demo`, their local 10:00-10:10 Berlin period is occupied time,
so O is measured zero for this fully covered period. The separate off-hours demo
uses 08:00-10:00 local samples and produces O=2 kWh.
This verifies the data layer; final A/C integration requires its own checks.

The diagram source is [capstone_b_period.mmd](uml/capstone_b_period.mmd).
It abbreviates existing classes to the methods involved in this increment.

## Group integration boundary

B's local demo calendar has been agreed as Monday-Friday 09:00-17:00,
Europe/Berlin, with no additional closed dates. This is illustrative, not a real
building configuration. The current dashboard calls B's period service and
passes its comparison payload to C for scoring. Live database, external AI and
complete deployment checks remain separate from the B unit tests. Coordinate Docker database settings
with the group's deployment owner. [B's Docker database and B-only runner](capstone_b_docker.md)
are now verified in actual Docker: MySQL started healthy, 52 B-only tests passed
inside the B runner, and seeded E/R/O queries succeeded across the container
network. Full web/AI/container integration is not implemented by these B demos.
