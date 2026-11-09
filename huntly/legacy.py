"""Legacy compatibility module for Huntly."""

from __future__ import annotations

import os
from pathlib import Path

from huntly.paths import PROJECT_ROOT

FILES = []
OLD_PID = ""
WELCOME = ""


def adopt_legacy_env(environ=os.environ) -> list[str]:
    return []


def migrate_files(project_root: Path) -> list[tuple[str, str]]:
    return []


def welcome_pending(project_root: Path) -> bool:
    return False


def dismiss_welcome(project_root: Path) -> None:
    pass
