"""Collect distribution notices alongside the desktop executables."""

from importlib.metadata import distributions
from pathlib import Path
import shutil
import sys

output = Path(sys.argv[1])
project = Path(__file__).resolve().parents[2]
for path in ("LICENSE", "NOTICE"):
    shutil.copyfile(project / path, output / path)

licenses = output / "third-party-licenses"
licenses.mkdir(exist_ok=True)
shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", licenses / "Python.txt")
for dist in distributions():
    name = dist.metadata["Name"]
    if name.lower() == "huntly":
        continue
    for file in dist.files or ():
        metadata_index = next(
            (index for index, part in enumerate(file.parts) if part.endswith(".dist-info")),
            None,
        )
        if metadata_index is None:
            continue
        parts = file.parts[metadata_index + 1:]
        if not parts or ".." in parts:
            continue
        if parts[0] != "licenses" and not file.name.upper().startswith(
            ("LICENSE", "COPYING", "NOTICE", "AUTHORS")
        ):
            continue
        target = licenses.joinpath(name, *parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file.locate(), target)
