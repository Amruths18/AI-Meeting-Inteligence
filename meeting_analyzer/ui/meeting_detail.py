"""
ui/meeting_detail.py
Full meeting view: transcript, summary, and task management panel.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QWidget, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QLineEdit, QDateEdit, QMessageBox,
    QFormLayout, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QFont

from database import db_manager
from ui.styles import COLOR, badge_style


class TaskEditDialog(QDialog):
    """Small dialog to create or edit a task."""

    def __init__(self, meeting_id: int, task: dict = None, parent=None):
        super().__init__(parent)
        self.meeting_id = meeting_id
        self.task = task
        self.setWindowTitle("Edit Task" if task else "Add Task")
        self.setMinimumWidth(420)
        self._build_ui()
        if task:
            self._populate(task)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Task title")
        form.addRow("Title *", self.title_input)

        self.desc_input = QTextEdit()
        self.desc_input.setFixedHeight(80)
        self.desc_input.setPlaceholderText("Optional description or context")
        form.addRow("Description", self.desc_input)

        # Assigned to dropdown
        self.user_combo = QComboBox()
        self.user_combo.addItem("— Unassigned —", None)
        self._employees = db_manager.get_employees()
        for emp in self._employees:
            self.user_combo.addItem(emp["full_name"], emp["id"])
        form.addRow("Assigned To", self.user_combo)

        # Deadline
        self.deadline_edit = QDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDate(QDate.currentDate().addDays(7))
        self.deadline_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Deadline", self.deadline_edit)

        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Pending", "In Progress", "Completed"])
        form.addRow("Status", self.status_combo)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondary_btn")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        save = QPushButton("Save Task")
        save.clicked.connect(self._save)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _populate(self, task: dict):
        self.title_input.setText(task.get("title", ""))
        self.desc_input.setPlainText(task.get("description", ""))
        if task.get("deadline"):
            self.deadline_edit.setDate(QDate.fromString(task["deadline"], "yyyy-MM-dd"))
        status_idx = self.status_combo.findText(task.get("status", "Pending"))
        if status_idx >= 0:
            self.status_combo.setCurrentIndex(status_idx)
        assigned_id = task.get("assigned_to")
        if assigned_id:
            for i in range(self.user_combo.count()):
                if self.user_combo.itemData(i) == assigned_id:
                    self.user_combo.setCurrentIndex(i)
                    break

    def _save(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Required", "Task title is required.")
            return
        assigned = self.user_combo.currentData()
        deadline = self.deadline_edit.date().toString("yyyy-MM-dd")
        status   = self.status_combo.currentText()
        desc     = self.desc_input.toPlainText().strip()

        if self.task:
            db_manager.update_task(
                self.task["id"], title, desc, assigned, deadline, status
            )
        else:
            db_manager.create_task(self.meeting_id, title, desc, assigned, deadline)

        self.accept()


# ─────────────────────────────────────────────────────────────────────────────

class MeetingDetailWindow(QDialog):
    """Full-screen meeting view with tabs for Transcript, Summary, and Tasks."""

    tasks_updated = pyqtSignal()

    def __init__(self, meeting_id: int, is_admin: bool = False, parent=None):
        super().__init__(parent)
        self.meeting_id = meeting_id
        self.is_admin   = is_admin
        meeting = db_manager.get_meeting(meeting_id)
        self.setWindowTitle(f"Meeting: {meeting.get('title', '')}")
        self.resize(900, 640)
        self._build_ui(meeting)

    def _build_ui(self, meeting: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title_lbl = QLabel(meeting.get("title", "Meeting"))
        title_lbl.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {COLOR['text_primary']};"
        )
        header.addWidget(title_lbl)
        header.addStretch()

        meta = QLabel(f"🗓  {meeting.get('created_at', '')[:10]}")
        meta.setStyleSheet(f"color: {COLOR['text_muted']}; font-size: 12px;")
        header.addWidget(meta)
        layout.addLayout(header)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._build_transcript_tab(meeting), "📄  Transcript")
        tabs.addTab(self._build_summary_tab(meeting),    "📝  Summary")
        tabs.addTab(self._build_tasks_tab(),             "✅  Tasks")
        layout.addWidget(tabs)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondary_btn")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)
        layout.addLayout(row)

    # ── Transcript Tab ────────────────────────────────────────────────────────

    def _build_transcript_tab(self, meeting: dict) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)

        lbl = QLabel("Full Meeting Transcript")
        lbl.setObjectName("section_label")
        layout.addWidget(lbl)

        transcript_box = QTextEdit()
        transcript_box.setReadOnly(True)
        transcript_box.setPlainText(meeting.get("transcript") or "No transcript available.")
        transcript_box.setStyleSheet(
            f"background: {COLOR['bg_mid']}; font-size: 13px; font-family: monospace;"
        )
        layout.addWidget(transcript_box)
        return w

    # ── Summary Tab ───────────────────────────────────────────────────────────

    def _build_summary_tab(self, meeting: dict) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)

        lbl = QLabel("AI-Generated Meeting Summary")
        lbl.setObjectName("section_label")
        layout.addWidget(lbl)

        summary_box = QTextEdit()
        summary_box.setReadOnly(True)
        summary_box.setPlainText(meeting.get("summary") or "No summary available.")
        summary_box.setStyleSheet(
            f"background: {COLOR['bg_mid']}; font-size: 14px; line-height: 1.6;"
        )
        layout.addWidget(summary_box)
        return w

    # ── Tasks Tab ─────────────────────────────────────────────────────────────

    def _build_tasks_tab(self) -> QWidget:
        w = QWidget()
        self._tasks_layout = QVBoxLayout(w)
        self._tasks_layout.setContentsMargins(12, 12, 12, 12)
        self._tasks_layout.setSpacing(10)

        # Toolbar
        toolbar = QHBoxLayout()
        lbl = QLabel("Action Items & Tasks")
        lbl.setObjectName("section_label")
        toolbar.addWidget(lbl)
        toolbar.addStretch()

        if self.is_admin:
            add_btn = QPushButton("+ Add Task")
            add_btn.clicked.connect(self._add_task)
            toolbar.addWidget(add_btn)

        self._tasks_layout.addLayout(toolbar)

        # Table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(6)
        self.task_table.setHorizontalHeaderLabels(
            ["Title", "Assigned To", "Deadline", "Status", "Created", "Actions"]
        )
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setStyleSheet(
            "QTableWidget { alternate-background-color: #2A2A3E; }"
        )
        self._tasks_layout.addWidget(self.task_table)
        self._load_tasks()
        return w

    def _load_tasks(self):
        tasks = db_manager.get_tasks_for_meeting(self.meeting_id)
        self.task_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            self.task_table.setItem(row, 0, QTableWidgetItem(task.get("title", "")))
            self.task_table.setItem(row, 1, QTableWidgetItem(task.get("assigned_to_name") or "Unassigned"))
            self.task_table.setItem(row, 2, QTableWidgetItem(task.get("deadline") or "—"))
            self.task_table.setItem(row, 3, QTableWidgetItem(task.get("status", "Pending")))
            self.task_table.setItem(row, 4, QTableWidgetItem(task.get("created_at", "")[:10]))

            # Action buttons cell
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(4, 2, 4, 2)
            cell_layout.setSpacing(6)

            if self.is_admin:
                edit_btn = QPushButton("Edit")
                edit_btn.setFixedWidth(55)
                edit_btn.setObjectName("secondary_btn")
                edit_btn.clicked.connect(lambda _, t=task: self._edit_task(t))
                cell_layout.addWidget(edit_btn)

                del_btn = QPushButton("Delete")
                del_btn.setFixedWidth(60)
                del_btn.setObjectName("danger_btn")
                del_btn.clicked.connect(lambda _, t=task: self._delete_task(t))
                cell_layout.addWidget(del_btn)

            self.task_table.setCellWidget(row, 5, cell_widget)

        self.task_table.resizeRowsToContents()

    def _add_task(self):
        dlg = TaskEditDialog(self.meeting_id, parent=self)
        if dlg.exec_():
            self._load_tasks()
            self.tasks_updated.emit()

    def _edit_task(self, task: dict):
        dlg = TaskEditDialog(self.meeting_id, task=task, parent=self)
        if dlg.exec_():
            self._load_tasks()
            self.tasks_updated.emit()

    def _delete_task(self, task: dict):
        reply = QMessageBox.question(
            self, "Delete Task",
            f'Delete task "{task["title"]}"?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db_manager.delete_task(task["id"])
            self._load_tasks()
            self.tasks_updated.emit()
