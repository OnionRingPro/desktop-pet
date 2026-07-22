from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from src.app_paths import todos_file


@dataclass
class TodoItem:
    id: str
    text: str
    comment: str
    done: bool
    created_at: str

    @classmethod
    def create(cls, text: str, comment: str = "") -> TodoItem:
        return cls(
            id=uuid.uuid4().hex[:12],
            text=text.strip(),
            comment=comment.strip(),
            done=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


def _load_raw_items() -> list[dict]:
    path = todos_file()
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return []


def _save_raw_items(items: list[dict]) -> None:
    path = todos_file()
    path.write_text(
        json.dumps({"items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_todos() -> list[TodoItem]:
    todos: list[TodoItem] = []
    for raw in _load_raw_items():
        text = str(raw.get("text", "")).strip()
        if not text:
            continue
        todos.append(
            TodoItem(
                id=str(raw.get("id", uuid.uuid4().hex[:12])),
                text=text,
                comment=str(raw.get("comment", "")).strip(),
                done=bool(raw.get("done", False)),
                created_at=str(raw.get("created_at", "")),
            )
        )
    return todos


def save_todos(todos: list[TodoItem]) -> None:
    _save_raw_items([asdict(item) for item in todos])


def add_todo(text: str, comment: str = "") -> TodoItem:
    todo = TodoItem.create(text, comment)
    todos = load_todos()
    todos.insert(0, todo)
    save_todos(todos)
    return todo


def set_todo_done(todo_id: str, done: bool) -> None:
    todos = load_todos()
    for item in todos:
        if item.id == todo_id:
            item.done = done
            break
    save_todos(todos)


def delete_todo(todo_id: str) -> None:
    todos = [item for item in load_todos() if item.id != todo_id]
    save_todos(todos)


def pending_todos() -> list[TodoItem]:
    return [item for item in load_todos() if not item.done]


def format_pending_todos_message() -> str:
    items = pending_todos()
    if not items:
        return "今天没有待办啦，轻松一天～"

    lines: list[str] = ["今日待办："]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item.text}")
    return "\n".join(lines)
