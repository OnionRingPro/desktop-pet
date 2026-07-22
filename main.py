import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from src.app_icon import apply_app_icon
from src.pet_window import PetWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    apply_app_icon(app)

    try:
        pet = PetWindow()
        pet.show()
    except Exception:
        QMessageBox.critical(
            None,
            "启动失败",
            f"桌宠启动时发生错误：\n\n{traceback.format_exc()}",
        )
        return 1

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
