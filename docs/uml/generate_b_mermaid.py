"""Generate Mermaid class diagrams from the checked-out B implementation.

Run from any directory: python docs/uml/generate_b_mermaid.py
No application imports, database access or third-party packages are required.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'docs' / 'uml'

FIELDS = {
    'Building': {'_building_id': 'int', '_name': 'str'},
    'Meter': {'_meter_id': 'int', '_building': 'Building', '_name': 'str'},
    'Reading': {'_meter': 'Meter', '_start': 'datetime', '_end': 'datetime', '_energy_kwh': 'Decimal'},
    'EnergySettings': {'_building': 'Building', '_tariff': 'Decimal', '_carbon_factor': 'Decimal', '_off_hours_share': 'Decimal'},
    'AnalyticsService': {'_readings': 'list[Reading]', '_settings': 'EnergySettings'},
    'MeterEvent': {'_meter_id': 'int', '_timestamp': 'datetime', '_power_kw': 'Decimal', '_active': 'bool', '_interval_seconds': 'int'},
    'MeterStream': {'_iterator': 'Iterator[MeterEvent]'},
    'Database': {'_config': 'dict'},
    'BuildingRepository': {'_database': 'Database'},
    'MeterRepository': {'_database': 'Database'},
    'ReadingRepository': {'_database': 'Database'},
    'AnalyticsError': {'code': 'str'},
    'AnalyticsErrorHandler': {},
}

def kind(node):
    if node is None:
        return ''
    value = ast.unparse(node).strip("'\"")
    if value.endswith(' | None'):
        value = 'Optional[' + value[:-7] + ']'
    value = value.replace('[', '~').replace(']', '~')
    return value.replace(', ', '_')

def class_block(relative, name):
    tree = ast.parse((ROOT / relative).read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    assigned = {n.attr for n in ast.walk(cls) if isinstance(n, ast.Attribute)
                and isinstance(n.ctx, ast.Store) and isinstance(n.value, ast.Name)
                and n.value.id == 'self'}
    assert assigned == set(FIELDS[name]), (name, assigned, FIELDS[name])
    lines = [f'    class {name} {{']
    for attr, label in FIELDS[name].items():
        lines.append(f'        {"#" if attr.startswith("_") else "+"}{label.replace("[", "~").replace("]", "~")} {attr}')
    for method in cls.body:
        if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(isinstance(d, ast.Name) and d.id == 'property' for d in method.decorator_list):
            lines.append(f'        +{kind(method.returns)} {method.name}')
            continue
        args = [a.arg + (': ' + kind(a.annotation) if a.annotation else '')
                for a in method.args.args if a.arg not in ('self', 'cls')]
        visibility = '#' if method.name.startswith('_') and not method.name.endswith('__') else '+'
        result = kind(method.returns)
        lines.append(f'        {visibility}{method.name}({", ".join(args)})' + (' ' + result if result else ''))
    return '\n'.join(lines + ['    }'])

def diagram(filename, pairs, relations, extra=''):
    text = 'classDiagram\n' + '\n'.join(class_block(path, name) for path, name in pairs)
    text += '\n' + extra + '\n' + '\n'.join('    ' + r for r in relations) + '\n'
    (DEST / filename).write_text(text)

def analytics(filename):
    return 'smart_energy/analytics/' + filename + '.py'

diagram('analytics_classes.mmd', [(analytics(f), n) for f, n in [
    ('building', 'Building'), ('meter', 'Meter'), ('reading', 'Reading'),
    ('energy_settings', 'EnergySettings'), ('analytics_service', 'AnalyticsService')]], [
    'Meter "0..*" --> "1" Building : _building',
    'Reading "0..*" --> "1" Meter : _meter',
    'EnergySettings "0..*" --> "1" Building : _building',
    'AnalyticsService "0..*" --> "1" EnergySettings : _settings',
    'AnalyticsService "0..*" --> "0..*" Reading : _readings',
])

if (ROOT / 'smart_energy/streaming/source/meter_event.py').exists():
    diagram('ha2_source.mmd', [(f'smart_energy/streaming/source/{f}.py', n) for f,n in [
        ('meter_event', 'MeterEvent'), ('meter_stream', 'MeterStream')]], [
        'Iterator <|-- MeterStream', 'MeterStream ..> MeterEvent : yields and validates',
        'SampleSource ..> MeterEvent : constructs lazily',
    ], '    class Iterator {\n        <<interface>>\n    }\n'
       '    class SampleSource {\n        <<module>>\n        +generate_meter_events() Iterator~MeterEvent~\n    }')

if (ROOT / analytics('database')).exists():
    diagram('ha3_repositories.mmd', [(analytics(f), n) for f,n in [
        ('database', 'Database'), ('building_repository', 'BuildingRepository'),
        ('meter_repository', 'MeterRepository'), ('reading_repository', 'ReadingRepository')]], [
        'BuildingRepository "0..*" --> "1" Database : _database',
        'MeterRepository "0..*" --> "1" Database : _database',
        'ReadingRepository "0..*" --> "1" Database : _database',
        'BuildingRepository ..> Building : saves and returns',
        'MeterRepository ..> Meter : saves and returns',
        'MeterRepository ..> Building : reuses supplied object',
        'ReadingRepository ..> Meter : reuses supplied object',
        'ReadingRepository ..> Reading : inserts and returns',
    ])

if (ROOT / analytics('errors')).exists():
    diagram('ha4_errors.mmd', [(analytics('errors'), 'AnalyticsError'),
                              (analytics('errors'), 'AnalyticsErrorHandler')], [
        'Exception <|-- AnalyticsError', 'AnalyticsErrorHandler ..> AnalyticsError : formats',
        'AnalyticsService ..> AnalyticsError : raises no_readings',
        'Database ..> AnalyticsError : raises database_unavailable',
    ], '    class AnalyticsService {\n        +totals() dict\n    }\n'
       '    class Database {\n        +connect()\n    }')

print('Generated Mermaid diagrams from the current B classes.')
