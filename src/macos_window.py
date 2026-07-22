from __future__ import annotations

import sys
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

_space_change_observers: list[object] = []


def is_macos() -> bool:
    return sys.platform == "darwin"


def enable_visible_when_inactive(widget: QWidget) -> None:
    if not is_macos():
        return

    widget.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)


def apply_stay_visible_on_macos(widget: QWidget) -> bool:
    if not is_macos():
        return False

    win_id = int(widget.winId())
    if win_id == 0:
        return False

    ns_window = _get_ns_window(widget)
    if ns_window is None:
        return False

    if hasattr(ns_window, "setHidesOnDeactivate_"):
        ns_window.setHidesOnDeactivate_(False)
    if hasattr(ns_window, "setFloatingPanel_"):
        ns_window.setFloatingPanel_(True)
    if hasattr(ns_window, "setBecomesKeyOnlyIfNeeded_"):
        ns_window.setBecomesKeyOnlyIfNeeded_(False)
    if hasattr(ns_window, "setAcceptsMouseMovedEvents_"):
        ns_window.setAcceptsMouseMovedEvents_(True)

    return True


def watch_active_space_changes(callback: Callable[[], None]) -> None:
    if not is_macos():
        return

    try:
        from AppKit import NSWorkspace
    except ImportError:
        return

    def handler(_notification) -> None:
        callback()

    observer = NSWorkspace.sharedWorkspace().notificationCenter().addObserverForName_object_queue_usingBlock_(
        "NSWorkspaceActiveSpaceDidChangeNotification",
        None,
        None,
        handler,
    )
    _space_change_observers.append(observer)


def _get_ns_window(widget: QWidget):
    try:
        import objc
    except ImportError:
        return None

    win_id = int(widget.winId())
    if win_id == 0:
        return None

    ns_view = objc.objc_object(c_void_p=win_id)
    return ns_view.window()
