# Subsystem B: 60-day simulated MySQL demo history

Owner: Danial. This package adds only a B data generator, a CLI, tests and this
documentation. It does not change A's web routes, C's scoring/AI, the SQL schema,
existing measurements, or the rule that reference comparisons need full coverage.
All newly generated readings are **SIMULATED**, not sensor measurements or a live
stream. Existing records remain unchanged.

## Purpose and data policy

The 30-day dashboard preset needs a complete selected period plus a complete
preceding 30-day reference: 60 elapsed days ending at the same fixed timestamp.
The 24-hour and 7-day presets and their references fit inside the same history.
These are UTC elapsed durations, including across daylight saving transitions.

`DemoHistoryGenerator` generates a deterministic office-like profile, with higher
load Monday-Friday 09:00-17:00 Europe/Berlin and a lower base load otherwise. The
profile is illustrative; it is not calibrated to a real building. The same seed,
meter and UTC hour produce the same simulated power profile regardless of run
date. Seasonal offsets follow the local business calendar.

The generator finds actual uncovered intervals, then splits them at UTC hour
boundaries. If an hour already contains two five-minute readings, it fills only
the remaining minutes. It never drops that whole hour, overwrites its readings,
or adds a full overlapping hourly row. Existing overlaps are rejected rather
than hidden. New interval energy is stored as non-negative DECIMAL(18,6) kWh;
very short gaps can round to zero at this storage precision.

## Requirements

- Existing B dependencies: `python -m pip install -r requirements-capstone-b.txt`.
- Existing MySQL schema and building/meter (defaults: building 1 / meter 101).
- A running Docker MySQL service for the documented Docker example.
- Use an isolated **demo** database/meter. The script deliberately does not
  create entities, erase tables, replace rows or change database credentials.

No additional Python dependency is required. The CLI explicitly loads simple
database KEY=value entries from the selected `.env`; it does not execute shell
code, interpolate variables, load the root password, or print passwords.

## Preview first (no writes)

From the project root, with the project Python environment active:

```bash
python seed_demo_history_b.py --env-file docker/analytics/.env
```

For this Docker file, unset connection fields default to localhost port **3307**,
user `energy_app`, database `smart_energy_ha3`. Explicit file values override
matching process variables. Without `--env-file`, the existing `Database`
environment/default behavior applies (including port 3306). Check the reported
`database_target` before applying. Do not copy or upload the actual `.env`.

The default end is the start of the current UTC hour: the end of the last
completed hourly interval. No unfinished hour or future interval is generated.
The default duration is 60 days. The output contains the selected UTC start/end,
existing count, proposed inserts, coverage and projected comparisons for 1, 7
and 30 days. `preview_no_writes` explicitly identifies a preview; projected
results do not claim to describe already stored rows.

To pin a repeatable preview/apply endpoint, copy the `end` timestamp from the
preview (example only):

```bash
python seed_demo_history_b.py --env-file docker/analytics/.env --end 2026-11-12T14:00:00+00:00
python seed_demo_history_b.py --env-file docker/analytics/.env --end 2026-11-12T14:00:00+00:00 --apply
```

The `--apply` command appends gaps in a single transaction, after locking the
meter and rereading its measurements. Failure rolls back the batch. It uses the
same parent-meter lock as `ReadingRepository.add`; external direct SQL writers
must respect that lock too. It is not a guarantee against unrelated writers
that ignore the repository's locking convention.

Rerunning with the **same end timestamp** inserts zero rows. Running again in a
later hour fills the newly elapsed time without changing earlier data. The
script is a manual demo tool, not a background collector or scheduler.

Other options: `--days` (60..366), `--building-id`, `--meter-id`, `--timezone`,
`--seed`. New data follows the selected simulation timezone; align the dashboard
calendar with it. Switching the seed does not replace already saved data.

## Handoff to Saeid (Subsystem A)

1. Use this history only as explicitly labelled simulated demo data.
2. Anchor all three presets at the **same end of the last completed reading**
   (`dashboard_end_utc` in the report). Do not use a slightly later `now()` for
   the same dataset: that reintroduces a missing tail.
3. Build a selected 1/7/30-day window and an immediately preceding equal-duration
   reference. Display the actual period and last-data timestamp.
4. Keep B's complete-coverage condition. After generation, both windows should
   be `complete`, comparison `ready`, coverage 1, and score inputs `ready`.
5. Use the actual reference energy/score_inputs. Do not create a reference as a
   fixed percentage of current consumption. C must receive real B-calculated
   values **from the simulated records**, not an invented reference total.
6. `energy_saved_percent` is savings. Conventional **Energy change** is its
   negative: `(current-reference)/reference*100`. Zero reference has no defined
   percentage and remains null.
7. Running this script changes only the local database you target. Git push
   shares the generator, **not** the records; teammates must run it on their own
   demo databases, or use the same explicitly configured shared database.

No new orchestration service, Flask route, AI request or C code is introduced.
This script verifies B comparison readiness; it does not itself render cards or
calculate a C sustainability score.

## Existing sample and tests

The original six rows from `20-demo-readings.sql` remain intact. Their two-hour
November 3/4 checks still produce E=5, R=7 and O=2. October data does not affect
those filtered periods. No `docker compose down -v` is needed.

```bash
python -m pytest tests/test_demo_history_b.py -v
python -m pytest tests -q
```

The new tests cover partial-hour gaps, exact preservation, deterministic reruns,
three full reference comparisons, the E/R/O scenario, DST, tiny gaps, rejection
of overlaps, preview without writes, commit/rollback behavior and environment
loading. Database-independent unit tests do not touch the running MySQL.

For the existing read-only MySQL check, use the same database environment as the
seeding command. In particular, running `check_docker_database_b.py` directly
does not automatically read `.env`; its environment must already target Docker
localhost:3307 with the application credentials.

## MySQL verification on 12 November 2026

All **74 tests** on the B branch passed, including **12 new demo-history tests**.

The script was first verified against a newly created disposable database on the
Docker MySQL server. Preview left the database unchanged. Apply preserved the six
original rows and inserted 1,436 gap rows. Repeating the same endpoint inserted
zero rows. The original E=5/R=7/O=2 read-only check passed. Only that disposable
database was removed after the integration test.

The same operation was then completed on the local Docker demo database
`smart_energy_ha3` at localhost:3307, building 1 / meter 101. Its history now has
1,442 rows, including all six unchanged originals. The verified window is
2026-09-13 14:00 UTC through 2026-11-12 14:00 UTC (15:00 Europe/Berlin at the end).
For each 1/7/30-day selected period and preceding reference, coverage was 100%,
comparison was ready, and B score inputs were ready. A repeated apply inserted
zero rows and the original database scenario still passed.

This verifies stored data and B calculations, not rendering on Saeid's machine
or a live OpenAI request. Teammates using another database must run the script
there themselves. Update the history before a later presentation, or explicitly
show this fixed historical demo endpoint.
