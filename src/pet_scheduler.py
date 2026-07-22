from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QTimer

from src.animation_manager import AnimationState
from src.resource_utils import resource_path

MESSAGES_CONFIG = "config/messages.json"
DEFAULT_MOOD_IDLE_SECONDS = 45
DEFAULT_MOOD_HAPPY_SECONDS = 12
DEFAULT_MOOD_DRINK_SECONDS = 10
DEFAULT_REMINDER_MINUTES = 45

AUTO_MOOD_STATES = (
    AnimationState.IDLE,
    AnimationState.HAPPY,
    AnimationState.DRINK,
)


@dataclass(frozen=True)
class SchedulerConfig:
    mood_idle_ms: int
    mood_happy_ms: int
    mood_drink_ms: int
    reminder_ms: int


def load_scheduler_config(config_path: Path | None = None) -> SchedulerConfig:
    path = config_path or resource_path(MESSAGES_CONFIG)
    idle_seconds = DEFAULT_MOOD_IDLE_SECONDS
    happy_seconds = DEFAULT_MOOD_HAPPY_SECONDS
    drink_seconds = DEFAULT_MOOD_DRINK_SECONDS
    reminder_minutes = DEFAULT_REMINDER_MINUTES

    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            idle_seconds = int(data.get("mood_idle_seconds", idle_seconds))
            happy_seconds = int(data.get("mood_happy_seconds", happy_seconds))
            drink_seconds = int(data.get("mood_drink_seconds", drink_seconds))
            reminder_minutes = int(data.get("reminder_minutes", reminder_minutes))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass

    idle_seconds = max(idle_seconds, 5)
    happy_seconds = max(happy_seconds, 3)
    drink_seconds = max(drink_seconds, 3)
    reminder_minutes = max(reminder_minutes, 1)

    return SchedulerConfig(
        mood_idle_ms=idle_seconds * 1000,
        mood_happy_ms=happy_seconds * 1000,
        mood_drink_ms=drink_seconds * 1000,
        reminder_ms=reminder_minutes * 60 * 1000,
    )


class PetScheduler:
    def __init__(self, pet_window) -> None:
        self._pet = pet_window
        self._config = load_scheduler_config()
        self._auto_mood = True
        self._mood_paused_remaining_ms: int | None = None

        self._mood_timer = QTimer(pet_window)
        self._mood_timer.setSingleShot(True)
        self._mood_timer.timeout.connect(self._on_mood_cycle)

        self._speech_timer = QTimer(pet_window)
        self._speech_timer.timeout.connect(self._on_reminder_speech)
        self._speech_timer.start(self._config.reminder_ms)

    def start(self) -> None:
        self._schedule_next_mood()

    def stop(self) -> None:
        self._mood_timer.stop()
        self._speech_timer.stop()

    def pause_mood(self) -> None:
        if self._mood_timer.isActive():
            remaining = self._mood_timer.remainingTime()
            if remaining > 0:
                self._mood_paused_remaining_ms = remaining
        self._mood_timer.stop()

    def resume_mood(self) -> None:
        self._schedule_next_mood(remaining_ms=self._mood_paused_remaining_ms)
        self._mood_paused_remaining_ms = None

    def on_manual_state(self, state: AnimationState) -> None:
        self._auto_mood = state in AUTO_MOOD_STATES
        self._mood_paused_remaining_ms = None
        if self._auto_mood:
            self._schedule_next_mood()
        else:
            self._mood_timer.stop()

    def _mood_duration(self, state: AnimationState) -> int:
        if state is AnimationState.HAPPY:
            return self._config.mood_happy_ms
        if state is AnimationState.DRINK:
            return self._config.mood_drink_ms
        return self._config.mood_idle_ms

    def _schedule_next_mood(self, remaining_ms: int | None = None) -> None:
        if not self._auto_mood or self._pet._dragging:
            return

        animation = self._pet._animation
        current = self._pet._selected_state
        if current not in AUTO_MOOD_STATES:
            return
        if current not in animation.available_states():
            return

        full_duration = self._mood_duration(current)
        duration = (
            remaining_ms
            if remaining_ms is not None and remaining_ms > 0
            else full_duration
        )
        self._mood_timer.start(duration)

    def _next_auto_mood_state(self, current: AnimationState) -> AnimationState | None:
        available = set(self._pet._animation.available_states())
        cycle = [state for state in AUTO_MOOD_STATES if state in available]
        if current not in cycle:
            return cycle[0] if cycle else None

        index = cycle.index(current)
        return cycle[(index + 1) % len(cycle)]

    def _on_mood_cycle(self) -> None:
        if not self._auto_mood or self._pet._dragging:
            self._schedule_next_mood()
            return

        current = self._pet._selected_state
        next_state = self._next_auto_mood_state(current)
        if next_state is not None and next_state is not current:
            self._pet._apply_animation_state(next_state, from_scheduler=True)
        else:
            self._schedule_next_mood()

    def _on_reminder_speech(self) -> None:
        if self._pet._dragging:
            return
        self._pet._speech_bubble.show_for_pet()
