"""Generate the Graphviz UML source from the implemented HA4 error classes.

Run from the repository root:
    python3 docs/uml/generate_ha4_uml.py

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
    ("errors.py", "AnalyticsError", [("code", "str")]),
    ("errors.py", "AnalyticsErrorHandler", []),
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
    'digraph HA4Errors {',
    '  graph [rankdir=BT, bgcolor="white", pad="0.4", nodesep="0.9", ranksep="1.0",',
    '    splines=polyline, outputorder=edgesfirst, fontname="Arial", fontsize=20,',
    '    labelloc=t, label="HA4 — Danial: error handling\\nImplemented classes in smart_energy.analytics"];',
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
    attrs = [f"{chr(35) if field.startswith(chr(95)) else chr(43)} {field}: {kind}" for field, kind in fields]
    label = (
        '<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="10" COLOR="#087F79">'
        f'<TR><TD BGCOLOR="#102E31"><FONT COLOR="white" POINT-SIZE="16"><B>{name}</B></FONT></TD></TR>'
        f'<TR><TD ALIGN="LEFT" BGCOLOR="#F0F6F5">{rows(attrs)}</TD></TR>'
        '<HR/>'
        f'<TR><TD ALIGN="LEFT">{rows([method_text(method) for method in methods])}</TD></TR>'
        '</TABLE>'
    )
    dot.append(f'  {name} [label=<{label}>];')

# Existing callers are abbreviated; only their relevant operation is shown.
dot += [
    '  Exception [shape=record, label="{Exception|Python standard library}"];',
    '  AnalyticsService [shape=record, label="{«existing» AnalyticsService|+ totals(): dict}"];',
    '  Database [shape=record, label="{«existing» Database|+ connect()}"];',
    '  AnalyticsError -> Exception [arrowhead=empty, label="inherits"];',
    '  AnalyticsErrorHandler -> AnalyticsError [style=dashed, label="formats"];',
    '  AnalyticsService -> AnalyticsError [style=dashed, label="raises: no_readings"];',
    '  Database -> AnalyticsError [style=dashed, label="raises: database_unavailable"];',
    '}',
]
(DEST / "ha4_errors.dot").write_text("\n".join(dot) + "\n")
print(json.dumps({"classes": len(CLASSES), "methods": method_counts,
                  "source": str(DEST / "ha4_errors.dot")}))
