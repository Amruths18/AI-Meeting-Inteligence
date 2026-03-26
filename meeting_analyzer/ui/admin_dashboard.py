"""
ui/admin_dashboard.py
Main window for Admin users: meetings list, task overview, user management.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QFrame, QMessageBox, QSizePolicy, QLineEdit,
    QDialog, QFormLayout, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from database import db_manager
from ui.styles import COLOR
from ui.upload_window import UploadWindow
from ui.meeting_detail import MeetingDetailWindow


# ── Create User Dialog ────────────────────────────────────────────────────────

class CreateUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New User")
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        form = QFormLayout()
        self.name_input     = QLineEdit(); self.name_input.setPlaceholderText("Full name")
        self.username_input = QLineEdit(); self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit(); self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Password")
        self.role_combo     = QComboBox(); self.role_combo.addItems(["employee", "admin"])

        form.addRow("Full Name *",  self.name_input)
        form.addRow("Username *",   self.username_input)
        form.addRow("Password *",   self.password_input)
        form.addRow("Role",         self.role_combo)
        layout.addLayout(form)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet(f"color: {COLOR['danger']}; font-size: 12px;")
        self.error_lbl.hide()
        layout.addWidget(self.error_lbl)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = QPushButton("Cancel"); cancel.setObjectName("secondary_btn")
        cancel.clicked.connect(self.reject); btn_row.addWidget(cancel)
        save = QPushButton("Create User"); save.clicked.connect(self._create)
        btn_row.addWidget(save); layout.addLayout(btn_row)

    def _create(self):
        name = self.name_input.text().strip()
        uname = self.username_input.text().strip()
        pwd = self.password_input.text()
        role = self.role_combo.currentText()
        if not name or not uname or not pwd:
            self.error_lbl.setText("All fields are required.")
            self.error_lbl.show(); return
        ok = db_manager.create_user(uname, pwd, name, role)
        if ok:
            self.accept()
        else:
            self.error_lbl.setText("Username already exists.")
            self.error_lbl.show()


# ── Admin Dashboard ───────────────────────────────────────────────────────────

class AdminDashboard(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.setWindowTitle("Meeting Analyzer – Admin Dashboard")
        self.resize(1100, 680)
        self._build_ui()
        self._refresh_all()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Top Bar ──
        topbar = QFrame()
        topbar.setFixedHeight(70)
        topbar.setStyleSheet(
            f"background-color: {COLOR['bg_card']};"
            f"border-bottom: 1px solid {COLOR['border']};"
        )
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(24, 0, 24, 0)
        top_layout.setSpacing(12)

        app_name = QLabel("🎙️  Meeting Analyzer")
        app_name.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR['text_primary']};"
        )
        top_layout.addWidget(app_name)
        top_layout.addStretch()

        user_lbl = QLabel(f"👤  {self.user['full_name']}  |  Admin")
        user_lbl.setStyleSheet(
            f"color: {COLOR['text_muted']}; font-size: 13px; padding-right: 16px;"
        )
        top_layout.addWidget(user_lbl)

        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("secondary_btn")
        logout_btn.setMinimumHeight(36)
        logout_btn.setMinimumWidth(90)
        logout_btn.clicked.connect(self.logout_requested.emit)
        top_layout.addWidget(logout_btn)

        main_layout.addWidget(topbar)

        # ── Content ──
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(20)

        # Stats row
        content_layout.addLayout(self._build_stats_row())

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._build_meetings_tab(), "📁  Meetings")
        tabs.addTab(self._build_tasks_tab(),    "✅  All Tasks")
        tabs.addTab(self._build_users_tab(),    "👥  Users")
        content_layout.addWidget(tabs)

        main_layout.addWidget(content)

    def _stat_card(self, icon: str, value: str, label: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background: {COLOR['bg_card']}; border: 1px solid {COLOR['border']};"
            "border-radius: 10px;"
        )
        card.setMinimumHeight(100)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 28px;")
        icon_lbl.setMinimumWidth(40)
        top_row.addWidget(icon_lbl)
        top_row.addStretch()
        layout.addLayout(top_row)

        val_lbl = QLabel(value)
        val_lbl.setObjectName("stat_value")
        val_lbl.setStyleSheet(
            f"font-size: 32px; font-weight: 700; color: {COLOR['text_primary']};"
        )
        layout.addWidget(val_lbl)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 12px; color: {COLOR['text_muted']};")
        layout.addWidget(lbl)
        return card

    def _build_stats_row(self) -> QHBoxLayout:
        self._stat_row = QHBoxLayout()
        self._stat_row.setSpacing(16)

        meetings = db_manager.get_all_meetings()
        tasks    = db_manager.get_all_tasks()
        users    = db_manager.get_all_users()

        pending_tasks   = sum(1 for t in tasks if t["status"] == "Pending")
        completed_tasks = sum(1 for t in tasks if t["status"] == "Completed")

        for icon, val, lbl in [
            ("📁", str(len(meetings)),        "Total Meetings"),
            ("✅", str(len(tasks)),            "Total Tasks"),
            ("⏳", str(pending_tasks),         "Pending Tasks"),
            ("🏁", str(completed_tasks),       "Completed"),
            ("👥", str(len(users)),            "Users"),
        ]:
            self._stat_row.addWidget(self._stat_card(icon, val, lbl))

        return self._stat_row

    # ── Meetings Tab ──────────────────────────────────────────────────────────

    def _build_meetings_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        upload_btn = QPushButton("+ Upload Meeting")
        upload_btn.clicked.connect(self._open_upload)
        toolbar.addWidget(upload_btn)
        layout.addLayout(toolbar)

        self.meetings_table = QTableWidget()
        self.meetings_table.setColumnCount(5)
        self.meetings_table.setHorizontalHeaderLabels(
            ["Title", "Uploaded By", "Date", "Status", "Actions"]
        )
        self.meetings_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.meetings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.meetings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.meetings_table.verticalHeader().setVisible(False)
        layout.addWidget(self.meetings_table)
        return w

    def _load_meetings(self):
        meetings = db_manager.get_all_meetings()
        self.meetings_table.setRowCount(len(meetings))
        for row, m in enumerate(meetings):
            self.meetings_table.setItem(row, 0, QTableWidgetItem(m["title"]))
            self.meetings_table.setItem(row, 1, QTableWidgetItem(m.get("uploaded_by_name", "—")))
            self.meetings_table.setItem(row, 2, QTableWidgetItem(m["created_at"][:10]))
            self.meetings_table.setItem(row, 3, QTableWidgetItem(m["status"].capitalize()))

            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(4, 2, 4, 2)
            cell_layout.setSpacing(6)

            view_btn = QPushButton("View")
            view_btn.setFixedWidth(55)
            view_btn.setObjectName("secondary_btn")
            view_btn.clicked.connect(lambda _, mid=m["id"]: self._view_meeting(mid))
            cell_layout.addWidget(view_btn)

            del_btn = QPushButton("Delete")
            del_btn.setFixedWidth(60)
            del_btn.setObjectName("danger_btn")
            del_btn.clicked.connect(lambda _, mid=m["id"]: self._delete_meeting(mid))
            cell_layout.addWidget(del_btn)

            self.meetings_table.setCellWidget(row, 4, cell)

        self.meetings_table.resizeRowsToContents()

    # ── Tasks Tab ─────────────────────────────────────────────────────────────

    def _build_tasks_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.all_tasks_table = QTableWidget()
        self.all_tasks_table.setColumnCount(6)
        self.all_tasks_table.setHorizontalHeaderLabels(
            ["Task", "Meeting", "Assigned To", "Deadline", "Status", "Updated"]
        )
        self.all_tasks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.all_tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.all_tasks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.all_tasks_table.verticalHeader().setVisible(False)
        layout.addWidget(self.all_tasks_table)
        return w

    def _load_tasks(self):
        tasks = db_manager.get_all_tasks()
        self.all_tasks_table.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            self.all_tasks_table.setItem(row, 0, QTableWidgetItem(t["title"]))
            self.all_tasks_table.setItem(row, 1, QTableWidgetItem(t.get("meeting_title", "—")))
            self.all_tasks_table.setItem(row, 2, QTableWidgetItem(t.get("assigned_to_name") or "Unassigned"))
            self.all_tasks_table.setItem(row, 3, QTableWidgetItem(t.get("deadline") or "—"))
            self.all_tasks_table.setItem(row, 4, QTableWidgetItem(t["status"]))
            self.all_tasks_table.setItem(row, 5, QTableWidgetItem(t.get("updated_at", "")[:10]))
        self.all_tasks_table.resizeRowsToContents()

    # ── Users Tab ─────────────────────────────────────────────────────────────

    def _build_users_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        add_btn = QPushButton("+ Add User")
        add_btn.clicked.connect(self._add_user)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["Full Name", "Username", "Role", "Actions"])
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.users_table.verticalHeader().setVisible(False)
        layout.addWidget(self.users_table)
        return w

    def _load_users(self):
        users = db_manager.get_all_users()
        self.users_table.setRowCount(len(users))
        for row, u in enumerate(users):
            self.users_table.setItem(row, 0, QTableWidgetItem(u["full_name"]))
            self.users_table.setItem(row, 1, QTableWidgetItem(u["username"]))
            self.users_table.setItem(row, 2, QTableWidgetItem(u["role"].capitalize()))

            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(4, 2, 4, 2)
            # Prevent deleting own account
            if u["id"] != self.user["id"]:
                del_btn = QPushButton("Remove")
                del_btn.setFixedWidth(70)
                del_btn.setObjectName("danger_btn")
                del_btn.clicked.connect(lambda _, uid=u["id"]: self._delete_user(uid))
                cell_layout.addWidget(del_btn)
            self.users_table.setCellWidget(row, 3, cell)

        self.users_table.resizeRowsToContents()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _refresh_all(self):
        self._load_meetings()
        self._load_tasks()
        self._load_users()

    def _open_upload(self):
        dlg = UploadWindow(self.user, parent=self)
        dlg.processing_done.connect(self._on_processing_done)
        dlg.exec_()

    def _on_processing_done(self, result: dict):
        """After Whisper + NLP complete, auto-save extracted tasks and refresh."""
        meeting_id = result["meeting_id"]
        for task in result.get("tasks", []):
            db_manager.create_task(
                meeting_id,
                task["title"],
                task["description"],
                None,            # assign later from meeting detail
                task.get("deadline")
            )
        self._refresh_all()
        QMessageBox.information(
            self, "Processing Complete",
            f"Meeting processed successfully!\n"
            f"📄 Transcript generated\n"
            f"✅ {len(result.get('tasks', []))} action items extracted\n\n"
            f"Open the meeting to review and assign tasks."
        )

    def _view_meeting(self, meeting_id: int):
        dlg = MeetingDetailWindow(meeting_id, is_admin=True, parent=self)
        dlg.tasks_updated.connect(self._load_tasks)
        dlg.exec_()

    def _delete_meeting(self, meeting_id: int):
        reply = QMessageBox.question(
            self, "Delete Meeting",
            "Delete this meeting and all its tasks? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db_manager.delete_meeting(meeting_id)
            self._refresh_all()

    def _add_user(self):
        dlg = CreateUserDialog(parent=self)
        if dlg.exec_():
            self._load_users()

    def _delete_user(self, user_id: int):
        reply = QMessageBox.question(
            self, "Remove User", "Remove this user account?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db_manager.delete_user(user_id)
            self._load_users()
