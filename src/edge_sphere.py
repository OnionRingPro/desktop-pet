from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from src.resource_utils import resource_path

PEEP_IMAGE = "assets/peep/001.png"
FLOATING_BALL_IMAGE = "assets/floating_ball/image.png"
BALL_DISPLAY_SIZE = 32
PEEP_TARGET_HEIGHT = 120
CURSOR_RIGHT_EDGE_THRESHOLD = 0
SCREEN_MARGIN = 4


class SphereDockMode(Enum):
    NONE = "none"
    BALL = "ball"
    PEEK = "peek"


_ball_pixmap_cache: QPixmap | None = None
_ball_source_cache: QPixmap | None = None
_peep_pixmap_cache: QPixmap | None = None
_cropped_peep_cache: QPixmap | None = None


def screen_geometry(widget: QWidget):
    screen = widget.screen() or QApplication.primaryScreen()
    if screen is None:
        from PySide6.QtCore import QRect

        return QRect()
    return screen.availableGeometry()


def screen_right_edge(widget: QWidget) -> int:
    screen = widget.screen() or QApplication.primaryScreen()
    if screen is None:
        return screen_geometry(widget).right()
    return screen.geometry().right()


def _crop_to_opaque_bounds(peep: QPixmap) -> QPixmap:
    if peep.isNull():
        return QPixmap()

    image = peep.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    width = image.width()
    height = image.height()

    left = width
    right = 0
    top = height
    bottom = 0

    for y in range(height):
        for x in range(width):
            if image.pixelColor(x, y).alpha() > 10:
                left = min(left, x)
                right = max(right, x)
                top = min(top, y)
                bottom = max(bottom, y)

    if right < left or bottom < top:
        return peep

    return peep.copy(left, top, right - left + 1, bottom - top + 1)


def prepare_peep_pixmap() -> QPixmap:
    global _cropped_peep_cache
    if _cropped_peep_cache is not None:
        return _cropped_peep_cache

    source = load_peep_pixmap()
    if source.isNull():
        return QPixmap()

    _cropped_peep_cache = _crop_to_opaque_bounds(source)
    return _cropped_peep_cache


def load_peep_pixmap() -> QPixmap:
    global _peep_pixmap_cache
    if _peep_pixmap_cache is not None:
        return _peep_pixmap_cache

    path = resource_path(PEEP_IMAGE)
    if not path.exists():
        return QPixmap()

    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return QPixmap()

    _peep_pixmap_cache = pixmap
    return pixmap


def load_ball_pixmap() -> QPixmap:
    global _ball_pixmap_cache
    if _ball_pixmap_cache is not None:
        return _ball_pixmap_cache

    source = _load_ball_source()
    if source.isNull():
        return QPixmap()

    cropped = _crop_to_opaque_bounds(source)
    if cropped.isNull():
        cropped = source

    _ball_pixmap_cache = cropped.scaled(
        BALL_DISPLAY_SIZE,
        BALL_DISPLAY_SIZE,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return _ball_pixmap_cache


def _load_ball_source() -> QPixmap:
    global _ball_source_cache
    if _ball_source_cache is not None:
        return _ball_source_cache

    path = resource_path(FLOATING_BALL_IMAGE)
    if not path.exists():
        return QPixmap()

    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return QPixmap()

    _ball_source_cache = pixmap
    return _ball_source_cache


def scale_peep_pixmap(_peep: QPixmap, _display_max_size: int) -> QPixmap:
    cropped = prepare_peep_pixmap()
    if cropped.isNull():
        return QPixmap()

    return cropped.scaled(
        int(cropped.width() * PEEP_TARGET_HEIGHT / cropped.height()),
        PEEP_TARGET_HEIGHT,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def should_sphere_dock(
    widget: QWidget,
    *,
    cursor_global: QPoint | None = None,
) -> bool:
    available = screen_geometry(widget)
    if available.isNull():
        return False

    if cursor_global is None:
        from PySide6.QtGui import QCursor

        cursor_global = QCursor.pos()

    return cursor_global.x() >= available.right() - CURSOR_RIGHT_EDGE_THRESHOLD


def ball_position(anchor_y: int, ball_size, available) -> tuple[int, int]:
    # Align the full ball to the visible desktop edge. Partial off-screen
    # clipping showed the transparent side of the circular icon instead.
    x = available.right() - ball_size.width() + 1
    y = anchor_y - ball_size.height() // 2
    y = max(available.top() + SCREEN_MARGIN, y)
    y = min(available.bottom() - ball_size.height() - SCREEN_MARGIN, y)
    return x, y


def peep_position(anchor_y: int, peep_size, available, *, screen_right: int | None = None) -> tuple[int, int]:
    right_edge = screen_right if screen_right is not None else available.right()
    x = right_edge - peep_size.width() + 1
    y = anchor_y - peep_size.height() // 2
    y = max(available.top() + SCREEN_MARGIN, y)
    y = min(available.bottom() - peep_size.height() - SCREEN_MARGIN, y)
    return x, y
