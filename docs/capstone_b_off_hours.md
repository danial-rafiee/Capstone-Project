# Capstone B - off-hours energy and scoring handoff

Branch: `capstone-danial-b`. This extends B's period contract; A/C source files
and submitted HA branches are unchanged. It does not implement scoring or AI.

## Agreed simulated building calendar

- Timezone: `Europe/Berlin`.
- Open Monday-Friday, 09:00-17:00 local time.
- Closed Saturday/Sunday; no extra closed dates in the demo.
- These are explicit demo assumptions agreed with Danial. There is no global
  production calendar or default schedule silently assigned to a building.

```python
from smart_energy.analytics.operating_schedule import OperatingSchedule
from smart_energy.analytics.period_analytics import PeriodAnalyticsService

schedule = OperatingSchedule(
    'Europe/Berlin',
    {day: [('09:00', '17:00')] for day in range(5)},
    closed_dates=(),
)
service = PeriodAnalyticsService(settings, schedule)
```

Weekdays use Monday=0 through Sunday=6. Multiple intervals per day are supported.
Use `date` objects for explicit closed dates. No public-holiday calendar is
downloaded or inferred. Time strings use HH:MM, with 24:00 permitted as an end.
Overnight opening must be split across entries on adjacent weekdays.

`get_timezone()` returns the timezone name. `to_dict()` exports a copy of the
local schedule with string weekday keys and ISO date strings. C can include
this data in its AI context; do not imply that an example schedule is measured.

## Allocation and quality

For each measured interval clipped to the selected window:

`off-hours kWh = original interval kWh * off-hours elapsed seconds / original interval seconds`

UTC elapsed seconds are used after resolving the local calendar. The occupied
portion is the selected-period energy minus the off-hours portion. No energy
is removed from E: essential off-hours consumption still counts as consumption.
C applies its agreed allowance separately when scoring.

If an interval crosses an opening/closing boundary, allocating its energy by
time assumes constant average power. `off_hours_energy_estimated` flags this.
Do not present that split as an independently measured off-hours reading.
It is separate from `energy_estimated`, which marks selected-window clipping.

Opening is included and closing excluded. A reading starting at 17:00 is
outside a 09:00-17:00 opening interval.

Additional summary fields:

| Key | Contract |
| --- | --- |
| `off_hours_energy_kwh` | O over the measured portion; null without data/schedule |
| `occupied_energy_kwh` | Measured in-hours energy; null without data/schedule |
| `off_hours_status` | `complete`, `partial`, `no_data`, or `not_configured` |
| `off_hours_energy_estimated` | Whether allocating O required a split; otherwise false/null |
| `expected_off_hours_seconds` | Outside-hours duration in the requested window |
| `covered_off_hours_seconds` | Outside-hours duration with measurements |
| `off_hours_coverage_fraction` | Covered/expected outside-hours time; null if expected time is zero or schedule absent |
| `operating_schedule` | Explicit timezone, weekly hours and closed dates |

Missing off-hours data is not replaced with measured zero. Even if the available
readings give O=0, incomplete overall coverage blocks ready scoring inputs.
A completely occupied, fully measured window legitimately has O=0.

IANA `zoneinfo` is used for date-specific offsets. Full-day DST transitions use
actual elapsed time (23/25-hour days), not an assumed 24 hours. An opening or
closing wall time that is ambiguous or nonexistent on a DST transition is
rejected with ValueError; choose an unambiguous boundary. This is deliberate
validation, not automatic guessing of a fold policy.

See the [Python zoneinfo documentation](https://docs.python.org/3.14/library/zoneinfo.html)
for IANA data and ambiguous-time behavior. `requirements-capstone-b.txt` includes
the `tzdata` fallback so Windows/minimal containers can load these zones.

## For Hananeh - ready E/R/O, before JSON serialization

Call `service.compare(...)` as documented in [the period contract](capstone_b.md).
It returns the original current/reference/comparison data plus:

```python
result['score_inputs']
# {'current_energy': Decimal('5'),
#  'reference_energy': Decimal('7'),
#  'off_hours_energy': Decimal('2')}
result['score_inputs_status']     # 'ready' or 'unavailable'
result['score_inputs_estimated']  # True/False, or None when unavailable
result['score_allowance_share']   # Decimal('0.10') in the demo
```

`score_inputs` is null if the schedule is missing, either period is incomplete,
or current/reference energy is not positive (matching the current C calculator's
input conditions). Zero measured consumption stays visible in the data report;
it is not converted into missing data. A comparison may be ready while the
score is unavailable, for example when reference energy is measured zero.

Integration example for C to implement in its own code:

```python
# Do this before to_json_ready(), while inputs are Decimal objects.
if result['score_inputs_status'] == 'ready':
    calculator = ScoreCalculator(result['score_allowance_share'])
    score_result = calculator.calculate(**result['score_inputs'])
else:
    # Return/display unavailable; do not invent E/R/O or a score.
    score_result = None
```

`ScoreCalculator` belongs to C; B does not import, modify or call it. The example
above is a handoff, not completed integration. Propagate estimated-input flags
to the displayed score/AI context rather than implying a measured result.

## For Saeid - display integration

Supply the explicit schedule when creating the B service. Keep the earlier
timezone-aware period bounds and same Building/Meter object references.
Display energy, cost and carbon from the same selected current report. Show O
with units, coverage and estimation flags. Display the local timezone alongside
the selected dates; B stores/transmits measurement timestamps in UTC.

Existing `PeriodAnalyticsService(settings)` calls remain valid: without the
optional schedule, ordinary totals still work, but O is null and scoring inputs
are unavailable. Existing `AnalyticsService` and its output are unchanged.

## Demo and verification

```bash
python -m pip install -r requirements-capstone-b.txt -r requirements-web.txt
python demo_off_hours_b.py
python demo_off_hours_b.py --full
python -m pytest tests/test_off_hours_analytics.py -v
python -m pytest tests -q
```

The demo uses hourly simulated readings for 3/4 November 2026, 08:00-10:00 local
Berlin time. Current E=5 kWh, reference R=7 kWh, current O=2 kWh and occupied
energy=3 kWh. Allowance share is the explicit sample value 0.10. It neither
connects to MySQL nor calculates a score nor calls OpenAI.

All 62 tests passed: 15 existing application tests, 19 period tests, and 28
off-hours tests including parametrized timezone and input cases. Existing A/C
tests are executed unchanged. This does not replace checking the final web/AI
flow after teammates integrate their parts.
