from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.macos_window import apply_stay_visible_on_macos, enable_visible_when_inactive
from src.note_storage import export_notebook, load_notebook, save_notebook

PANEL_WIDTH = 300
PANEL_HEIGHT = 360
PANEL_MARGIN = 8
PANEL_PET_GAP = 12


class NotePanel(QWidget):
    note_saved = Signal()

    def __init__(self, pet_window: QWidget) -> None:
        super().__init__(pet_window)
        self._pet_window = pet_window
        self._saved_content = ""

        self._title_label = QLabel("帮我写一下")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._editor = QTextEdit()
        self._editor.setPlaceholderText("Markdown 记事本…")
        self._editor.setAcceptRichText(False)

        self._save_button = QPushButton("保存")
        self._save_button.clicked.connect(self._on_save_clicked)

        self._export_button = QPushButton("导出")
        self._export_button.clicked.connect(self._on_export_clicked)

        self._close_button = QPushButton("关闭")
        self._close_button.clicked.connect(self._on_close_clicked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(self._title_label)
        layout.addWidget(self._editor)

        button_row = QHBoxLayout()
        button_row.addWidget(self._save_button)
        button_row.addWidget(self._export_button)
        button_row.addStretch()
        button_row.addWidget(self._close_button)
        layout.addLayout(button_row)

        self._setup_window()
        self._apply_styles()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        enable_visible_when_inactive(self)
        self.setFixedSize(PANEL_WIDTH, PANEL_HEIGHT)

    def _apply_styles(self) -> None:
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self._title_label.setFont(title_font)

        editor_font = QFont()
        editor_font.setPointSize(10)
        self._editor.setFont(editor_font)

        self.setStyleSheet(
            "QWidget#NotePanelRoot {"
            "  background-color: rgba(255, 255, 255, 245);"
            "  border: 1px solid rgba(0, 0, 0, 35);"
            "  border-radius: 12px;"
            "}"
            "QTextEdit {"
            "  background: white;"
            "  border: 1px solid rgba(0, 0, 0, 30);"
            "  border-radius: 8px;"
            "  padding: 8px;"
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
            "QLabel { color: #2b2b2b; background: transparent; }"
        )
        self.setObjectName("NotePanelRoot")
        self._close_button.setObjectName("CloseButton")

    def _current_content(self) -> str:
        return self._editor.toPlainText()

    def _is_dirty(self) -> bool:
        return self._current_content() != self._saved_content

    def reload(self) -> None:
        self._saved_content = load_notebook()
        self._editor.blockSignals(True)
        self._editor.setPlainText(self._saved_content)
        self._editor.blockSignals(False)

    def show_near_pet(self) -> None:
        self.reload()
        self._position_near_pet()
        self.show()
        apply_stay_visible_on_macos(self)
        self._editor.setFocus()

    def toggle_near_pet(self) -> None:
        if self.isVisible():
            self._try_close()
            return
        self.show_near_pet()

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

    def _on_save_clicked(self) -> None:
        content = self._current_content()
        try:
            save_notebook(content)
        except OSError as error:
            QMessageBox.warning(self, "保存失败", f"无法写入文件：\n{error}")
            return

        self._saved_content = content
        self.note_saved.emit()

    def _on_export_clicked(self) -> None:
        default_name = f"notebook-{datetime.now().strftime('%Y-%m-%d')}.md"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 Markdown",
            default_name,
            "Markdown (*.md)",
        )
        if not path:
            return

        export_path = Path(path if path.endswith(".md") else f"{path}.md")
        try:
            export_notebook(export_path, self._current_content())
        except OSError as error:
            QMessageBox.warning(self, "导出失败", f"无法写入文件：\n{error}")
            return

        QMessageBox.information(self, "导出完成", f"已保存到：\n{export_path}")

    def _try_close(self) -> None:
        if self._is_dirty():
            answer = QMessageBox.question(
                self,
                "未保存的更改",
                "记事本有未保存的内容，要保存吗？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer is QMessageBox.StandardButton.Cancel:
                return
            if answer is QMessageBox.StandardButton.Save:
                self._on_save_clicked()
                if self._is_dirty():
                    return
        self.hide()

    def _on_close_clicked(self) -> None:
        self._try_close()
