"""
ui/employee_dashboard.py
Employee dashboard: assigned tasks + join live meetings.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from database import db_manager
from ui.styles import COLOR


class EmployeeDashboard(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.setWindowTitle("Meeting Analyzer – My Tasks")
        self.resize(980, 640)
        self._build_ui()
        self._load_tasks()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top Bar
        topbar = QFrame()
        topbar.setFixedHeight(60)
        topbar.setStyleSheet(
            f"background-color: {COLOR['bg_card']};"
            f"border-bottom: 1px solid {COLOR['border']};"
        )
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(20, 0, 20, 0)

        app_name = QLabel("🎙️  Meeting Analyzer")
        app_name.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLOR['text_primary']};"
        )
        top_layout.addWidget(app_name)
        top_layout.addStretch()

        user_lbl = QLabel(f"👤  {self.user['full_name']}  |  Employee")
        user_lbl.setStyleSheet(f"color: {COLOR['text_muted']}; font-size: 13px;")
        top_layout.addWidget(user_lbl)

        join_btn = QPushButton("🔴  Join Live Meeting")
        join_btn.setFixedHeight(36)
        join_btn.setStyleSheet(
            f"background: {COLOR['danger']}; color: white; border: none;"
            "border-radius: 6px; font-weight: 700; font-size: 13px; padding: 0 14px;"
        )
        join_btn.clicked.connect(self._join_live_meeting)
        top_layout.addWidget(join_btn)

        refresh_btn = QPushButton("⟳")
        refresh_btn.setObjectName("secondary_btn")
        refresh_btn.setFixedWidth(40)
        refresh_btn.setToolTip("Refresh tasks")
        refresh_btn.clicked.connect(self._load_tasks)
        top_layout.addWidget(refresh_btn)

        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("secondary_btn")
        logout_btn.setFixedWidth(80)
        logout_btn.clicked.connect(self.logout_requested.emit)
        top_layout.addWidget(logout_btn)

        layout.addWidget(topbar)

        # Content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)

        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(12)
        content_layout.addLayout(self.stats_row)

        section = QLabel("My Assigned Tasks")
        section.setObjectName("section_label")
        content_layout.addWidget(section)

        filter_row = QHBoxLayout()
        filter_lbl = QLabel("Filter:")
        filter_lbl.setStyleSheet(f"color: {COLOR['text_muted']}; font-size: 12px;")
        filter_row.addWidget(filter_lbl)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Pending", "In Progress", "Completed"])
        self.status_filter.setFixedWidth(160)
        self.status_filter.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.status_filter)

        self.source_filter = QComboBox()
        self.source_filter.addItems(["All Sources", "📁 Recorded", "🔴 Live"])
        self.source_filter.setFixedWidth(160)
        self.source_filter.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.source_filter)

        filter_row.addStretch()
        content_layout.addLayout(filter_row)

        self.task_table = QTableWidget()
        self.task_table.setColumnCount(7)
        self.task_table.setHorizontalHeaderLabels(
            ["Task Title", "Source", "Meeting", "Deadline", "Status", "Updated", "Update Status"]
        )
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setStyleSheet(
            "QTableWidget { alternate-background-color: #2A2A3E; }"
        )
        content_layout.addWidget(self.task_table)

        layout.addWidget(content)

    def _stat_card(self, icon, value, label, color) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background: {COLOR['bg_card']}; border: 1px solid {COLOR['border']};"
            "border-radius: 10px;"
        )
        card.setFixedHeight(80)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 10, 16, 10)
        cl.setSpacing(2)
        row = QHBoxLayout()
        icon_lbl = QLabel(icon); icon_lbl.setStyleSheet("font-size: 20px;")
        row.addWidget(icon_lbl); row.addStretch()
        cl.addLayout(row)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {color};")
        cl.addWidget(val_lbl)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 11px; color: {COLOR['text_muted']};")
        cl.addWidget(lbl)
        return card

    def _load_tasks(self):
        self._all_tasks = db_manager.get_tasks_for_user(self.user["id"])
        self._update_stats()
        self._apply_filter()

    def _update_stats(self):
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        tasks     = self._all_tasks
        total     = len(tasks)
        pending   = sum(1 for t in tasks if t["status"] == "Pending")
        in_prog   = sum(1 for t in tasks if t["status"] == "In Progress")
        completed = sum(1 for t in tasks if t["status"] == "Completed")
        live_tasks = sum(1 for t in tasks if t.get("source") == "live")

        for icon, val, lbl, clr in [
            ("📋", str(total),      "Total Tasks",   COLOR["accent"]),
            ("⏳", str(pending),    "Pending",        COLOR["warning"]),
            ("🔄", str(in_prog),    "In Progress",    COLOR["in_progress"]),
            ("✅", str(completed),  "Completed",      COLOR["success"]),
            ("🔴", str(live_tasks), "From Live",      COLOR["danger"]),
        ]:
            self.stats_row.addWidget(self._stat_card(icon, val, lbl, clr))

    def _apply_filter(self):
        status_sel = self.status_filter.currentText()
        source_sel = self.source_filter.currentText()

        tasks = self._all_tasks
        if status_sel != "All":
            tasks = [t for t in tasks if t["status"] == status_sel]
        if source_sel == "📁 Recorded":
            tasks = [t for t in tasks if t.get("source") != "live"]
        elif source_sel == "🔴 Live":
            tasks = [t for t in tasks if t.get("source") == "live"]

        self.task_table.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            self.task_table.setItem(row, 0, QTableWidgetItem(t["title"]))
            self.task_table.setItem(row, 1, QTableWidgetItem(
                "🔴 Live" if t.get("source") == "live" else "📁 Recorded"
            ))
            self.task_table.setItem(row, 2, QTableWidgetItem(t.get("meeting_title", "—")))
            self.task_table.setItem(row, 3, QTableWidgetItem(t.get("deadline") or "—"))
            self.task_table.setItem(row, 4, QTableWidgetItem(t["status"]))
            self.task_table.setItem(row, 5, QTableWidgetItem(t.get("updated_at", "")[:10]))

            cell = QWidget()
            cl = QHBoxLayout(cell); cl.setContentsMargins(4, 2, 4, 2)
            combo = QComboBox()
            combo.addItems(["Pending", "In Progress", "Completed"])
            combo.setCurrentText(t["status"])
            combo.setFixedWidth(140)
            combo.currentTextChanged.connect(
                lambda new_status, tid=t["id"]: self._update_status(tid, new_status)
            )
            cl.addWidget(combo)
            self.task_table.setCellWidget(row, 6, cell)
        self.task_table.resizeRowsToContents()

    def _update_status(self, task_id: int, new_status: str):
        db_manager.update_task_status(task_id, new_status)
        self._load_tasks()

    def _join_live_meeting(self):
        from ui.join_meeting_dialog import JoinMeetingDialog
        from networking.client import MeetingClient

        dlg = JoinMeetingDialog(parent=self)
        if not dlg.exec_():
            return

        ip, port = dlg.get_connection()
        client = MeetingClient(user_name=self.user["full_name"], user_role=self.user["role"])

        if not client.connect(ip, port):
            QMessageBox.critical(
                self, "Connection Failed",
                f"Could not connect to {ip}:{port}\n\n"
                "Make sure the host has started a meeting and the details are correct."
            )
            return

        live_id = self._find_or_create_live_record(ip, port)

        from ui.live_meeting_window import LiveMeetingWindow
        self._live_window = LiveMeetingWindow(
            current_user=self.user,
            meeting_title="Live Meeting",
            live_meeting_id=live_id,
            is_host=False,
            client=client,
            parent=None,
        )
        self._live_window.show()
        self._live_window.destroyed.connect(self._load_tasks)

    def _find_or_create_live_record(self, ip: str, port: int) -> int:
        for m in db_manager.get_all_live_meetings():
            if m.get("host_ip") == ip and m.get("port") == port and m.get("status") == "active":
                db_manager.add_participant(m["id"], self.user["id"])
                return m["id"]
        live_id = db_manager.create_live_meeting("Live Meeting", self.user["id"], ip, port)
        db_manager.add_participant(live_id, self.user["id"])
        return live_id