"""Reproduce the fluorescence calibration module and its three final figures."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "output" / ".mplconfig"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

for name in ("parse.py", "model_0921.py", "plot_model.py"):
    subprocess.run([sys.executable, str(ROOT / "src" / name)], cwd=ROOT, check=True)

(ROOT / "figures").mkdir(exist_ok=True)
for path in (ROOT / "output").glob("figure2-[123]_*"):
    if path.suffix in (".png", ".svg"):
        shutil.copy2(path, ROOT / "figures" / path.name)
print("Reproduction complete. Figures: figures/; analysis outputs: output/.")
