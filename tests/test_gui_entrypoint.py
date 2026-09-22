from PySide6.QtWidgets import QApplication

import gui_app


def test_create_application_returns_qapplication(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = gui_app.create_application([])
    assert isinstance(app, QApplication)
    assert QApplication.applicationName() == "安服报告工作台"
