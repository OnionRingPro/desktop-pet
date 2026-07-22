from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from src.resource_utils import resource_path

FALLBACK_IMAGE = "assets/fallback.png"
IDLE_DIR = "assets/idle"

MAX_DISPLAY_WIDTH = 100
MAX_DISPLAY_HEIGHT = 125


class AnimationState(Enum):
    IDLE = "idle"
    WALK = "walk"
    WALK_LEFT = "walk_left"
    WALK_RIGHT = "walk_right"
    HAPPY = "happy"
    DRAGGING = "dragging"


MENU_STATES = (
    AnimationState.IDLE,
    AnimationState.WALK,
    AnimationState.HAPPY,
    AnimationState.DRAGGING,
)

STATE_LABELS = {
    AnimationState.IDLE: "待机",
    AnimationState.WALK: "行走",
    AnimationState.HAPPY: "开心",
    AnimationState.DRAGGING: "拖动",
}

FRAME_MS = {
    AnimationState.IDLE: 350,
    AnimationState.WALK: 120,
    AnimationState.WALK_LEFT: 120,
    AnimationState.WALK_RIGHT: 120,
    AnimationState.HAPPY: 180,
    AnimationState.DRAGGING: 160,
}


@dataclass
class Animation:
    frames: list[QPixmap]
    frame_ms: int
    loop: bool = True


class AnimationManager:
    def __init__(self, label: QLabel, parent: QWidget) -> None:
        self._label = label
        self._parent = parent
        self._animations: dict[AnimationState, Animation] = {}
        self._fallback = self._load_fallback()
        self._current_state = AnimationState.IDLE
        self._frame_index = 0
        self._paused = False
        self._display_size: tuple[int, int] | None = None

        self._timer = QTimer(parent)
        self._timer.timeout.connect(self._advance_frame)

        self._load_animations()
        self.set_state(AnimationState.IDLE)

    @property
    def current_state(self) -> AnimationState:
        return self._current_state

    def available_states(self) -> list[AnimationState]:
        return [state for state in MENU_STATES if state in self._animations]

    def set_state(self, state: AnimationState) -> None:
        self._paused = False
        self._current_state = state
        self._frame_index = 0

        animation = self._animations.get(state)
        if animation and animation.frames:
            self._show_frame(0)
            self._timer.start(animation.frame_ms)
            return

        self._timer.stop()
        self._show_fallback()

    def pause(self) -> None:
        self._paused = True
        self._timer.stop()

    def on_drag_start(self) -> None:
        if AnimationState.DRAGGING in self._animations:
            self.set_state(AnimationState.DRAGGING)
        else:
            self.pause()

    def on_drag_end(self, return_state: AnimationState) -> None:
        self.set_state(return_state)

    def stop(self) -> None:
        self._timer.stop()

    def current_display_size(self) -> tuple[int, int]:
        if self._display_size is not None:
            return self._display_size
        if not self._fallback.isNull():
            scaled = self._scale_pixmap(self._fallback)
            return scaled.width(), scaled.height()
        return 75, 100

    def _load_animations(self) -> None:
        idle_frames = self._load_frames_from_dir(IDLE_DIR)
        if idle_frames:
            self._animations[AnimationState.IDLE] = Animation(
                idle_frames,
                FRAME_MS[AnimationState.IDLE],
            )

        for state in (
            AnimationState.WALK,
            AnimationState.WALK_LEFT,
            AnimationState.WALK_RIGHT,
            AnimationState.HAPPY,
            AnimationState.DRAGGING,
        ):
            frames = self._load_frames_from_dir(f"assets/{state.value}")
            if frames:
                self._animations[state] = Animation(
                    frames,
                    FRAME_MS[state],
                )

    def _load_frames_from_dir(self, relative_dir: str) -> list[QPixmap]:
        directory = resource_path(relative_dir)
        if not directory.is_dir():
            return []

        frames: list[QPixmap] = []
        for path in sorted(directory.glob("*.png")):
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                continue
            frames.append(pixmap)
        return frames

    def _load_fallback(self) -> QPixmap:
        fallback_path = resource_path(FALLBACK_IMAGE)
        if not fallback_path.exists():
            return QPixmap()

        pixmap = QPixmap(str(fallback_path))
        if pixmap.isNull():
            return QPixmap()
        return pixmap

    def _advance_frame(self) -> None:
        if self._paused:
            return

        animation = self._animations.get(self._current_state)
        if animation is None or not animation.frames:
            self._timer.stop()
            return

        next_index = self._frame_index + 1
        if next_index >= len(animation.frames):
            if not animation.loop:
                self._timer.stop()
                return
            next_index = 0

        self._frame_index = next_index
        self._show_frame(next_index)

    def _show_frame(self, index: int) -> None:
        animation = self._animations.get(self._current_state)
        if animation is None or index >= len(animation.frames):
            self._show_fallback()
            return

        display = self._scale_pixmap(animation.frames[index])
        self._label.setPixmap(display)
        self._label.resize(display.size())
        self._display_size = (display.width(), display.height())

    def _show_fallback(self) -> None:
        if self._fallback.isNull():
            placeholder = QPixmap(75, 100)
            placeholder.fill(Qt.GlobalColor.transparent)
            self._label.setPixmap(placeholder)
            self._label.resize(placeholder.size())
            self._display_size = (placeholder.width(), placeholder.height())
            return

        display = self._scale_pixmap(self._fallback)
        self._label.setPixmap(display)
        self._label.resize(display.size())
        self._display_size = (display.width(), display.height())

    def _scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        if (
            pixmap.width() <= MAX_DISPLAY_WIDTH
            and pixmap.height() <= MAX_DISPLAY_HEIGHT
        ):
            return pixmap

        return pixmap.scaled(
            MAX_DISPLAY_WIDTH,
            MAX_DISPLAY_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
