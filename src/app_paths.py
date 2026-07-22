from __future__ import annotations

import sys
from pathlib import Path


def user_data_dir() -> Path:
    if sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "DesktopPet"
    else:
        path = Path.home() / ".desktop-pet"
    path.mkdir(parents=True, exist_ok=True)
    return path


def todos_file() -> Path:
    return user_data_dir() / "todos.json"


def notebook_file() -> Path:
    return user_data_dir() / "notebook.md"


def legacy_notes_file() -> Path:
    return user_data_dir() / "notes.json"
