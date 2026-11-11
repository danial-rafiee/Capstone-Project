"""Generate the Graphviz UML source from the implemented HA3 repository classes.

Run from the repository root:
    python3 docs/uml/generate_ha3_uml.py

Render the resulting .dot file with Graphviz to SVG or PNG. Regenerate the
rendered images after changing a class. No third-party Python package is needed
to generate the source.
"""

import ast
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent

CLASSES = [
    ("database.py", "Database", [("_config", "dict")]),
    ("building_repository.py", "BuildingRepository", [("_database", "Database")]),
    ("meter_repository.py", "MeterRepository", [("_database", "Database")]),
    ("reading_repository.py", "ReadingRepository", [("_database", "Database")]),
]


def method_text(method):
    args = method.args.args
    first_default = len(args) - len(method.args.defaults)
    params = []
    for index, arg in enumerate(args):
        if arg.arg == "self":
            continue
        text = arg.arg
        if arg.annotation:
            text += ": " + ast.unparse(arg.annotation)
        if index >= first_default:
            text += " = " + ast.unparse(method.args.defaults[index-first_default])
        params.append(text)
    visibility = "#" if method.name.startswith("_") and method.name != "__init__" else "+"
    text = f"{visibility} {method.name}({', '.join(params)})"
    if method.returns:
        text += ": " + ast.unparse(method.returns)
    return text


def rows(lines):
    return '<BR ALIGN="LEFT"/>'.join(html.escape(line) for line in lines) + '<BR ALIGN="LEFT"/>'


dot = [
    'digraph HA3Repositories {',
    '  graph [rankdir=BT, bgcolor="white", pad="0.4", nodesep="0.9", ranksep="1.0",',
    '    splines=polyline, outputorder=edgesfirst, fontname="Arial", fontsize=20,',
    '    labelloc=t, label="HA3 — Danial: MySQL access classes\\nImplemented classes in smart_energy.analytics"];',
    '  node [shape=plain, fontname="Arial", fontsize=13];',
    '  edge [color="#52656D", fontname="Arial", fontsize=12, arrowhead=vee,',
    '    arrowsize=0.75, penwidth=1.2, labeldistance=2.0, labelangle=25];',
]

method_counts = {}
for filename, name, fields in CLASSES:
    tree = ast.parse((ROOT / "smart_energy" / "analytics" / filename).read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
    assignments = {
        node.attr for node in ast.walk(cls)
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store)
        and isinstance(node.value, ast.Name) and node.value.id == "self"
    }
    assert assignments == {field for field, _ in fields}, f"Update UML fields for {name}"
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)]
    method_counts[name] = len(methods)
    attrs = [f"# {field}: {kind}" for field, kind in fields]
    label = (
        '<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="10" COLOR="#087F79">'
        f'<TR><TD BGCOLOR="#102E31"><FONT COLOR="white" POINT-SIZE="16"><B>{name}</B></FONT></TD></TR>'
        f'<TR><TD ALIGN="LEFT" BGCOLOR="#F0F6F5">{rows(attrs)}</TD></TR>'
        '<HR/>'
        f'<TR><TD ALIGN="LEFT">{rows([method_text(method) for method in methods])}</TD></TR>'
        '</TABLE>'
    )
    dot.append(f'  {name} [label=<{label}>];')

# Repositories retain a Database connection factory, not a persistent connection.
dot += [
    '  { rank=same; BuildingRepository; MeterRepository; ReadingRepository; }',
    '  BuildingRepository -> Database [label="_database", taillabel="0..*", headlabel="1"];',
    '  MeterRepository -> Database [label="_database", taillabel="0..*", headlabel="1"];',
    '  ReadingRepository -> Database [label="_database", taillabel="0..*", headlabel="1"];',
    '}',
]
(DEST / "ha3_repositories.dot").write_text("\n".join(dot) + "\n")
print(json.dumps({"classes": len(CLASSES), "methods": method_counts,
                  "source": str(DEST / "ha3_repositories.dot")}))
