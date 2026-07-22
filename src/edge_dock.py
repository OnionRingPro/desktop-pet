from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QWidget

SNAP_THRESHOLD = 48
DOCK_VISIBLE_RATIO = 0.38
SCREEN_MARGIN = 4


class DockEdge(Enum):
    NONE = "none"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


def screen_geometry(widget: QWidget) -> QRect:
    screen = widget.screen() or QApplication.primaryScreen()
    if screen is None:
        return QRect()
    return screen.availableGeometry()


def is_docked(edge: DockEdge) -> bool:
    return edge is not DockEdge.NONE


def detect_snap_edge(widget: QWidget) -> DockEdge:
    available = screen_geometry(widget)
    if available.isNull():
        return DockEdge.NONE

    rect = widget.frameGeometry()
    distances = {
        DockEdge.LEFT: rect.left() - available.left(),
        DockEdge.RIGHT: available.right() - rect.right(),
        DockEdge.TOP: rect.top() - available.top(),
        DockEdge.BOTTOM: available.bottom() - rect.bottom(),
    }

    nearest = min(distances, key=distances.get)
    if distances[nearest] > SNAP_THRESHOLD:
        return DockEdge.NONE
    return nearest


def clamp_fully_on_screen(widget: QWidget) -> None:
    available = screen_geometry(widget)
    if available.isNull():
        return

    rect = widget.frameGeometry()
    x = rect.x()
    y = rect.y()

    x = max(available.left() + SCREEN_MARGIN, x)
    x = min(available.right() - widget.width() - SCREEN_MARGIN, x)
    y = max(available.top() + SCREEN_MARGIN, y)
    y = min(available.bottom() - widget.height() - SCREEN_MARGIN, y)
    widget.move(x, y)


def dock_to_edge(widget: QWidget, edge: DockEdge) -> None:
    available = screen_geometry(widget)
    if available.isNull() or edge is DockEdge.NONE:
        return

    width = widget.width()
    height = widget.height()
    rect = widget.frameGeometry()
    visible_width = max(int(width * DOCK_VISIBLE_RATIO), 24)
    visible_height = max(int(height * DOCK_VISIBLE_RATIO), 24)

    x = rect.x()
    y = rect.y()

    if edge is DockEdge.LEFT:
        x = available.left() - (width - visible_width)
        y = _clamp_axis(
            y,
            available.top() + SCREEN_MARGIN,
            available.bottom() - height - SCREEN_MARGIN,
        )
    elif edge is DockEdge.RIGHT:
        x = available.right() - visible_width
        y = _clamp_axis(
            y,
            available.top() + SCREEN_MARGIN,
            available.bottom() - height - SCREEN_MARGIN,
        )
    elif edge is DockEdge.TOP:
        y = available.top() - (height - visible_height)
        x = _clamp_axis(
            x,
            available.left() + SCREEN_MARGIN,
            available.right() - width - SCREEN_MARGIN,
        )
    elif edge is DockEdge.BOTTOM:
        y = available.bottom() - visible_height
        x = _clamp_axis(
            x,
            available.left() + SCREEN_MARGIN,
            available.right() - width - SCREEN_MARGIN,
        )

    widget.move(x, y)


def expand_from_dock(widget: QWidget, edge: DockEdge) -> None:
    available = screen_geometry(widget)
    if available.isNull() or edge is DockEdge.NONE:
        return

    rect = widget.frameGeometry()
    x = rect.x()
    y = rect.y()

    if edge is DockEdge.LEFT:
        x = available.left() + SCREEN_MARGIN
    elif edge is DockEdge.RIGHT:
        x = available.right() - widget.width() - SCREEN_MARGIN
    elif edge is DockEdge.TOP:
        y = available.top() + SCREEN_MARGIN
    elif edge is DockEdge.BOTTOM:
        y = available.bottom() - widget.height() - SCREEN_MARGIN

    widget.move(x, y)


def _clamp_axis(value: int, minimum: int, maximum: int) -> int:
    if maximum < minimum:
        return minimum
    return max(minimum, min(value, maximum))
