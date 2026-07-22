from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from src.resource_utils import resource_path

APP_ICON_IMAGE = "assets/floating_ball/image.png"


def app_icon_path() -> Path:
    return resource_path(APP_ICON_IMAGE)


def apply_app_icon(app: QApplication) -> None:
    path = app_icon_path()
    if not path.exists():
        return

    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return

    app.setWindowIcon(QIcon(pixmap))

    if sys.platform != "darwin":
        return

    try:
        from AppKit import NSApplication, NSImage
    except ImportError:
        return

    ns_image = NSImage.alloc().initWithContentsOfFile_(str(path))
    if ns_image is not None:
        NSApplication.sharedApplication().setApplicationIconImage_(ns_image)
