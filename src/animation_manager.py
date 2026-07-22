from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from src.resource_utils import resource_path

FALLBACK_IMAGE = "assets/fallback.png"
IDLE_DIR = "assets/idle"
MESSAGES_CONFIG = "config/messages.json"

DEFAULT_DISPLAY_MAX_SIZE = 100
MIN_DISPLAY_MAX_SIZE = 80
MAX_DISPLAY_MAX_SIZE = 280


class AnimationState(Enum):
    IDLE = "idle"
    WALK = "walk"
    WALK_LEFT = "walk_left"
    WALK_RIGHT = "walk_right"
    HAPPY = "happy"
    DRINK = "drink"
    DRAGGING = "dragging"
    SLEEP = "sleep"


MENU_STATES = (
    AnimationState.IDLE,
    AnimationState.HAPPY,
    AnimationState.DRINK,
    AnimationState.SLEEP,
    AnimationState.WALK,
    AnimationState.DRAGGING,
)

STATE_LABELS = {
    AnimationState.IDLE: "待机",
    AnimationState.WALK: "行走",
    AnimationState.HAPPY: "开心",
    AnimationState.DRINK: "喝水",
    AnimationState.SLEEP: "睡觉",
    AnimationState.DRAGGING: "拖动",
}

FRAME_MS = {
    AnimationState.IDLE: 350,
    AnimationState.WALK: 120,
    AnimationState.WALK_LEFT: 120,
    AnimationState.WALK_RIGHT: 120,
    AnimationState.HAPPY: 180,
    AnimationState.DRINK: 180,
    AnimationState.DRAGGING: 160,
    AnimationState.SLEEP: 500,
}


@dataclass
class Animation:
    frames: list[QPixmap]
    frame_ms: int
    loop: bool = True


def load_display_max_size(config_path: Path | None = None) -> int:
    path = config_path or resource_path(MESSAGES_CONFIG)
    size = DEFAULT_DISPLAY_MAX_SIZE
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            size = int(data.get("pet_display_size", size))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return max(MIN_DISPLAY_MAX_SIZE, min(MAX_DISPLAY_MAX_SIZE, size))


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
        self._display_max_size = load_display_max_size()

        self._timer = QTimer(parent)
        self._timer.timeout.connect(self._advance_frame)

        self._load_animations()
        self.set_state(AnimationState.IDLE)

    @property
    def current_state(self) -> AnimationState:
        return self._current_state

    def available_states(self) -> list[AnimationState]:
        return [state for state in MENU_STATES if state in self._animations]

    def has_state(self, state: AnimationState) -> bool:
        animation = self._animations.get(state)
        return animation is not None and bool(animation.frames)

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

    def pause_for_overlay(self) -> None:
        self.pause()

    def show_overlay_pixmap(self, pixmap: QPixmap) -> None:
        self._timer.stop()
        if pixmap.isNull():
            return
        self._label.setPixmap(pixmap)
        self._label.resize(pixmap.size())
        self._display_size = (pixmap.width(), pixmap.height())

    def resume_after_overlay(self) -> None:
        self.set_state(self._current_state)

    def on_drag_start(self) -> None:
        if AnimationState.DRAGGING in self._animations:
            self.set_state(AnimationState.DRAGGING)
        else:
            self.pause()

    def on_drag_end(self, return_state: AnimationState) -> None:
        self.set_state(return_state)

    def stop(self) -> None:
        self._timer.stop()

    def display_max_size(self) -> int:
        return self._display_max_size

    def set_display_max_size(self, size: int) -> None:
        self._display_max_size = max(
            MIN_DISPLAY_MAX_SIZE,
            min(MAX_DISPLAY_MAX_SIZE, size),
        )
        self.refresh_display()

    def refresh_display(self) -> None:
        animation = self._animations.get(self._current_state)
        if animation and animation.frames:
            self._show_frame(self._frame_index)
            return
        self._show_fallback()

    def current_display_size(self) -> tuple[int, int]:
        if self._display_size is not None:
            return self._display_size
        if not self._fallback.isNull():
            scaled = self._scale_pixmap(self._fallback)
            return scaled.width(), scaled.height()
        return self._placeholder_size()

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
            AnimationState.DRINK,
            AnimationState.DRAGGING,
            AnimationState.SLEEP,
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
            width, height = self._placeholder_size()
            placeholder = QPixmap(width, height)
            placeholder.fill(Qt.GlobalColor.transparent)
            self._label.setPixmap(placeholder)
            self._label.resize(placeholder.size())
            self._display_size = (width, height)
            return

        display = self._scale_pixmap(self._fallback)
        self._label.setPixmap(display)
        self._label.resize(display.size())
        self._display_size = (display.width(), display.height())

    def _placeholder_size(self) -> tuple[int, int]:
        width = int(self._display_max_size * 0.75)
        height = self._display_max_size
        return width, height

    def _scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        return pixmap.scaled(
            self._display_max_size,
            self._display_max_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
