from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import (
    QActionGroup,
    QCloseEvent,
    QEnterEvent,
    QMouseEvent,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QSlider,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from src.animation_manager import (
    AnimationManager,
    AnimationState,
    MAX_DISPLAY_MAX_SIZE,
    MIN_DISPLAY_MAX_SIZE,
    STATE_LABELS,
)
from src.edge_dock import (
    DockEdge,
    clamp_fully_on_screen,
    detect_snap_edge,
    dock_to_edge,
    expand_from_dock,
    is_docked,
    screen_geometry,
)
from src.edge_sphere import (
    SphereDockMode,
    ball_position,
    load_ball_pixmap,
    load_peep_pixmap,
    peep_position,
    scale_peep_pixmap,
    screen_right_edge,
    should_sphere_dock,
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
        self._sphere_mode = SphereDockMode.NONE
        self._sphere_anchor_y = 0
        self._sphere_allow_peep = False

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

    def _on_size_slider_changed(self, value: int, value_label: QLabel) -> None:
        value_label.setText(f"{value}px")
        self._animation.set_display_max_size(value)
        if self._sphere_mode is SphereDockMode.PEEK:
            self._show_peep()
        elif self._sphere_mode is SphereDockMode.BALL:
            self._show_sphere_ball()
        else:
            self._apply_window_size()
            if not is_docked(self._docked_edge):
                clamp_fully_on_screen(self)

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

        size_action = QWidgetAction(menu)
        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(12, 4, 12, 4)
        size_label = QLabel("大小")
        size_slider = QSlider(Qt.Orientation.Horizontal)
        size_slider.setRange(MIN_DISPLAY_MAX_SIZE, MAX_DISPLAY_MAX_SIZE)
        size_slider.setValue(self._animation.display_max_size())
        size_slider.setFixedWidth(140)
        size_value_label = QLabel(f"{size_slider.value()}px")
        size_slider.valueChanged.connect(
            lambda value, value_label=size_value_label: self._on_size_slider_changed(
                value, value_label
            )
        )
        size_layout.addWidget(size_label)
        size_layout.addWidget(size_slider)
        size_layout.addWidget(size_value_label)
        size_action.setDefaultWidget(size_widget)
        menu.addAction(size_action)

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
            if self._sphere_mode is not SphereDockMode.NONE:
                self._exit_sphere_dock()
            elif is_docked(self._docked_edge):
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
            cursor = event.globalPosition().toPoint()
            entering_sphere = should_sphere_dock(self, cursor_global=cursor)
            if not entering_sphere:
                self._animation.on_drag_end(self._selected_state)
            self._apply_edge_dock(cursor_global=cursor)
            self._scheduler.resume_mood()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _apply_edge_dock(self, *, cursor_global: QPoint | None = None) -> None:
        if should_sphere_dock(self, cursor_global=cursor_global):
            self._enter_sphere_dock()
            return
        snap_edge = detect_snap_edge(self)
        if snap_edge is DockEdge.RIGHT:
            clamp_fully_on_screen(self)
            return
        if snap_edge is not DockEdge.NONE:
            dock_to_edge(self, snap_edge)
            self._docked_edge = snap_edge
            self._speech_bubble.hide_bubble()
            return

        self._docked_edge = DockEdge.NONE
        clamp_fully_on_screen(self)

    def _apply_sphere_overlay_size(self, width: int, height: int) -> None:
        self._label.setFixedSize(width, height)
        self.setFixedSize(width, height)
        self.layout().activate()

    def _clear_sphere_size_constraints(self) -> None:
        max_size = 16777215
        self.setMinimumSize(0, 0)
        self.setMaximumSize(max_size, max_size)
        self._label.setMinimumSize(0, 0)
        self._label.setMaximumSize(max_size, max_size)

    def _enter_sphere_dock(self) -> None:
        self._sphere_anchor_y = self.frameGeometry().center().y()
        self._docked_edge = DockEdge.RIGHT
        self._sphere_allow_peep = False
        self._animation.pause_for_overlay()
        self.setMouseTracking(True)
        self._show_sphere_ball()
        self._speech_bubble.hide_bubble()
        QTimer.singleShot(0, self._finalize_sphere_ball_display)

    def _finalize_sphere_ball_display(self) -> None:
        if self._sphere_mode is not SphereDockMode.BALL:
            return

        self._apply_sphere_overlay_size(self.width(), self.height())
        self._apply_macos_visibility()
        self.show()
        self.update()
        self.repaint()
        QApplication.processEvents()
        QTimer.singleShot(120, self._enable_sphere_peep)

    def _enable_sphere_peep(self) -> None:
        if self._sphere_mode is SphereDockMode.BALL:
            self._sphere_allow_peep = True

    def _show_sphere_ball(self) -> None:
        ball = load_ball_pixmap()
        if ball.isNull():
            return

        self._animation.show_overlay_pixmap(ball)
        self._apply_sphere_overlay_size(ball.width(), ball.height())
        available = screen_geometry(self)
        x, y = ball_position(self._sphere_anchor_y, ball.size(), available)
        self.move(x, y)
        self._sphere_mode = SphereDockMode.BALL
        self.update()
        self.repaint()

    def _show_peep(self) -> None:
        if self._sphere_mode is not SphereDockMode.BALL:
            return

        peep_source = load_peep_pixmap()
        if peep_source.isNull():
            return

        peep = scale_peep_pixmap(peep_source, self._animation.display_max_size())
        self._animation.show_overlay_pixmap(peep)
        self._apply_sphere_overlay_size(peep.width(), peep.height())
        available = screen_geometry(self)
        x, y = peep_position(
            self._sphere_anchor_y,
            peep.size(),
            available,
            screen_right=screen_right_edge(self),
        )
        self.move(x, y)
        self._sphere_mode = SphereDockMode.PEEK

    def _exit_sphere_dock(self) -> None:
        if self._sphere_mode is SphereDockMode.NONE:
            return

        self._sphere_mode = SphereDockMode.NONE
        self._sphere_allow_peep = False
        self._docked_edge = DockEdge.NONE
        self.setMouseTracking(False)
        self._clear_sphere_size_constraints()
        self._animation.resume_after_overlay()
        self._apply_window_size()

        available = screen_geometry(self)
        x = available.right() - self.width() - 4
        y = self._sphere_anchor_y - self.height() // 2
        y = max(available.top() + 4, y)
        y = min(available.bottom() - self.height() - 4, y)
        self.move(x, y)

    def enterEvent(self, event: QEnterEvent) -> None:
        if self._sphere_mode is SphereDockMode.BALL and self._sphere_allow_peep:
            self._show_peep()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._sphere_mode is SphereDockMode.PEEK:
            self._show_sphere_ball()
        super().leaveEvent(event)

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
