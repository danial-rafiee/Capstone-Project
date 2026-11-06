import subprocess
from pathlib import Path
import os
import shutil


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
    uml_dir = Path(__file__).parent
    dot_file = uml_dir / "web_classes.dot"
    svg_file = uml_dir / "web_classes.svg"
    png_file = uml_dir / "web_classes.png"

    if not dot_file.exists():
        print(f"Error: {dot_file} not found.")
        return

    dot_cmd = find_dot_executable()

    try:
        subprocess.run([dot_cmd, "-Tsvg", str(dot_file), "-o", str(svg_file)], check=True)
        subprocess.run([dot_cmd, "-Tpng", str(dot_file), "-o", str(png_file), "-Gdpi=150"], check=True)
        print("Web subsystem UML diagrams generated successfully!")
    except Exception as e:
        print(f"Failed to generate UML diagrams. Is Graphviz installed? Error: {e}")


if __name__ == "__main__":
    generate_uml()