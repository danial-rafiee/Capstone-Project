# AI-Powered Smart Energy Management System

Group 18's capstone monitors electricity use in one demo office building,
calculates consumption, cost and carbon, and provides sustainability scoring
and AI advice. The current implementation is the initial OOP learning stage.

## Team Overview

| Member | Subsystem | Package | Responsibility |
| --- | --- | --- | --- |
| Saeid Rafiei Taghanaki | A | `smart_energy/web` | Dashboard, Flask routes, service integration and web tests |
| Danial Rafiee | B | `smart_energy/analytics` | Data models, MySQL, reading validation and energy/cost/carbon calculations |
| Hananeh Hajari | C | `smart_energy/coach` | Score and penalties, AI context, OpenAI integration and AI/scoring tests |

## Project Structure

```text
Capstone-Project/
├── docs/
│   ├── uml/
│   │   ├── analytics_classes.dot
│   │   ├── analytics_classes.mmd
│   │   ├── analytics_classes.png
│   │   ├── analytics_classes.svg
│   │   ├── generate_analytics_uml.py
│   │   ├── generate_b_mermaid.py
│   │   ├── generate_ha3_uml.py
│   │   ├── generate_ha4_uml.py
│   │   ├── ha2_source.dot
│   │   ├── ha2_source.mmd
│   │   ├── ha2_source.png
│   │   ├── ha2_source.svg
│   │   ├── ha3_repositories.dot
│   │   ├── ha3_repositories.mmd
│   │   ├── ha3_repositories.png
│   │   ├── ha3_repositories.svg
│   │   ├── ha3_schema.dot
│   │   ├── ha3_schema.mmd
│   │   ├── ha3_schema.png
│   │   ├── ha3_schema.svg
│   │   ├── ha4_errors.dot
│   │   ├── ha4_errors.mmd
│   │   ├── ha4_errors.png
│   │   └── ha4_errors.svg
│   ├── ha2_source.md
│   ├── ha3_database.md
│   └── ha4_analytics.md
├── smart_energy/
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── analytics_service.py
│   │   ├── building.py
│   │   ├── building_repository.py
│   │   ├── database.py
│   │   ├── energy_settings.py
│   │   ├── errors.py
│   │   ├── meter.py
│   │   ├── meter_repository.py
│   │   ├── reading.py
│   │   └── reading_repository.py
│   ├── coach/
│   │   ├── __init__.py
│   │   ├── building_context.py
│   │   ├── coach_api.py
│   │   ├── coach_repository.py
│   │   ├── coach_service.py
│   │   ├── exceptions.py
│   │   ├── realtime_coach.py
│   │   ├── score_calculator.py
│   │   └── stream_pipeline.py
│   ├── streaming/
│   │   ├── source/
│   │   │   ├── __init__.py
│   │   │   ├── meter_event.py
│   │   │   ├── meter_stream.py
│   │   │   └── sample_source.py
│   │   ├── __init__.py
│   │   └── pipeline.py
│   ├── web/
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── coach_panel.py
│   │   │   ├── energy_summary.py
│   │   │   └── time_range.py
│   │   ├── templates/
│   │   │   └── dashboard.html
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── demo_data.py
│   │   └── errors.py
│   └── __init__.py
├── sql/
│   └── schema_ha3.sql
├── tests/
│   ├── test_analytics_ha4.py
│   ├── test_ha4_coach.py
│   └── test_web_ha4.py
├── .gitignore
├── README.md
├── demo.py
├── demo_coach.py
├── demo_ha2.py
├── demo_ha2_coach.py
├── demo_ha2_pipeline..py
├── demo_ha3.py
├── demo_ha3_coach.py
├── demo_ha4.py
├── requirements-ha3.txt
├── requirements-ha4.txt
├── requirements-web.txt
└── run_web.py
```

`Capstone-Project` is the shared repository name and the local project folder
name. The HA1 submission branch remains `Homeworkassignment001`.

This tree lists the versioned project files in `Homeworkassignment004`. Local virtual environments and IDE settings are omitted. B diagrams use Mermaid; DOT/PNG/SVG files are retained as supplementary exports. A/C documentation is maintained by their respective authors.

## Run the current example

1. Run Console Demo
To test the core OOP and data structures without external dependencies:

```bash
# On Windows:
python demo.py

# On macOS / Linux:
python3 demo.py
```
In PyCharm, right-click `demo.py` in the project tree and choose **Run 'demo'**.
Use that file rather than the earlier step-specific run configurations.

Expected output:

```text
Meter ID: 101
Meter name: Main Meter
Connected building ID: 1
Connected building name: Demo Office
Updated meter name: First Floor Meter
Invalid connection rejected: Meter must be connected to a Building object.
Building after rejected update: Demo Office

Energy reading
Reading meter ID: 101
Start: 2026-11-04T09:00:00+00:00
End: 2026-11-04T09:05:00+00:00
Energy: 2.5 kWh
Updated energy: 3.0 kWh
Invalid energy rejected: Reading energy must be finite and non-negative.
Energy after rejected update: 3.0 kWh

Energy settings
Settings building ID: 1
Tariff: 0.30 EUR/kWh
Carbon factor: 0.40 kg CO2/kWh
Off-hours allowance share: 0.10
Invalid settings rejected: Carbon factor must be finite and non-negative.
Tariff after rejected configuration: 0.30 EUR/kWh

Energy analytics
Reading count: 2
Total energy: 5.0 kWh
Estimated cost: 1.50 EUR
Estimated CO2: 2.00 kg
Duplicate reading rejected: Duplicate or overlapping intervals for the same meter.
Reading count after rejection: 2
```
2. Run Web Dashboard
To start the Flask-based web application interface:
```bash
# First, activate your virtual environment (.venv), then run:
python run_web.py
# (Or use python3 run_web.py on macOS/Linux)
```
Open your browser and navigate to http://127.0.0.1:5000.


## System Design


### Subsystem A class diagram

```mermaid
classDiagram
    class TimeRange {
        # _preset: str
        # _start: datetime
        # _end: datetime
        + __init__(preset: str, start: datetime, end: datetime)
        + configure(preset: str, start: datetime, end: datetime): None
        # _utc(value: datetime): datetime
        + get_preset(): str
        + set_preset(value: str): None
        + get_start(): datetime
        + set_start(value: datetime): None
        + get_end(): datetime
        + set_end(value: datetime): None
        + to_dict(): dict
    }

    class EnergySummary {
        # _totals: dict
        # _savings: dict
        # _reference: dict
        # _score: float
        # _penalties: list
        + __init__(totals: int, savings: int, reference: object, score: object, penalties: str)
        + configure(totals: int, savings: int, reference: object, score: object, penalties: str): None
        # _number(value, label, minimum, maximum): Decimal
        + get_totals(): Decimal
        + set_totals(value): None
        + get_savings(): Decimal
        + set_savings(value): None
        + get_reference(): object
        + set_reference(value): None
        + get_score(): object
        + set_score(value): None
        + get_penalties(): str
        + set_penalties(value): None
        + to_dict(): dict
    }

    class CoachPanel {
        # _question: str
        # _answer: str
        + __init__(question: str, answer: str)
        + configure(question: str, answer: str): None
        # _text(value): str
        + get_question(): str
        + set_question(value): None
        + get_answer(): str
        + set_answer(value): None
        + submit_question(question: str): None
        + set_response(answer: str): None
        + to_dict(): dict
    }
```

The diagram shows the core implemented domain and mock data classes for Subsystem A (`smart_energy.web`).

- `+` marks public methods, including `__init__`.
- `#` marks underscore-prefixed attributes, following Python's non-public convention.

### Implemented classes for Subsystem A

Current implemented classes and components in `smart_energy.web`:

| Component / Class | Meaning in the current code |
| --- | --- |
| `TimeRange` | Encapsulates datetime intervals and preset ranges for filtering energy dashboard queries. |
| `EnergySummary` | Acts as a DTO aggregating consumption totals, costs, carbon footprints, and scores. |
| `CoachPanel` | Structures AI coaching prompts, answers, and sustainability advice for the UI. |
| `DemoData` | Generates mock datasets and initial office building topologies for preview. |
| `Flask App & Dashboard` | Configures application routes (`app.py`) and renders summary cards and panels via Jinja2 templates (`dashboard.html`). |


### Subsystem B class diagram

```mermaid
classDiagram
    class Building {
        #int _building_id
        #str _name
        +__init__(building_id: int, name: str)
        +get_building_id() int
        +set_building_id(building_id: int) None
        +get_name() str
        +set_name(name: str) None
    }
    class Meter {
        #int _meter_id
        #Building _building
        #str _name
        +__init__(meter_id: int, building: Building, name: str)
        +get_meter_id() int
        +set_meter_id(meter_id: int) None
        +get_building() Building
        +set_building(building: Building) None
        +get_building_id() int
        +get_name() str
        +set_name(name: str) None
    }
    class Reading {
        #Meter _meter
        #datetime _start
        #datetime _end
        #Decimal _energy_kwh
        +__init__(meter: Meter, start: datetime, end: datetime, energy_kwh: Decimal)
        +get_meter() Meter
        +set_meter(meter: Meter) None
        +get_meter_id() int
        +get_interval() tuple~datetime_datetime~
        +set_interval(start: datetime, end: datetime) None
        +get_energy_kwh() Decimal
        +set_energy_kwh(energy_kwh: Decimal) None
    }
    class EnergySettings {
        #Building _building
        #Decimal _tariff
        #Decimal _carbon_factor
        #Decimal _off_hours_share
        +__init__(building: Building, tariff: Decimal, carbon_factor: Decimal, off_hours_share: Decimal)
        +configure(tariff: Decimal, carbon_factor: Decimal, off_hours_share: Decimal) None
        +get_building() Building
        +set_building(building: Building) None
        +get_building_id() int
        +get_tariff() Decimal
        +set_tariff(tariff: Decimal) None
        +get_carbon_factor() Decimal
        +set_carbon_factor(carbon_factor: Decimal) None
        +get_off_hours_share() Decimal
        +set_off_hours_share(off_hours_share: Decimal) None
        #_validate_factor(value: Decimal, label: str) None
        #_validate_share(off_hours_share: Decimal) None
    }
    class AnalyticsService {
        #list~Reading~ _readings
        #EnergySettings _settings
        +__init__(settings: EnergySettings, readings)
        +get_settings() EnergySettings
        +set_settings(settings: EnergySettings) None
        +get_readings() list~Reading~
        +set_readings(readings: list~Reading~) None
        +add_reading(reading: Reading) None
        +totals() dict
        #_validate_readings(readings: list~Reading~, settings: EnergySettings) None
    }

    Meter "0..*" --> "1" Building : _building
    Reading "0..*" --> "1" Meter : _meter
    EnergySettings "0..*" --> "1" Building : _building
    AnalyticsService "0..*" --> "1" EnergySettings : _settings
    AnalyticsService "0..*" --> "0..*" Reading : _readings
```

The diagram is generated from the B implementation in this branch. `+` denotes public members and `#` Python non-public convention. Arrows show stored references; multiplicities describe those references.

[Mermaid source](docs/uml/analytics_classes.mmd). Regenerate with `python docs/uml/generate_b_mermaid.py`; GitHub renders the embedded Mermaid blocks directly.

### Implemented classes

Current implemented classes in `smart_energy.analytics`:

- `Building(building_id, name)` stores building identity and name.
- `Meter(meter_id, building, name)` stores meter identity, name and building.
- `Reading(meter, start, end, energy_kwh)` stores interval energy for a meter.
- `EnergySettings(building, tariff, carbon_factor, off_hours_share)` stores
  factors for one building and provides `configure()` for initial setup or
  later reconfiguration.
- `AnalyticsService(settings, readings=None)` holds readings in memory,
  validates their relationships and returns energy, cost and CO2 totals.

All five classes use `__init__` and explicit getters/setters. Constructors use
validated setters or `configure()` so creation and updates follow the same
validation rules. Invalid updates
leave the previous value intact. Leading underscores mark non-public attributes
by Python convention; they do not prevent direct access.

Each meter references one `Building` object. Several meters may reference the
same building. A building ID is read from that object rather than copied into
a second field that could get out of sync. Database persistence and database-wide
identity constraints are not implemented. `AnalyticsService` checks meter ID
consistency within its current collection of readings.

Each reading references one `Meter`, which references one `Building`. The
reading uses `Decimal` for energy in kWh (interval consumption, not instantaneous
power). Energy must be finite and non-negative. The start and end timestamps
must include a timezone and the end must be later than the start. The class
normalizes timestamps to UTC and updates the interval atomically. Duplicate and
overlap checks across multiple readings belong to `AnalyticsService`.
The demonstration uses fixed illustrative timestamps and energy values.

`EnergySettings` stores the tariff in EUR/kWh, the carbon factor in kg CO2/kWh
and the off-hours allowance as a fraction between 0 and 1. These are explicit
demo assumptions. B stores the allowance; C will interpret it in scoring.
`configure()` validates all factors before changing any of them. The example
rejects a configuration containing a negative carbon factor and keeps the
previous tariff unchanged. Cost, carbon and score calculations are not
implemented by this settings class.

`AnalyticsService` totals only the readings explicitly supplied to it. It
requires the same building object as the settings, distinct IDs for distinct
meter objects, and non-overlapping intervals for each meter. Adjacent intervals
are valid, and simultaneous intervals from different meters are valid. An
invalid list, settings change or new reading is rejected before replacing the
stored state. Totals revalidate current objects to catch later meter/interval
changes. The readings getter returns a copy of the list.

An empty collection raises an unavailable-data error rather than reporting a
measured zero. A valid zero-energy reading can produce zero totals. The current
service does not establish complete period coverage, query MySQL, calculate
reference/off-hours metrics, or compute the sustainability score. These remain
later capstone work; scoring belongs to subsystem C.

The demo calculates 3.0 + 2.0 = 5.0 kWh, 5.0 x 0.30 = EUR 1.50 and
5.0 x 0.40 = 2.00 kg CO2. Figures are illustrative and use constant factors.

## HA1 progress

Local branch: `Homeworkassignment001`.

The complete group submission is still in progress. Five B classes are currently
implemented at the OOP demonstration level, with a matching rendered B UML
diagram embedded above. Teammates' classes, their UML, group integration and
the group video remain to be completed. Building operating hours,
essential equipment and full period analytics remain further capstone work.
MySQL, Flask and OpenAI are planned project capabilities
and are not connected in the current example.

## HA1 Presentation Link

The group video has not been recorded yet.
# =====HA2=====
## HA2 — Saeid: Pipeline & Stream Processing Integration

Branch: `Homeworkassignment002`. Saeid's contribution implements the core stream processing **`Pipeline`** mechanism, supporting operator overloading (`|` and `+`) to chain multiple processors (such as filters and transformers) and execute real-time stream transformations sequentially.

### Subsystem A Pipeline Architecture (Mermaid Class Diagram)
```mermaid
classDiagram
    class Pipeline {
        - stages: list
        + __init__(stages: list)
        + __or__(other) Pipeline
        + __add__(other) Pipeline
        + process(event: Any) Optional[Any]
        + run(stream: MeterStream) Iterator[Any]
    }

    class InactiveMeterFilter {
        + min_threshold_kw: Decimal
        + process(event)
    }

    class RealTimeScoreTransformer {
        + reference_kw: Decimal
        + allowance_share: Decimal
        + process(event)
    }

    Pipeline o-- InactiveMeterFilter : orchestrates stages via pipe (|)
    Pipeline o-- RealTimeScoreTransformer : orchestrates stages via pipe (|)

```
### HA2 Implementation Highlights

- **Pipeline Orchestration (`pipeline.py`):** Chains multiple processing stages sequentially and drops events early if any stage returns `None`.
- **Operator Overloading:** Implements `__or__` and `__add__` to allow natural pipeline composition using `filter_stage | transform_stage`.
- **Stream Execution:** Iterates through `MeterStream` events and yields processed results via `run()`.


## HA2 — Danial: stream source

Branch: `Homeworkassignment002`. Danial's input contribution provides validated
`MeterEvent` objects, a single-pass `MeterStream` implementing `__iter__` and
`__next__`, and a lazy sample generator using `yield`.

```mermaid
classDiagram
    class MeterEvent {
        #int _meter_id
        #datetime _timestamp
        #Decimal _power_kw
        #bool _active
        #int _interval_seconds
        +__init__(meter_id: int, timestamp: datetime, power_kw: Decimal, active: bool, interval_seconds: int)
        +int meter_id
        +datetime timestamp
        +Decimal power_kw
        +bool active
        +int interval_seconds
        +Decimal energy_kwh
    }
    class MeterStream {
        #Iterator~MeterEvent~ _iterator
        +__init__(events: Iterable~MeterEvent~)
        +__iter__() MeterStream
        +__next__() MeterEvent
    }
    class Iterator {
        <<interface>>
    }
    class SampleSource {
        <<module>>
        +generate_meter_events() Iterator~MeterEvent~
    }
    Iterator <|-- MeterStream
    MeterStream ..> MeterEvent : yields and validates
    SampleSource ..> MeterEvent : constructs lazily
```

[Mermaid source](docs/uml/ha2_source.mmd)

See [the event contract and source documentation](docs/ha2_source.md).
Run `python3 demo_ha2.py` from the repository root.

The remaining group implementation must add the explicit abstract processor
contract, specialized filter/transform processors, operator-based pipeline
composition and the five-minute presentation link. The original HA1 sections
above describe the earlier implementation; this section documents only the
current HA2 source contribution.



## HA2 — Hananeh: Real-Time Stream Pipeline & AI Coach

Branch: `Homeworkassignment002`. Subsystem C's contribution processes real-time event streams from IoT meters, evaluates operational penalties on the fly, computes live sustainability scores, and triggers instant AI coach intervention alerts.

### Subsystem C Stream Architecture (Mermaid Class Diagram)

```mermaid
classDiagram
    class BaseStreamProcessor {
        <<abstract>>
        +process(event: Any)* Optional[Any]
        +__or__(other: BaseStreamProcessor) Pipeline
    }

    class Pipeline {
        -stages: list[BaseStreamProcessor]
        +__init__(stages: list)
        +process(event: Any) Optional[Any]
        +__or__(other: BaseStreamProcessor) Pipeline
        +run(stream: Iterator) Iterator
    }

    class InactiveMeterFilter {
        +min_threshold_kw: Decimal
        +process(event: MeterEvent) Optional[MeterEvent]
    }

    class RealTimeScoreTransformer {
        +reference_kw: Decimal
        +allowance_share: Decimal
        +process(event: MeterEvent) Optional[dict]
    }

    class RealTimeCoachAlerter {
        +threshold: float
        +process(event_data: dict) Optional[dict]
    }

    BaseStreamProcessor <|-- Pipeline : inherits & extends
    BaseStreamProcessor <|-- InactiveMeterFilter : inherits
    BaseStreamProcessor <|-- RealTimeScoreTransformer : inherits
    BaseStreamProcessor <|-- RealTimeCoachAlerter : inherits

Pipeline o-- BaseStreamProcessor : composes stages via pipe (|)
```

### HA2 Implementation Highlights
- **Abstract Base Classes (ABCs):** `BaseStreamProcessor` enforces the `@abstractmethod` contract for `process()`.
- **Inheritance & Polymorphism:** `InactiveMeterFilter`, `RealTimeScoreTransformer`, and `RealTimeCoachAlerter` adhere to a uniform streaming contract.
- **Operator Overloading:** Overloaded `__or__` allows natural pipeline chaining:
```python
pipeline = filter_stage | transform_stage | alert_stage
```
- **Stream Consumption:** Evaluates stream events yielded by `MeterStream` iterator on the fly.

### Running Subsystem C Demo
Run the standalone real-time streaming demonstration:
```bash
python3 demo_ha2_coach.py
```

### HA2 Presentation Link
The 5-minute video walkthrough link will be placed here:
- **Presentation Video:** `[Pending Recording / Video Link]`

# =====HA3=====

## HA3 — Saeid: Flask Web & MySQL Integration

Branch: `Homeworkassignment003`. Subsystem A's contribution integrates the Flask web application with the production MySQL relational database (`smart_energy_ha3`). It connects the repository architecture (`BuildingRepository`, `MeterRepository`, `ReadingRepository`) and `AnalyticsService` directly to the web layer, ensuring live data retrieval, dynamic metric calculations, and real-time dashboard rendering.
```mermaid
classDiagram
    class FlaskApp {
        <<module>>
        +get_db_connection() Database
        +create_app(test_config) Flask
        +home() HTML
        +api_analytics(building_id, meter_id) JSON
    }
    class Database {
        +connect()
    }
    class BuildingRepository {
        +get_by_id(building_id) Optional~Building~
    }
    class MeterRepository {
        +get_by_id(meter_id, building) Optional~Meter~
    }
    class ReadingRepository {
        +list_for_meter(meter) list~Reading~
    }
    class AnalyticsService {
        +totals() dict
    }
    FlaskApp ..> Database : constructs
    FlaskApp ..> BuildingRepository : loads building
    FlaskApp ..> MeterRepository : loads meter with same building
    FlaskApp ..> ReadingRepository : loads readings
    FlaskApp ..> EnergySettings : supplies sample factors
    FlaskApp ..> AnalyticsService : calculates totals
    FlaskApp ..> TimeRange : creates display object
    FlaskApp ..> EnergySummary : prepares template data
    FlaskApp ..> CoachPanel : prepares template data
```

### HA3 Implementation Highlights
* **Application Factory & Database Integration:** Configured Flask routes (`app.py`) to instantiate database connections and fetch live building, meter, and reading records dynamically.
* **Service & Domain Wiring:** Integrated `EnergySettings` with explicit `Decimal` parameters alongside `AnalyticsService` to compute real-time energy consumption, estimated costs, and carbon footprints.
* **REST API & Dashboard Verification:** Added dedicated JSON API endpoints (e.g., `/api/analytics/<building_id>/<meter_id>`) for integration testing, successfully rendering live metrics and sustainability scores on the Jinja2 `dashboard.html` template.

To run the integrated web application:
1. Ensure your MySQL database is running and configured with the HA3 schema.
2. Start the Flask development server from the repository root:
```bash
python run_web.py
```
Open your browser and navigate to http://127.0.0.1:5000/ or verify data flow via the API endpoint at http://127.0.0.1:5000/api/analytics/1/101.

The application successfully retrieves live readings from the database, computes analytics totals, and displays the dynamic web dashboard. The group's final integration, complete diagrams, and five-minute video link remain to be finalized.
## HA3 — Danial: MySQL data access

Branch: `Homeworkassignment003`. Danial's B contribution adds Database,
BuildingRepository, MeterRepository and ReadingRepository. The shared domain
classes and AnalyticsService read real stored readings through these repositories.

```mermaid
classDiagram
    class Database {
        #dict _config
        +__init__()
        +connect()
    }
    class BuildingRepository {
        #Database _database
        +__init__(database: Database)
        +save(building: Building) None
        +get_by_id(building_id: int) Optional~Building~
    }
    class MeterRepository {
        #Database _database
        +__init__(database: Database)
        +save(meter: Meter) None
        +get_by_id(meter_id: int, building: Building) Optional~Meter~
    }
    class ReadingRepository {
        #Database _database
        +__init__(database: Database)
        +add(reading: Reading) None
        +list_for_meter(meter: Meter) list~Reading~
    }

    BuildingRepository "0..*" --> "1" Database : _database
    MeterRepository "0..*" --> "1" Database : _database
    ReadingRepository "0..*" --> "1" Database : _database
    BuildingRepository ..> Building : saves and returns
    MeterRepository ..> Meter : saves and returns
    MeterRepository ..> Building : reuses supplied object
    ReadingRepository ..> Meter : reuses supplied object
    ReadingRepository ..> Reading : inserts and returns
```

[Mermaid source](docs/uml/ha3_repositories.mmd)

```mermaid
erDiagram
    buildings ||--o{ meters : contains
    meters ||--o{ readings : records
    buildings {
        int building_id PK
        varchar name
    }
    meters {
        int meter_id PK
        int building_id FK
        varchar name
    }
    readings {
        bigint reading_id PK
        int meter_id FK
        datetime start_utc
        datetime end_utc
        decimal energy_kwh
    }
```

See [setup, storage behavior and the integration contract](docs/ha3_database.md).
Install `requirements-ha3.txt`, create the schema with `sql/schema_ha3.sql`,
configure local database credentials through environment variables if needed,
and run `python demo_ha3.py` from the repository root.

The two retrieved demo readings total 5.0 kWh, EUR 1.50 and 2.00 kg CO2 with
explicit sample factors. This section documents B only. Subsystem A must connect
the repositories to the final Flask/Django response. The group's final README,
complete diagrams and five-minute video link remain to be integrated.

# =====HA4=====

## HA4 — Exception Handling & Comprehensive Testing

Branch: `Homeworkassignment004` (or current active branch). Subsystem implementation integrates robust cross-layer exception handling and a comprehensive automated testing suite.

### HA4 Implementation Highlights

* **Cross-Layer Exception Handling:** 
  * Created dedicated error-handling classes and modules across subsystems to catch domain and database anomalies cleanly.
  * Registered centralized error handlers in the Flask application (`register_web_error_handlers(app)`) to map internal errors to appropriate HTTP status codes (e.g., `404`, `503`).
* **Comprehensive Test Suite (15 Tests):** 
  * Implemented a robust suite of **15 distinct unit and integration tests** covering all major components:
    * **Analytics Tests (`test_analytics_ha4.py`):** Validates energy calculations, zero/negative reading rejections, overlap checks, and connection failure handling.
    * **Coach Tests (`test_ha4_coach.py`):** Tests score boundaries, building lookup exceptions, and evaluation API endpoints.
    * **Web Tests (`test_web_ha4.py`):** Validates dashboard route accessibility, API analytics endpoints, time range & decimal conversions, coach panel interactions, and custom WebAppError status code integration.
* **Environment-Agnostic Mocking:** Leveraged `unittest.mock` (`MagicMock` and `patch`) in test suites to ensure complete test isolation, high execution speed, and stability without requiring an active local MySQL database connection during test runs.

### Subsystem A Error-Handling Class Diagram
```mermaid
classDiagram
    class WebAppError {
        +str message
        +str code
        +__init__(message: str, code: str)
    }
    class WebAppErrorHandler {
        +handle(error: WebAppError)$ dict
    }
    class FlaskApp {
        +register_web_error_handlers(app)
        +handle_web_error(error)
    }
    Exception <|-- WebAppError
    WebAppErrorHandler ..> WebAppError : formats
    FlaskApp ..> WebAppError : catches and maps to HTTP status
```
### Subsystem A Implementation Highlights
- **Web Tests (`test_web_ha4.py`):** 
      - Implemented a robust suite of **5 distinct unit and integration tests** in `tests/test_web_ha4.py` covering:
        - Dashboard route accessibility (`test_dashboard_route_status`).
        - API analytics endpoints (`test_api_analytics_endpoint`).
        - Time range and decimal conversions (`test_time_range_and_energy_summary`).
        - Coach panel interactions (`test_coach_panel_interactions`).
        - Custom `WebAppError` handling and routing integration (`test_web_app_error_handling_and_routing`).

### Subsystem B error-handling class diagram

```mermaid
classDiagram
    class AnalyticsError {
        +str code
        +__init__(message: str, code: str)
    }
    class AnalyticsErrorHandler {
        +handle(error: Exception) dict
    }
    class AnalyticsService {
        +totals() dict
    }
    class Database {
        +connect()
    }
    Exception <|-- AnalyticsError
    AnalyticsErrorHandler ..> AnalyticsError : formats
    AnalyticsService ..> AnalyticsError : raises no_readings
    Database ..> AnalyticsError : raises database_unavailable
```

[Mermaid source](docs/uml/ha4_errors.mmd) · [B error handling and five tests](docs/ha4_analytics.md)

Database and AnalyticsService are abbreviated to the operations involved in error handling. AnalyticsError inherits Exception; dashed arrows denote raising or formatting dependencies.

### Running the Test Suite

To run all 15 tests and verify the system state, execute the following command from the repository root:

```bash
python -m pytest tests -v
```
