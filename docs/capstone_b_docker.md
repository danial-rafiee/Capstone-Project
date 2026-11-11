# Capstone B - isolated Docker database and B-only verification

This package is owned by Danial. It does not modify/package Saeid's Flask app
or Hananeh's AI/score code. It is not the group's complete Docker deployment.
The group's existing `sql/schema_ha3.sql` is mounted unchanged, including its
existing shared table definitions, to keep the database schema consistent.

## What is included

```text
docker/analytics/
  compose.yaml                  MySQL and optional B-check service
  .env.example                  Empty local credential template
  Dockerfile                    Python B demo/test runner
  Dockerfile.dockerignore        B-only build context allowlist
  20-demo-readings.sql           Explicit simulated sample rows
check_docker_database_b.py       Read-only verification of the seeded E/R/O case
```

- MySQL uses the official `mysql:8.4` image.
- A named volume stores the Docker database independently of host MySQL.
- Only `127.0.0.1:3307` is published by default; host MySQL on 3306 stays separate.
- Container database name is fixed as `smart_energy_ha3` to match the existing SQL.
- The application account is `energy_app`; Python does not use Docker's root account.
- The healthcheck uses a TCP login and actual table query with the application
  account. It waits for initialization, not just for a process to start.
- B-check is opt-in via the `check` profile and waits for the database to be healthy.
- The B Python image runs as a non-root user, installs requirements before
  copying changing source files, and does not include A/C code or credentials.

## Prerequisite

Install and start [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/),
or use another working Docker Engine with Compose. On Danial's Mac, choose the
Apple silicon installer. Verify `docker compose version` before proceeding.

All commands below run from the repository root. These instructions configure a
dedicated local demo database; they do not change the existing Homebrew database.

## 1. Local credentials

```bash
cp docker/analytics/.env.example docker/analytics/.env
```

Open the new `.env` file locally. Fill `MYSQL_ROOT_PASSWORD` and
`SMART_ENERGY_DB_PASSWORD` with two nonempty Docker-database passwords. The
application password is used for `energy_app`; these settings are separate from
the host database's credentials. For simple local setup, use generated
alphanumeric values. The `.env` file is already ignored by Git; only the blank
`.env.example` is committed. If adding special characters, follow Compose's
[environment file syntax](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).

Leave the other template values as supplied for this demo. In particular, the
schema/database name is fixed; changing an environment setting alone does not
rename the SQL schema.

Validate without printing resolved passwords:

```bash
docker compose --env-file docker/analytics/.env -f docker/analytics/compose.yaml config --quiet
```

## 2. Start MySQL

```bash
docker compose --env-file docker/analytics/.env -f docker/analytics/compose.yaml up -d --wait mysql
docker compose --env-file docker/analytics/.env -f docker/analytics/compose.yaml ps
```

On a fresh volume, the official MySQL entrypoint runs the existing schema and
then `20-demo-readings.sql`. Initialization scripts are not migrations: they run
only when the volume starts empty. Editing SQL or passwords later does not
automatically rewrite a populated database or change an existing account password.

The seed includes simulated building 1, meter 101, two hourly readings for
3 November and two for 4 November 2026, 08:00-10:00 Europe/Berlin local time.
Under the agreed weekday 09:00-17:00 calendar, current E=5 kWh, reference R=7 kWh,
current O=2 kWh. Two additional 09:00-09:10 UTC readings support the earlier HA3
demo. There is no overlap between these intervals and no data is claimed to be
from a physical smart meter.

## 3. Build and run B's checks inside Docker

```bash
docker compose --env-file docker/analytics/.env -f docker/analytics/compose.yaml --profile check build b-check
docker compose --env-file docker/analytics/.env -f docker/analytics/compose.yaml --profile check run --rm b-check
```

The B-check service is expected to:

1. Pass the 52 B-only tests (5 HA4 B + 19 period + 28 off-hours cases).
2. Read actual seeded MySQL rows through B's repositories and verify E=5, R=7,
   O=2, current cost EUR 1.50 and current CO2 2 kg.
3. Run the earlier MySQL period demo and the separate simulated off-hours demo.

An error in any stage gives a nonzero exit code. The read-only verification
script never fixes/overwrites data to make a check pass. It expects this dedicated
sample dataset. This service excludes A/C source and therefore does not execute
the full 62-test application suite; run that separately in the shared environment.

The standalone Dockerfile defaults to the in-memory off-hours demo. Compose
overrides the command to perform the full B verification sequence above.

## Host PyCharm versus container connection settings

For PyCharm/Python **on the host**, use the settings from the local `.env` file:

```text
SMART_ENERGY_DB_HOST=127.0.0.1
SMART_ENERGY_DB_PORT=3307
SMART_ENERGY_DB_NAME=smart_energy_ha3
SMART_ENERGY_DB_USER=energy_app
SMART_ENERGY_DB_PASSWORD=<the local Docker application password>
```

Set these explicitly in the run configuration. `Database` does not automatically
load `.env`. Passing Compose `--env-file` configures Compose, not unrelated host
Python processes. PyCharm running `check_docker_database_b.py` needs these values.

For a Python/web service **inside the same Compose network**, use hostname
`mysql` and port `3306`, with the same name, user and application password.
Compose already supplies this environment to B-check. Never use container-local
`localhost` to mean another container's database.

## For Saeid and Hananeh

- Merge/coordinate B's Docker database service into the agreed final deployment.
  The service name is `mysql`; do not start two different databases accidentally.
- Configure your own application service with the container connection values
  above and a `depends_on` health condition for `mysql`.
- A/C still need their own application Dockerfile/service configuration; this B
  runner is a test/demo image, not a Flask web server or OpenAI service.
- Keep the existing schema source consistent. The shared schema is mounted
  unchanged; B does not redefine or migrate C's evaluation table.
- The database seed is for the fixed demonstration scenario only.

## Stop while preserving data

```bash
docker compose --env-file docker/analytics/.env -f docker/analytics/compose.yaml down
```

This keeps the named data volume. Recreating a container does not reset its
database. No data-deleting reset command is needed for normal demo use.

## Validation status

- Official Compose v5.7.0 parsed/resolved the configuration successfully.
- Port mapping, required credentials, bind mounts, profile and health dependency
  were checked; empty credentials are rejected.
- The unchanged schema and new seed SQL ran successfully on local MySQL in a
  uniquely created disposable schema. The read-only E/R/O check passed and only
  that temporary validation schema was removed; the host project DB was untouched.
- The exact B source/test set included by the Dockerfile passed all 52 B tests
  independently on the host, with no A/C source present.
- **Runtime verified on 10 November 2026:** Docker Engine 29.9.3 and Compose
  v5.7.0 built the B image and started MySQL successfully. The MySQL service is
  healthy and published only on host `127.0.0.1:3307`.
- The actual `b-check` container completed with exit code 0: **52 B tests passed**,
  followed by the read-only seeded E/R/O verification, the MySQL period demo
  and the simulated off-hours demo. Container-to-container access used
  `mysql:3306` and the `energy_app` account.
- Local Docker credentials were generated in the Git-ignored `.env`; they are
  not included in committed files or this guide. The existing host database
  on port 3306 was not changed by the Docker startup.
- This verifies B's database/demo containers only. The group's complete Docker
  requirement still needs A/C application services integrated and tested.

References:

- [Official MySQL image and initialization behavior](https://hub.docker.com/_/mysql)
- [Compose startup order and health conditions](https://docs.docker.com/compose/how-tos/startup-order/)
- [Compose configuration validation](https://docs.docker.com/reference/cli/docker/compose/config/)
