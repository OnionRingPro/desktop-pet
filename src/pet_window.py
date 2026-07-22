from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QMouseEvent, QShowEvent, QActionGroup
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from src.animation_manager import (
    AnimationManager,
    AnimationState,
    STATE_LABELS,
)
from src.edge_dock import (
    DockEdge,
    clamp_fully_on_screen,
    detect_snap_edge,
    dock_to_edge,
    expand_from_dock,
    is_docked,
)
from src.macos_window import apply_stay_visible_on_macos, enable_visible_when_inactive
from src.pet_scheduler import PetScheduler
from src.resource_utils import resource_path
from src.speech_bubble import SpeechBubble

FALLBACK_IMAGE = "assets/fallback.png"
IDLE_DIR = "assets/idle"


class PetWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._dragging = False
        self._drag_offset = QPoint()
        self._docked_edge = DockEdge.NONE

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._speech_bubble = SpeechBubble(self)
        self._animation = AnimationManager(self._label, self)
        self._selected_state = AnimationState.IDLE
        self._scheduler = PetScheduler(self)

        self._setup_window()
        self._check_assets()
        self._apply_window_size()
        self._move_to_default_position()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        enable_visible_when_inactive(self)
        enable_visible_when_inactive(self._speech_bubble)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_macos_visibility)
        QTimer.singleShot(200, self._apply_macos_visibility)
        self._scheduler.start()

    def _apply_macos_visibility(self) -> None:
        apply_stay_visible_on_macos(self)
        if self._speech_bubble.isVisible():
            apply_stay_visible_on_macos(self._speech_bubble)

    def _check_assets(self) -> None:
        fallback_path = resource_path(FALLBACK_IMAGE)
        idle_dir = resource_path(IDLE_DIR)

        has_idle = idle_dir.is_dir() and any(idle_dir.glob("*.png"))
        has_fallback = fallback_path.exists()

        if has_idle or has_fallback:
            return

        self._show_missing_image_message(fallback_path)

    def _apply_window_size(self) -> None:
        width, height = self._animation.current_display_size()
        self.resize(width, height)

    def _show_missing_image_message(self, image_path: Path) -> None:
        QMessageBox.warning(
            self,
            "缺少桌宠图片",
            (
                f"未找到图片文件：\n{image_path}\n\n"
                "请将一张透明背景 PNG 保存为 assets/fallback.png 后重新启动。\n"
                "当前将显示空白占位窗口。"
            ),
        )

    def _move_to_default_position(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        x = available.right() - self.width() - 40
        y = available.bottom() - self.height() - 40
        self.move(x, y)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        state_group = QActionGroup(menu)
        state_group.setExclusive(True)

        for state in self._animation.available_states():
            action = menu.addAction(STATE_LABELS[state])
            action.setCheckable(True)
            action.setChecked(state is self._selected_state)
            state_group.addAction(action)
            action.triggered.connect(
                lambda _checked=False, s=state: self._set_animation_state(s)
            )

        if menu.actions():
            menu.addSeparator()

        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.exec(event.globalPos())

    def _set_animation_state(self, state: AnimationState) -> None:
        self._apply_animation_state(state, from_scheduler=False)

    def _apply_animation_state(
        self,
        state: AnimationState,
        *,
        from_scheduler: bool,
    ) -> None:
        self._selected_state = state
        if not self._dragging:
            self._animation.set_state(state)
        if not from_scheduler:
            self._scheduler.on_manual_state(state)
        else:
            self._scheduler.resume_mood()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if is_docked(self._docked_edge):
                expand_from_dock(self, self._docked_edge)
                self._docked_edge = DockEdge.NONE

            self._dragging = True
            self._scheduler.pause_mood()
            self._animation.on_drag_start()
            global_pos = event.globalPosition().toPoint()
            self._drag_offset = global_pos - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            self.move(global_pos - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._animation.on_drag_end(self._selected_state)
            self._apply_edge_dock()
            self._scheduler.resume_mood()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _apply_edge_dock(self) -> None:
        snap_edge = detect_snap_edge(self)
        if snap_edge is not DockEdge.NONE:
            dock_to_edge(self, snap_edge)
            self._docked_edge = snap_edge
            self._speech_bubble.hide_bubble()
            return

        self._docked_edge = DockEdge.NONE
        clamp_fully_on_screen(self)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._speech_bubble.show_for_pet()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._scheduler.stop()
        self._animation.stop()
        self._speech_bubble.hide_bubble()
        super().closeEvent(event)
