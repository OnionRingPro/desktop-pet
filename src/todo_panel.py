from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.macos_window import apply_stay_visible_on_macos, enable_visible_when_inactive
from src.todo_storage import add_todo, delete_todo, load_todos, set_todo_done

PANEL_WIDTH = 260
PANEL_MARGIN = 8
PANEL_PET_GAP = 12


class TodoPanel(QWidget):
    item_added = Signal()

    def __init__(self, pet_window: QWidget) -> None:
        super().__init__(pet_window)
        self._pet_window = pet_window

        self._title_label = QLabel("帮我记一下")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._close_button = QPushButton("关闭")
        self._close_button.setFixedHeight(28)
        self._close_button.clicked.connect(self.hide)

        self._todo_input = QLineEdit()
        self._todo_input.setPlaceholderText("待办")

        self._comment_input = QTextEdit()
        self._comment_input.setPlaceholderText("备注")
        self._comment_input.setFixedHeight(64)

        self._add_button = QPushButton("添加")
        self._add_button.clicked.connect(self._on_add_clicked)

        self._delete_button = QPushButton("删除")
        self._delete_button.clicked.connect(self._on_delete_clicked)
        self._delete_button.setEnabled(False)

        self._list = QListWidget()
        self._list.itemChanged.connect(self._on_item_changed)
        self._list.currentItemChanged.connect(self._on_selection_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.addWidget(self._title_label, stretch=1)
        header_row.addWidget(self._close_button)
        layout.addLayout(header_row)

        layout.addWidget(self._todo_input)
        layout.addWidget(self._comment_input)

        button_row = QHBoxLayout()
        button_row.addWidget(self._delete_button)
        button_row.addStretch()
        button_row.addWidget(self._add_button)
        layout.addLayout(button_row)
        layout.addWidget(self._list)

        self._setup_window()
        self._apply_styles()
        self.reload()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        enable_visible_when_inactive(self)
        self.setFixedWidth(PANEL_WIDTH)
        self._todo_input.returnPressed.connect(self._on_add_clicked)

    def _apply_styles(self) -> None:
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self._title_label.setFont(title_font)

        self.setStyleSheet(
            "QWidget#TodoPanelRoot {"
            "  background-color: rgba(255, 255, 255, 245);"
            "  border: 1px solid rgba(0, 0, 0, 35);"
            "  border-radius: 12px;"
            "}"
            "QLineEdit, QTextEdit, QListWidget {"
            "  background: white;"
            "  border: 1px solid rgba(0, 0, 0, 30);"
            "  border-radius: 8px;"
            "  padding: 6px;"
            "  color: #2b2b2b;"
            "}"
            "QPushButton {"
            "  background: #ffb6c1;"
            "  border: none;"
            "  border-radius: 8px;"
            "  padding: 6px 14px;"
            "  color: #2b2b2b;"
            "}"
            "QPushButton:hover { background: #ffc9d4; }"
            "QPushButton#CloseButton {"
            "  background: transparent;"
            "  border: 1px solid rgba(0, 0, 0, 20);"
            "  padding: 4px 10px;"
            "}"
            "QPushButton#CloseButton:hover { background: rgba(0, 0, 0, 8); }"
            "QPushButton:disabled { color: rgba(43, 43, 43, 120); background: #f0f0f0; }"
            "QLabel { color: #2b2b2b; background: transparent; }"
        )
        self.setObjectName("TodoPanelRoot")
        self._close_button.setObjectName("CloseButton")

    def reload(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()

        for todo in load_todos():
            item = QListWidgetItem(self._format_item_text(todo.text, todo.comment))
            item.setData(Qt.ItemDataRole.UserRole, todo.id)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            item.setCheckState(
                Qt.CheckState.Checked if todo.done else Qt.CheckState.Unchecked
            )
            self._list.addItem(item)

        self._list.blockSignals(False)
        self._on_selection_changed(self._list.currentItem(), None)
        self._adjust_height()

    def show_near_pet(self) -> None:
        self.reload()
        self._position_near_pet()
        self.show()
        apply_stay_visible_on_macos(self)
        self._todo_input.setFocus()

    def toggle_near_pet(self) -> None:
        if self.isVisible():
            self.hide()
            return
        self.show_near_pet()

    def _format_item_text(self, text: str, comment: str) -> str:
        if comment:
            return f"{text}\n备注：{comment}"
        return text

    def _position_near_pet(self) -> None:
        screen = self._pet_window.screen() or QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        pet_rect = self._pet_window.frameGeometry()

        x = pet_rect.left() - self.width() - PANEL_PET_GAP
        y = pet_rect.top()

        if x < available.left() + PANEL_MARGIN:
            x = pet_rect.right() + PANEL_PET_GAP

        y = max(available.top() + PANEL_MARGIN, y)
        y = min(available.bottom() - PANEL_MARGIN - self.height(), y)
        x = max(available.left() + PANEL_MARGIN, x)
        x = min(available.right() - PANEL_MARGIN - self.width(), x)

        self.move(x, y)

    def _adjust_height(self) -> None:
        row_height = 52
        list_height = max(120, min(self._list.count() * row_height, 220))
        self._list.setFixedHeight(list_height)
        self.adjustSize()

    def _on_add_clicked(self) -> None:
        text = self._todo_input.text().strip()
        if not text:
            self._todo_input.setFocus()
            return

        comment = self._comment_input.toPlainText().strip()
        add_todo(text, comment)
        self._todo_input.clear()
        self._comment_input.clear()
        self.reload()
        self.item_added.emit()
        self._todo_input.setFocus()

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        todo_id = item.data(Qt.ItemDataRole.UserRole)
        if not todo_id:
            return
        done = item.checkState() is Qt.CheckState.Checked
        set_todo_done(str(todo_id), done)

    def _on_selection_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        self._delete_button.setEnabled(current is not None)

    def _delete_selected_item(self) -> None:
        current = self._list.currentItem()
        if current is None:
            return
        todo_id = current.data(Qt.ItemDataRole.UserRole)
        if not todo_id:
            return
        delete_todo(str(todo_id))
        self.reload()

    def _on_delete_clicked(self) -> None:
        self._delete_selected_item()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self._list.hasFocus() or self._delete_button.hasFocus():
                if self._list.currentItem() is not None:
                    self._delete_selected_item()
                    event.accept()
                    return
        super().keyPressEvent(event)
