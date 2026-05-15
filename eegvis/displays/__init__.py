"""Bundled and user MontageDisplay profiles.

Two locations are searched:

- **System / bundled** — JSON files shipped next to this module in
  ``eegvis/displays/``. Curated profiles part of the package.
- **User** — JSON files under ``~/.eegvis/displays/`` (override with
  ``EEGVIS_USER_DISPLAYS_DIR``). Created by the in-app montage editor and
  loaded the same way as bundled profiles. User profiles take precedence
  over bundled ones if a name collides.

Each ``*.json`` is a serialized :class:`eegvis.montage_display.MontageDisplay`
matching the schema in ``SCHEMA.md`` /
``montage_display.schema.json``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from ..montage_display import MontageDisplay

SYSTEM_DIR = Path(__file__).resolve().parent


def user_dir() -> Path:
    """Return the user-displays directory. May not exist yet."""
    override = os.environ.get("EEGVIS_USER_DISPLAYS_DIR")
    if override:
        return Path(override).expanduser()
    return Path("~/.eegvis/displays").expanduser()


def _is_profile(p: Path) -> bool:
    return p.suffix == ".json" and not p.name.endswith(".schema.json")


def list_displays(scope: str = "all") -> List[str]:
    """Return the names of available MontageDisplay profiles.

    Args:
        scope: ``"system"`` (bundled only), ``"user"`` (user dir only),
            or ``"all"`` (both; user overrides system on name collisions).
    """
    if scope == "system":
        return sorted(p.stem for p in SYSTEM_DIR.glob("*.json") if _is_profile(p))
    if scope == "user":
        ud = user_dir()
        if not ud.exists():
            return []
        return sorted(p.stem for p in ud.glob("*.json") if _is_profile(p))
    if scope == "all":
        names = set(list_displays("system"))
        names.update(list_displays("user"))
        return sorted(names)
    raise ValueError(f"unknown scope {scope!r}; expected system/user/all")


def list_displays_by_scope() -> Dict[str, List[str]]:
    """Return ``{"system": [...], "user": [...]}`` for the editor UI."""
    return {"system": list_displays("system"), "user": list_displays("user")}


def find_display_path(name: str, scope: Optional[str] = None) -> Path:
    """Resolve a profile name to a path. Raises KeyError if not found.

    If ``scope`` is None, search user first then system.
    """
    if scope == "user":
        path = user_dir() / f"{name}.json"
        if not path.exists():
            raise KeyError(f"unknown user display {name!r}")
        return path
    if scope == "system":
        path = SYSTEM_DIR / f"{name}.json"
        if not path.exists():
            raise KeyError(f"unknown bundled display {name!r}")
        return path
    # default: user wins over system
    upath = user_dir() / f"{name}.json"
    if upath.exists():
        return upath
    spath = SYSTEM_DIR / f"{name}.json"
    if spath.exists():
        return spath
    raise KeyError(f"unknown display {name!r}; available: {list_displays('all')}")


def load_display(name: str, scope: Optional[str] = None) -> MontageDisplay:
    """Load a MontageDisplay by name from user-or-system."""
    return MontageDisplay.load(find_display_path(name, scope=scope))


def save_user_display(display: MontageDisplay, name: Optional[str] = None) -> Path:
    """Write a MontageDisplay to the user directory and return the path.

    Uses ``display.name`` as the filename stem unless ``name`` is given.
    Creates the user directory if needed. A user profile with the same name
    as a bundled system profile shadows it (user wins in
    :func:`load_display`); use ``list_displays_by_scope`` to see both lists.
    """
    stem = name or display.name
    if not stem:
        raise ValueError("MontageDisplay.name is empty; pass a name explicitly")
    ud = user_dir()
    ud.mkdir(parents=True, exist_ok=True)
    path = ud / f"{stem}.json"
    display.save(path)
    return path
