from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.app_paths import legacy_notes_file, notebook_file


def _local_tz():
    return datetime.now().astimezone().tzinfo


def _format_legacy_time(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(_local_tz()).strftime("%H:%M")
    except ValueError:
        return ""


def _migrate_legacy_notes() -> str:
    legacy_path = legacy_notes_file()
    if not legacy_path.exists():
        return ""

    try:
        data = json.loads(legacy_path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        if not isinstance(items, list) or not items:
            return ""
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ""

    lines = ["# 记事本", ""]
    for raw in sorted(
        [item for item in items if isinstance(item, dict)],
        key=lambda item: str(item.get("created_at", "")),
    ):
        text = str(raw.get("text", "")).strip()
        if not text:
            continue
        time_label = _format_legacy_time(str(raw.get("created_at", "")))
        if time_label:
            lines.extend([f"## {time_label}", ""])
        lines.extend([text, ""])

    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def load_notebook() -> str:
    path = notebook_file()
    if path.exists():
        return path.read_text(encoding="utf-8")

    migrated = _migrate_legacy_notes()
    if migrated:
        save_notebook(migrated)
        return migrated
    return ""


def save_notebook(content: str) -> None:
    notebook_file().write_text(content, encoding="utf-8")


def export_notebook(dest: Path, content: str) -> None:
    dest.write_text(content, encoding="utf-8")
