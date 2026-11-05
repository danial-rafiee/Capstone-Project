import ast
import html
import json
from pathlib import Path
import subprocess
import os
import shutil

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent

# فقط کلاس‌های واقعی و موجود در زیرسیستم A
CLASSES = [
    ("domain/time_range.py", "TimeRange", [
        ("_preset", "str"), ("_start", "datetime"), ("_end", "datetime"),
    ]),
    ("domain/energy_summary.py", "EnergySummary", [
        ("_totals", "dict"), ("_savings", "dict"), ("_reference", "dict"),
        ("_score", "float"), ("_penalties", "list"),
    ]),
    ("domain/coach_panel.py", "CoachPanel", [
        ("_question", "str"), ("_answer", "str"),
    ]),
    ("demo_data.py", "DemoData", []),
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
            text += " = " + ast.unparse(method.args.defaults[index - first_default])
        params.append(text)
    visibility = "#" if method.name.startswith("_") and method.name != "__init__" else "+"
    text = f"{visibility} {method.name}({', '.join(params)})"
    if method.returns:
        text += ": " + ast.unparse(method.returns)
    return text


def rows(lines):
    if not lines:
        return '<BR ALIGN="LEFT"/>'
    return '<BR ALIGN="LEFT"/>'.join(html.escape(line) for line in lines) + '<BR ALIGN="LEFT"/>'


def find_dot_executable():
    if shutil.which("dot"):
        return "dot"
    common_paths = [
        r"C:\Program Files\Graphviz\bin\dot.exe",
        r"C:\Program Files (x86)\Graphviz\bin\dot.exe",
        os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\Graphviz.Graphviz_noArch\Graphviz\bin\dot.exe"),
    ]
    for path in common_paths:
        if Path(path).exists():
            return path
    return "dot"


def generate_uml():
    dot = [
        'digraph WebUML {',
        '  graph [rankdir=BT, bgcolor="white", pad="0.4", nodesep="0.9", ranksep="1.0",',
        '    splines=polyline, outputorder=edgesfirst, fontname="Arial", fontsize=20,',
        '    labelloc=t, label="Subsystem A class diagram\\nImplemented classes in smart_energy.web"];',
        '  node [shape=plain, fontname="Arial", fontsize=13];',
        '  edge [color="#087F79", fontname="Arial", fontsize=12, arrowhead=vee,',
        '    arrowsize=0.75, penwidth=1.2, labeldistance=2.0, labelangle=25];',
    ]

    for rel_path, name, fields in CLASSES:
        full_path = ROOT / "smart_energy" / "web" / rel_path
        if not full_path.exists():
            continue
        tree = ast.parse(full_path.read_text())
        cls = next((node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name), None)
        if not cls:
            continue
        methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)]
        attrs = [f"# {field}: {kind}" for field, kind in fields]

        attr_row = f'<TR><TD ALIGN="LEFT" BGCOLOR="#F0F6F5">{rows(attrs)}</TD></TR>' if attrs else ''
        separator = '<HR/>' if attrs and methods else ''
        method_row = f'<TR><TD ALIGN="LEFT">{rows([method_text(m) for m in methods])}</TD></TR>' if methods else ''

        label = (
            '<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="10" COLOR="#087F79">'
            f'<TR><TD BGCOLOR="#102E31"><FONT COLOR="white" POINT-SIZE="16"><B>{name}</B></FONT></TD></TR>'
            f'{attr_row}{separator}{method_row}'
            '</TABLE>'
        )
        dot.append(f'  {name} [label=<{label}>];')

    dot.append('}')

    dot_file = DEST / "web_classes.dot"
    svg_file = DEST / "web_classes.svg"
    png_file = DEST / "web_classes.png"

    dot_file.write_text("\n".join(dot) + "\n")

    dot_cmd = find_dot_executable()
    try:
        subprocess.run([dot_cmd, "-Tsvg", str(dot_file), "-o", str(svg_file)], check=True)
        subprocess.run([dot_cmd, "-Tpng", str(dot_file), "-o", str(png_file), "-Gdpi=150"], check=True)
        print("Web subsystem UML diagrams generated successfully!")
    except Exception as e:
        print(f"Failed to generate UML diagrams. Error: {e}")


if __name__ == "__main__":
    generate_uml()