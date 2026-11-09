"""Canonical filesystem locations: the user's home folder for config,
knowledge and state.

Config (huntly.yaml, .env), knowledge (prompts/, skills/) and state (data/)
all live in one home folder. Which folder depends on how the app was
installed, decided once at import:

- ``HUNTLY_HOME`` set: that folder. Docker pins it to /app, which is not a
  checkout (no pyproject.toml) but is where the volumes are mounted.
- A source checkout (pyproject.toml next to huntly/): the checkout itself,
  so a clone keeps working in place exactly as before.
- Anything else (a pipx or pip install into site-packages): a per-user
  folder, because site-packages is replaced on every upgrade.

``resolve()`` matters: when the package is reached through a symlink (some
editable installs), a bare ``Path(__file__).parent`` would point into
site-packages and the app would silently read/write the wrong files.
"""

import os
import sys
from pathlib import Path
from typing import Mapping

HOME_ENV = "HUNTLY_HOME"
APP_DIR = "huntly"

# Where the installed package's parent is: the checkout root for a clone,
# site-packages for an install.
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def is_checkout(package_root: Path) -> bool:
    """True for a source checkout, never for anything inside site-packages."""
    package_root = Path(package_root)
    return ((package_root / "pyproject.toml").is_file()
            and (package_root / "huntly" / "__init__.py").is_file()
            and "site-packages" not in package_root.parts)


def user_home_default(platform: str, env: Mapping[str, str], home: Path) -> Path:
    """The per-user data folder each OS expects an app to use."""
    home = Path(home)
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_DIR
    if platform == "win32":
        appdata = env.get("APPDATA")
        return Path(appdata) / APP_DIR if appdata else home / "AppData" / "Roaming" / APP_DIR
    return Path(env.get("XDG_DATA_HOME") or home / ".local" / "share") / APP_DIR


def resolve_home(env: Mapping[str, str] = os.environ, package_root: Path = PACKAGE_ROOT,
                 platform: str = sys.platform, home: Path | None = None) -> Path:
    """First match wins: HUNTLY_HOME, then a checkout, then the per-user default."""
    override = (env.get(HOME_ENV) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if is_checkout(package_root):
        return Path(package_root)
    return user_home_default(platform, env, Path.home() if home is None else home)


PROJECT_ROOT = resolve_home()


def cli_command(*args: str) -> list[str]:
    """Invoke the installed CLI, including from the Windows desktop bundle."""
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).with_name("HuntlyCLI.exe")), *args]
    return [sys.executable, "-P", "-m", "huntly", *args]
