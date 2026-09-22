import sys

from PySide6.QtWidgets import QApplication

from services.logging_setup import configure_logging
from ui.main_window import MainWindow


def create_application(argv=None):
    app = QApplication.instance() or QApplication(
        argv if argv is not None else sys.argv
    )
    app.setApplicationName("安服报告工作台")
    app.setOrganizationName("BaijiuDrink")
    return app


def main():
    configure_logging()
    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
