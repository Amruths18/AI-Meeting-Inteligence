"""
main.py
Entry point for the Meeting Analyzer desktop application.

Run with:
    python meeting_analyzer/main.py
or
    cd meeting_analyzer && python main.py
"""

import sys
import os
from pathlib import Path

# Get the directory where this script is located (meeting_analyzer)
script_dir = Path(__file__).parent.absolute()

# Change to the script directory to ensure relative imports work
os.chdir(script_dir)

# Ensure the meeting_analyzer directory is in the Python path
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from database.db_manager import initialize_database
from ui.styles import APP_STYLESHEET
from ui.login_window import LoginWindow
from ui.admin_dashboard import AdminDashboard
from ui.employee_dashboard import EmployeeDashboard


class MeetingAnalyzerApp:
    """
    Application controller.
    Manages window transitions: Login → Admin/Employee Dashboard → Login (on logout).
    """

    def __init__(self, qt_app: QApplication):
        self.qt_app = qt_app
        self.current_window = None

        # Initialise DB (creates tables + seeds default admin)
        initialize_database()

        self._show_login()

    def _show_login(self):
        self._close_current()
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self._on_login)
        self.login_window.show()
        self.current_window = self.login_window

    def _on_login(self, user: dict):
        self.login_window.hide()
        if user["role"] == "admin":
            dashboard = AdminDashboard(user)
            dashboard.logout_requested.connect(self._show_login)
        else:
            dashboard = EmployeeDashboard(user)
            dashboard.logout_requested.connect(self._show_login)

        self._close_current()
        dashboard.show()
        self.current_window = dashboard

    def _close_current(self):
        if self.current_window:
            try:
                self.current_window.close()
            except RuntimeError:
                pass
            self.current_window = None


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Meeting Analyzer")
    app.setOrganizationName("MeetingAI")
    app.setStyleSheet(APP_STYLESHEET)

    controller = MeetingAnalyzerApp(app)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
