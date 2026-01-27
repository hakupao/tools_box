import sys
from pathlib import Path

# 添加src目录到Python路径
if getattr(sys, "frozen", False):
    bundle_dir = Path(sys._MEIPASS)
else:
    bundle_dir = Path(__file__).parent.parent

if str(bundle_dir) not in sys.path:
    sys.path.insert(0, str(bundle_dir))

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

from src.gui.main_window import MainWindow
from src.gui.qt_common import pick_font


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("工具箱")
    setTheme(Theme.LIGHT)

    font_family = pick_font(
        ["Segoe UI Variable Text", "Segoe UI Variable Display", "Segoe UI", "Microsoft YaHei UI"],
        "Segoe UI",
    )
    app.setFont(QFont(font_family, 10))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
