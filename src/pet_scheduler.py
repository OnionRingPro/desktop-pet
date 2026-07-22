from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QTimer

from src.animation_manager import AnimationState
from src.resource_utils import resource_path

MESSAGES_CONFIG = "config/messages.json"
DEFAULT_MOOD_IDLE_SECONDS = 45
DEFAULT_MOOD_HAPPY_SECONDS = 12
DEFAULT_MOOD_DRINK_SECONDS = 10
DEFAULT_SLEEP_INACTIVITY_SECONDS = 100
DEFAULT_SLEEP_DURATION_SECONDS = 100
DEFAULT_REMINDER_MINUTES = 45
DEFAULT_WAKE_FROM_SLEEP_MESSAGES = (
    "早呀！",
    "你回来啦。",
    "睡够啦，精神满满！",
    "嗯？是谁在叫我？",
)

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
    sleep_inactivity_ms: int
    sleep_duration_ms: int
    reminder_ms: int


def load_wake_from_sleep_messages(config_path: Path | None = None) -> list[str]:
    path = config_path or resource_path(MESSAGES_CONFIG)
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            raw = data.get("wake_from_sleep_messages")
            if isinstance(raw, list):
                messages = [str(message).strip() for message in raw if str(message).strip()]
                if messages:
                    return messages
            legacy = str(data.get("wake_from_sleep_message", "")).strip()
            if legacy:
                return [legacy]
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return list(DEFAULT_WAKE_FROM_SLEEP_MESSAGES)


def load_scheduler_config(config_path: Path | None = None) -> SchedulerConfig:
    path = config_path or resource_path(MESSAGES_CONFIG)
    idle_seconds = DEFAULT_MOOD_IDLE_SECONDS
    happy_seconds = DEFAULT_MOOD_HAPPY_SECONDS
    drink_seconds = DEFAULT_MOOD_DRINK_SECONDS
    sleep_seconds = DEFAULT_SLEEP_INACTIVITY_SECONDS
    sleep_duration_seconds = DEFAULT_SLEEP_DURATION_SECONDS
    reminder_minutes = DEFAULT_REMINDER_MINUTES

    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            idle_seconds = int(data.get("mood_idle_seconds", idle_seconds))
            happy_seconds = int(data.get("mood_happy_seconds", happy_seconds))
            drink_seconds = int(data.get("mood_drink_seconds", drink_seconds))
            sleep_seconds = int(data.get("sleep_inactivity_seconds", sleep_seconds))
            sleep_duration_seconds = int(
                data.get("sleep_duration_seconds", sleep_duration_seconds)
            )
            reminder_minutes = int(data.get("reminder_minutes", reminder_minutes))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass

    idle_seconds = max(idle_seconds, 5)
    happy_seconds = max(happy_seconds, 3)
    drink_seconds = max(drink_seconds, 3)
    sleep_seconds = max(sleep_seconds, 10)
    sleep_duration_seconds = max(sleep_duration_seconds, 5)
    reminder_minutes = max(reminder_minutes, 1)

    return SchedulerConfig(
        mood_idle_ms=idle_seconds * 1000,
        mood_happy_ms=happy_seconds * 1000,
        mood_drink_ms=drink_seconds * 1000,
        sleep_inactivity_ms=sleep_seconds * 1000,
        sleep_duration_ms=sleep_duration_seconds * 1000,
        reminder_ms=reminder_minutes * 60 * 1000,
    )


class PetScheduler:
    def __init__(self, pet_window) -> None:
        self._pet = pet_window
        self._config = load_scheduler_config()
        self._wake_messages = load_wake_from_sleep_messages()
        self._auto_mood = True
        self._mood_paused_remaining_ms: int | None = None
        self._sleep_paused_remaining_ms: int | None = None

        self._mood_timer = QTimer(pet_window)
        self._mood_timer.setSingleShot(True)
        self._mood_timer.timeout.connect(self._on_mood_cycle)

        self._inactivity_timer = QTimer(pet_window)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.timeout.connect(self._on_inactivity)

        self._sleep_timer = QTimer(pet_window)
        self._sleep_timer.setSingleShot(True)
        self._sleep_timer.timeout.connect(self._on_sleep_end)

        self._speech_timer = QTimer(pet_window)
        self._speech_timer.timeout.connect(self._on_reminder_speech)
        self._speech_timer.start(self._config.reminder_ms)

    def start(self) -> None:
        self._schedule_next_mood()
        self._reset_inactivity_timer()

    def stop(self) -> None:
        self._mood_timer.stop()
        self._inactivity_timer.stop()
        self._sleep_timer.stop()
        self._speech_timer.stop()

    def pause_mood(self) -> None:
        if self._mood_timer.isActive():
            remaining = self._mood_timer.remainingTime()
            if remaining > 0:
                self._mood_paused_remaining_ms = remaining
        self._mood_timer.stop()
        self._inactivity_timer.stop()
        if self._sleep_timer.isActive():
            remaining = self._sleep_timer.remainingTime()
            if remaining > 0:
                self._sleep_paused_remaining_ms = remaining
        self._sleep_timer.stop()

    def resume_mood(self) -> None:
        if self._pet._selected_state is AnimationState.SLEEP:
            self._resume_sleep_timer()
        else:
            self._schedule_next_mood(remaining_ms=self._mood_paused_remaining_ms)
            self._mood_paused_remaining_ms = None
            self._reset_inactivity_timer()

    def _wake_from_sleep(self) -> None:
        self._sleep_timer.stop()
        self._sleep_paused_remaining_ms = None
        if self._pet._selected_state is not AnimationState.SLEEP:
            return
        self._pet._apply_animation_state(AnimationState.IDLE, from_scheduler=True)
        self._pet._speech_bubble.show_message(random.choice(self._wake_messages))

    def notify_user_activity(self) -> None:
        if self._pet._selected_state is AnimationState.SLEEP:
            self._wake_from_sleep()
            return

        self._reset_inactivity_timer()

    def on_manual_state(self, state: AnimationState) -> None:
        self._sleep_timer.stop()
        self._sleep_paused_remaining_ms = None
        self._mood_paused_remaining_ms = None
        self._auto_mood = state in AUTO_MOOD_STATES

        if state is AnimationState.SLEEP:
            self._mood_timer.stop()
            self._inactivity_timer.stop()
            self._start_sleep_timer()
            return

        if self._auto_mood:
            self._schedule_next_mood(remaining_ms=None)
        else:
            self._mood_timer.stop()

        self._reset_inactivity_timer()

    def on_scheduler_state(self, state: AnimationState) -> None:
        if state is AnimationState.SLEEP:
            self._mood_timer.stop()
            self._inactivity_timer.stop()
            self._start_sleep_timer()
            return

        if state in AUTO_MOOD_STATES:
            self._schedule_next_mood(remaining_ms=None)
            self._reset_inactivity_timer()

    def _start_sleep_timer(self, remaining_ms: int | None = None) -> None:
        duration = (
            remaining_ms
            if remaining_ms is not None and remaining_ms > 0
            else self._config.sleep_duration_ms
        )
        self._sleep_timer.start(duration)

    def _resume_sleep_timer(self) -> None:
        self._start_sleep_timer(remaining_ms=self._sleep_paused_remaining_ms)
        self._sleep_paused_remaining_ms = None

    def _on_sleep_end(self) -> None:
        if self._pet._selected_state is not AnimationState.SLEEP:
            return
        self._wake_from_sleep()

    def _mood_duration(self, state: AnimationState) -> int:
        if state is AnimationState.HAPPY:
            return self._config.mood_happy_ms
        if state is AnimationState.DRINK:
            return self._config.mood_drink_ms
        return self._config.mood_idle_ms

    def _schedule_next_mood(self, remaining_ms: int | None = None) -> None:
        if not self._auto_mood or self._pet._dragging:
            return

        current = self._pet._selected_state
        if current is AnimationState.SLEEP:
            return
        if current not in AUTO_MOOD_STATES:
            return
        if not self._pet._animation.has_state(current):
            return

        full_duration = self._mood_duration(current)
        duration = (
            remaining_ms
            if remaining_ms is not None and remaining_ms > 0
            else full_duration
        )
        self._mood_timer.start(duration)

    def _reset_inactivity_timer(self) -> None:
        from src.edge_sphere import SphereDockMode

        if self._pet._sphere_mode is not SphereDockMode.NONE:
            self._inactivity_timer.stop()
            return

        if not self._pet._animation.has_state(AnimationState.SLEEP):
            return

        self._inactivity_timer.start(self._config.sleep_inactivity_ms)

    def _next_auto_mood_state(self, current: AnimationState) -> AnimationState | None:
        animation = self._pet._animation

        if current is AnimationState.IDLE:
            choices = [
                state
                for state in (AnimationState.HAPPY, AnimationState.DRINK)
                if animation.has_state(state)
            ]
            return random.choice(choices) if choices else None

        if current in (AnimationState.HAPPY, AnimationState.DRINK):
            return AnimationState.IDLE if animation.has_state(AnimationState.IDLE) else None

        return None

    def _on_mood_cycle(self) -> None:
        if not self._auto_mood or self._pet._dragging:
            self._schedule_next_mood()
            return

        current = self._pet._selected_state
        if current is AnimationState.SLEEP:
            return

        next_state = self._next_auto_mood_state(current)
        if next_state is not None and next_state is not current:
            self._pet._apply_animation_state(next_state, from_scheduler=True)
        else:
            self._schedule_next_mood(remaining_ms=None)

    def _on_inactivity(self) -> None:
        from src.edge_sphere import SphereDockMode

        if self._pet._dragging or self._pet._sphere_mode is not SphereDockMode.NONE:
            self._reset_inactivity_timer()
            return

        if not self._auto_mood:
            self._reset_inactivity_timer()
            return

        if not self._pet._animation.has_state(AnimationState.SLEEP):
            return

        if self._pet._selected_state is AnimationState.SLEEP:
            return

        self._mood_timer.stop()
        self._pet._apply_animation_state(AnimationState.SLEEP, from_scheduler=True)

    def _on_reminder_speech(self) -> None:
        if self._pet._dragging:
            return
        self._pet._speech_bubble.show_for_pet()
