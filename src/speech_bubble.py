from __future__ import annotations

import json
import random
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from src.macos_window import apply_stay_visible_on_macos, enable_visible_when_inactive
from src.resource_utils import resource_path

MESSAGES_CONFIG = "config/messages.json"
FRAME_IMAGE = "assets/chatting-frame.png"
DEFAULT_MESSAGES = [
    "今天也要开心！",
    "你终于理我啦。",
    "要记得休息。",
    "我会在桌面陪着你。",
    "今天的任务完成了吗？",
]
BUBBLE_AUTO_HIDE_MS = 4000
BUBBLE_SCREEN_MARGIN = 8
BUBBLE_PET_GAP = 4
FRAME_SOURCE_WIDTH = 272
FRAME_SOURCE_HEIGHT = 250
FRAME_TEXT_LEFT = 38
FRAME_TEXT_TOP = 32
FRAME_TEXT_RIGHT = 234
FRAME_TEXT_BOTTOM = 168
FRAME_MIN_WIDTH = 120
FRAME_MAX_WIDTH = 170
FRAME_FONT_POINT_SIZE = 9


def load_messages(config_path: Path | None = None) -> list[str]:
    path = config_path or resource_path(MESSAGES_CONFIG)
    try:
        if not path.exists():
            return list(DEFAULT_MESSAGES)

        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        messages = data.get("double_click_messages", [])
        if not isinstance(messages, list) or not messages:
            return list(DEFAULT_MESSAGES)

        cleaned = [str(message).strip() for message in messages if str(message).strip()]
        return cleaned or list(DEFAULT_MESSAGES)
    except (OSError, json.JSONDecodeError, TypeError, AttributeError, ValueError):
        return list(DEFAULT_MESSAGES)


class SpeechBubble(QWidget):
    def __init__(self, pet_window: QWidget) -> None:
        super().__init__(pet_window)
        self._pet_window = pet_window
        self._messages = load_messages()
        self._frame_pixmap = self._load_frame_pixmap()

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self._frame_label = QLabel(self)
        self._frame_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._text_label = QLabel(self)
        self._text_label.setWordWrap(True)
        self._text_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        font = QFont()
        font.setPointSize(FRAME_FONT_POINT_SIZE)
        self._text_label.setFont(font)
        self._text_label.setStyleSheet(
            "QLabel { background: transparent; color: #2b2b2b; }"
        )

        self._setup_window()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        enable_visible_when_inactive(self)

    def _load_frame_pixmap(self) -> QPixmap:
        frame_path = resource_path(FRAME_IMAGE)
        if not frame_path.exists():
            return QPixmap()

        pixmap = QPixmap(str(frame_path))
        if pixmap.isNull():
            return QPixmap()

        return pixmap

    def show_for_pet(self) -> None:
        self.show_message(random.choice(self._messages))

    def show_message(
        self,
        message: str,
        *,
        hide_ms: int | None = None,
        force_frame: bool = False,
    ) -> None:
        self._apply_message_layout(message, force_frame=force_frame)
        self._position_above_pet()
        self.show()
        apply_stay_visible_on_macos(self)
        duration = hide_ms if hide_ms is not None else BUBBLE_AUTO_HIDE_MS
        if "\n" in message:
            duration = max(duration, 6000)
        self._hide_timer.start(duration)

    def _apply_message_layout(self, message: str, *, force_frame: bool = False) -> None:
        self._text_label.setText(message)

        if not self._frame_pixmap.isNull() and (force_frame or "\n" not in message):
            self._apply_framed_layout(message)
            return

        self._apply_fallback_layout(message)

    def _apply_framed_layout(self, message: str) -> None:
        self._text_label.setStyleSheet(
            "QLabel { background: transparent; color: #2b2b2b; }"
        )
        self._text_label.setMaximumWidth(16777215)

        source_inner_width = FRAME_TEXT_RIGHT - FRAME_TEXT_LEFT
        metrics = QFontMetrics(self._text_label.font())
        text_rect = metrics.boundingRect(
            0,
            0,
            source_inner_width,
            10000,
            Qt.TextFlag.TextWordWrap,
            message,
        )

        scale = FRAME_MIN_WIDTH / FRAME_SOURCE_WIDTH
        needed_scale = max(
            scale,
            (text_rect.width() + 24) / source_inner_width,
            (text_rect.height() + 20) / (FRAME_TEXT_BOTTOM - FRAME_TEXT_TOP),
        )
        max_scale = FRAME_MAX_WIDTH / FRAME_SOURCE_WIDTH
        scale = min(max(needed_scale, scale), max_scale)

        frame_width = max(int(FRAME_SOURCE_WIDTH * scale), FRAME_MIN_WIDTH)
        frame_height = max(
            int(FRAME_SOURCE_HEIGHT * scale),
            int(frame_width * FRAME_SOURCE_HEIGHT / FRAME_SOURCE_WIDTH),
        )

        frame = self._frame_pixmap.scaled(
            frame_width,
            frame_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._frame_label.setPixmap(frame)
        self._frame_label.resize(frame.size())

        width_ratio = frame.width() / FRAME_SOURCE_WIDTH
        height_ratio = frame.height() / FRAME_SOURCE_HEIGHT
        text_left = int(FRAME_TEXT_LEFT * width_ratio)
        text_top = int(FRAME_TEXT_TOP * height_ratio)
        text_width = int((FRAME_TEXT_RIGHT - FRAME_TEXT_LEFT) * width_ratio)
        text_height = int((FRAME_TEXT_BOTTOM - FRAME_TEXT_TOP) * height_ratio)

        self._text_label.setFixedSize(text_width, text_height)
        self._text_label.move(text_left, text_top)
        self.resize(frame.size())

    def _apply_fallback_layout(self, message: str) -> None:
        self._frame_label.clear()
        self._frame_label.resize(0, 0)
        max_width = 220 if "\n" in message else 150
        self._text_label.setMaximumWidth(max_width)
        self._text_label.setStyleSheet(
            "QLabel {"
            "  background-color: rgba(255, 255, 255, 230);"
            "  color: #2b2b2b;"
            "  border: 1px solid rgba(0, 0, 0, 40);"
            "  border-radius: 12px;"
            "  padding: 10px 14px;"
            "}"
        )
        self._text_label.adjustSize()
        self._text_label.move(0, 0)
        self.resize(self._text_label.size())

    def _position_above_pet(self) -> None:
        screen = self._pet_window.screen() or QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        pet_rect = self._pet_window.frameGeometry()

        x = pet_rect.center().x() - self.width() // 2
        y = pet_rect.top() - self.height() - BUBBLE_PET_GAP

        if y < available.top() + BUBBLE_SCREEN_MARGIN:
            y = pet_rect.bottom() + BUBBLE_PET_GAP

        x = max(available.left() + BUBBLE_SCREEN_MARGIN, x)
        x = min(available.right() - BUBBLE_SCREEN_MARGIN - self.width(), x)
        y = max(available.top() + BUBBLE_SCREEN_MARGIN, y)
        y = min(available.bottom() - BUBBLE_SCREEN_MARGIN - self.height(), y)

        self.move(x, y)

    def hide_bubble(self) -> None:
        self._hide_timer.stop()
        self.hide()
