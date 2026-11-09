"""Collect distribution notices alongside the desktop executables."""

from importlib.metadata import distributions
from pathlib import Path
import shutil
import sys

output = Path(sys.argv[1])
for path in ("LICENSE", "NOTICE"):
    shutil.copyfile(path, output / path)

licenses = output / "third-party-licenses"
licenses.mkdir(exist_ok=True)
shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", licenses / "Python.txt")
for dist in distributions():
    name = dist.metadata["Name"]
    if name.lower() == "huntly":
        continue
    for file in dist.files or ():
        if not any(part.endswith(".dist-info") for part in file.parts):
            continue
        if not file.name.upper().startswith(("LICENSE", "COPYING", "NOTICE", "AUTHORS")):
            continue
        target = licenses / name / file.name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(file.locate(), target)
