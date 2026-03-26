"""
ui/live_meeting_window.py
Full live meeting room — used for both HOST (Admin) and PARTICIPANT (Employee).
"""

import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QSplitter, QListWidget,
    QListWidgetItem, QDialog, QFormLayout, QLineEdit, QComboBox,
    QDateEdit, QMessageBox, QScrollArea, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QDate, QTimer
from PyQt5.QtGui import QTextCursor

from ui.styles import COLOR
from database import db_manager


# ── Background worker for mic transcription ───────────────────────────────────

class LiveTranscribeWorker(QObject):
    new_text = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, model_name="base"):
        super().__init__()
        self.model_name   = model_name
        self._transcriber = None

    def start_transcribing(self):
        from ai.live_transcriber import LiveTranscriber
        try:
            self._transcriber = LiveTranscriber(
                on_transcript=lambda t: self.new_text.emit(t),
                model_name=self.model_name,
            )
            self._transcriber.start()
        except Exception as e:
            self.error.emit(str(e))

    def stop_transcribing(self):
        if self._transcriber:
            self._transcriber.stop()


# ── Signal bridge for client callbacks → Qt main thread ──────────────────────

class ClientSignals(QObject):
    transcript   = pyqtSignal(str)
    task_assign  = pyqtSignal(dict)
    task_bcast   = pyqtSignal(dict)
    participants = pyqtSignal(list)
    meeting_end  = pyqtSignal(str)
    welcome      = pyqtSignal(dict)
    error        = pyqtSignal(str)


# ── Quick Task Assign Dialog ──────────────────────────────────────────────────

class QuickTaskDialog(QDialog):
    def __init__(self, live_meeting_id: int, parent=None):
        super().__init__(parent)
        self.live_meeting_id = live_meeting_id
        self.setWindowTitle("Assign Task")
        self.setMinimumWidth(400)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel("Assign Task to Employee")
        header.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLOR['text_primary']};"
            "background: transparent; border: none;"
        )
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Task title")
        self.title_input.setFixedHeight(42)
        form.addRow("Title *", self.title_input)

        self.desc_input = QTextEdit()
        self.desc_input.setFixedHeight(70)
        self.desc_input.setPlaceholderText("Description / context")
        form.addRow("Description", self.desc_input)

        self.user_combo = QComboBox()
        self.user_combo.addItem("— Unassigned —", None)
        self._employees = db_manager.get_employees()
        for emp in self._employees:
            self.user_combo.addItem(emp["full_name"], emp["id"])
        form.addRow("Assign To", self.user_combo)

        self.deadline_edit = QDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDate(QDate.currentDate().addDays(3))
        self.deadline_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Deadline", self.deadline_edit)

        layout.addLayout(form)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet(
            f"color: {COLOR['danger']}; font-size: 12px;"
            "background: transparent; border: none;"
        )
        self.error_lbl.hide()
        layout.addWidget(self.error_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondary_btn")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        save = QPushButton("Assign Task")
        save.clicked.connect(self._save)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _save(self):
        title = self.title_input.text().strip()
        if not title:
            self.error_lbl.setText("Title is required.")
            self.error_lbl.show()
            return

        assigned = self.user_combo.currentData()
        deadline = self.deadline_edit.date().toString("yyyy-MM-dd")
        desc     = self.desc_input.toPlainText().strip()

        task_id = db_manager.create_task(
            meeting_id=None,
            title=title,
            description=desc,
            assigned_to=assigned,
            deadline=deadline,
            live_meeting_id=self.live_meeting_id,
        )

        assigned_name = "Unassigned"
        if assigned:
            for emp in self._employees:
                if emp["id"] == assigned:
                    assigned_name = emp["full_name"]
                    break

        self._task_result = {
            "id":               task_id,
            "title":            title,
            "description":      desc,
            "assigned_to":      assigned,
            "assigned_to_name": assigned_name,
            "deadline":         deadline,
            "status":           "Pending",
        }
        self.accept()

    def get_task(self) -> dict:
        return self._task_result


# ── Live Meeting Window ────────────────────────────────────────────────────────

class LiveMeetingWindow(QMainWindow):
    def __init__(
        self,
        current_user: dict,
        meeting_title: str,
        live_meeting_id: int,
        is_host: bool = False,
        server=None,
        client=None,
        parent=None,
    ):
        super().__init__(parent)
        self.current_user    = current_user
        self.meeting_title   = meeting_title
        self.live_meeting_id = live_meeting_id
        self.is_host         = is_host
        self.server          = server
        self.client          = client

        self._full_transcript = ""
        self._start_time      = datetime.datetime.now()
        self._mic_active      = False
        self._worker          = None
        self._worker_thread   = None

        self.setWindowTitle(f"🔴 LIVE — {meeting_title}")
        self.resize(1180, 700)
        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_elapsed)
        self._timer.start(1000)

        if not is_host and client:
            self._wire_client_signals()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {COLOR['border']}; width: 2px; }}"
        )
        splitter.addWidget(self._build_transcript_panel())
        splitter.addWidget(self._build_sidebar())
        splitter.setSizes([780, 360])
        root.addWidget(splitter)

        root.addWidget(self._build_bottombar())

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(58)
        bar.setStyleSheet(
            f"background: {COLOR['bg_card']}; border-bottom: 1px solid {COLOR['border']};"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        self.rec_dot = QLabel("●")
        self.rec_dot.setStyleSheet(f"color: {COLOR['danger']}; font-size: 18px;")
        layout.addWidget(self.rec_dot)
        layout.addSpacing(8)

        title_lbl = QLabel(self.meeting_title)
        title_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLOR['text_primary']};"
            "background: transparent; border: none;"
        )
        layout.addWidget(title_lbl)
        layout.addSpacing(12)

        badge_color = COLOR['danger'] if self.is_host else COLOR['accent2']
        badge_text  = "HOST" if self.is_host else "PARTICIPANT"
        role_badge  = QLabel(badge_text)
        role_badge.setStyleSheet(
            f"background: {badge_color}; color: white; font-size: 11px; font-weight: 700;"
            "border-radius: 4px; padding: 2px 8px;"
        )
        layout.addWidget(role_badge)
        layout.addStretch()

        self.elapsed_lbl = QLabel("00:00:00")
        self.elapsed_lbl.setStyleSheet(
            f"color: {COLOR['text_muted']}; font-size: 13px; font-family: monospace;"
            "background: transparent; border: none;"
        )
        layout.addWidget(self.elapsed_lbl)
        layout.addSpacing(20)

        self.participant_lbl = QLabel("👥 0 participants")
        self.participant_lbl.setStyleSheet(
            f"color: {COLOR['text_muted']}; font-size: 13px;"
            "background: transparent; border: none;"
        )
        layout.addWidget(self.participant_lbl)
        return bar

    def _build_transcript_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 12, 8)
        layout.setSpacing(10)

        hrow = QHBoxLayout()
        lbl = QLabel("📄  Live Transcript")
        lbl.setObjectName("section_label")
        hrow.addWidget(lbl)
        hrow.addStretch()
        self.status_lbl = QLabel("● Waiting...")
        self.status_lbl.setStyleSheet(
            f"color: {COLOR['text_muted']}; font-size: 12px;"
            "background: transparent; border: none;"
        )
        hrow.addWidget(self.status_lbl)
        layout.addLayout(hrow)

        self.transcript_box = QTextEdit()
        self.transcript_box.setReadOnly(True)
        self.transcript_box.setStyleSheet(
            f"background: {COLOR['bg_mid']}; border: 1px solid {COLOR['border']};"
            "border-radius: 8px; font-size: 13px; padding: 12px;"
        )
        self.transcript_box.setPlaceholderText(
            "Live transcript will appear here as the meeting progresses..."
        )
        layout.addWidget(self.transcript_box)
        return panel

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setStyleSheet(
            f"background: {COLOR['bg_card']}; border-left: 1px solid {COLOR['border']};"
        )
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(14)

        # Host shows IP:PORT to share
        if self.is_host and self.server:
            info_frame = QFrame()
            info_frame.setStyleSheet(
                f"QFrame {{ background: {COLOR['bg_mid']}; border: 1px solid {COLOR['accent']};"
                "border-radius: 8px; }}"
            )
            info_layout = QVBoxLayout(info_frame)
            info_layout.setContentsMargins(12, 10, 12, 10)
            info_layout.setSpacing(4)

            share_lbl = QLabel("🔗  Share to invite participants")
            share_lbl.setStyleSheet(
                f"font-size: 11px; font-weight: 600; color: {COLOR['accent']};"
                "background: transparent; border: none;"
            )
            info_layout.addWidget(share_lbl)

            conn_str = self.server.connection_string
            conn_lbl = QLabel(conn_str)
            conn_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            conn_lbl.setStyleSheet(
                f"font-size: 18px; font-weight: 700; color: {COLOR['text_primary']};"
                "font-family: monospace; background: transparent; border: none;"
            )
            info_layout.addWidget(conn_lbl)

            copy_btn = QPushButton("Copy")
            copy_btn.setObjectName("secondary_btn")
            copy_btn.setFixedHeight(30)
            copy_btn.clicked.connect(
                lambda: QApplication.clipboard().setText(conn_str)
            )
            info_layout.addWidget(copy_btn)
            layout.addWidget(info_frame)

        # Participants list
        p_lbl = QLabel("👥  Participants")
        p_lbl.setObjectName("section_label")
        layout.addWidget(p_lbl)

        self.participants_list = QListWidget()
        self.participants_list.setFixedHeight(120)
        self.participants_list.setStyleSheet(
            f"background: {COLOR['bg_mid']}; border: 1px solid {COLOR['border']};"
            "border-radius: 6px; font-size: 12px;"
        )
        host_item = QListWidgetItem(
            f"👑  {self.current_user['full_name']} (You – Host)"
            if self.is_host else "🎙️  Host"
        )
        self.participants_list.addItem(host_item)
        layout.addWidget(self.participants_list)

        # Tasks section
        task_header = QHBoxLayout()
        t_lbl = QLabel("✅  Tasks")
        t_lbl.setObjectName("section_label")
        task_header.addWidget(t_lbl)
        task_header.addStretch()

        if self.is_host:
            self.assign_btn = QPushButton("+ Assign Task")
            self.assign_btn.setFixedHeight(30)
            self.assign_btn.clicked.connect(self._assign_task)
            task_header.addWidget(self.assign_btn)

        layout.addLayout(task_header)

        self.tasks_area = QScrollArea()
        self.tasks_area.setWidgetResizable(True)
        self.tasks_area.setStyleSheet("background: transparent; border: none;")
        self._tasks_container = QWidget()
        self._tasks_layout    = QVBoxLayout(self._tasks_container)
        self._tasks_layout.setContentsMargins(0, 0, 0, 0)
        self._tasks_layout.setSpacing(6)
        self._tasks_layout.addStretch()
        self.tasks_area.setWidget(self._tasks_container)
        layout.addWidget(self.tasks_area)
        return sidebar

    def _build_bottombar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setStyleSheet(
            f"background: {COLOR['bg_card']}; border-top: 1px solid {COLOR['border']};"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        if self.is_host:
            self.mic_btn = QPushButton("🎙️  Start Mic Transcription")
            self.mic_btn.setFixedHeight(40)
            self.mic_btn.setFixedWidth(220)
            self.mic_btn.clicked.connect(self._toggle_mic)
            layout.addWidget(self.mic_btn)

        layout.addStretch()

        if self.is_host:
            end_btn = QPushButton("End Meeting")
            end_btn.setObjectName("danger_btn")
            end_btn.setFixedHeight(40)
            end_btn.setFixedWidth(130)
            end_btn.clicked.connect(self._end_meeting)
            layout.addWidget(end_btn)
        else:
            leave_btn = QPushButton("Leave Meeting")
            leave_btn.setObjectName("secondary_btn")
            leave_btn.setFixedHeight(40)
            leave_btn.setFixedWidth(140)
            leave_btn.clicked.connect(self._leave_meeting)
            layout.addWidget(leave_btn)

        return bar

    # ── Host: Mic ─────────────────────────────────────────────────────────────

    def _toggle_mic(self):
        if not self._mic_active:
            self._start_mic()
        else:
            self._stop_mic()

    def _start_mic(self):
        self._worker        = LiveTranscribeWorker(model_name="base")
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker.new_text.connect(self._on_host_transcript)
        self._worker.error.connect(self._on_mic_error)
        self._worker_thread.started.connect(self._worker.start_transcribing)
        self._worker_thread.start()
        self._mic_active = True
        self.mic_btn.setText("⏹  Stop Mic")
        self.mic_btn.setStyleSheet(
            f"background: {COLOR['danger']}; color: white; border: none;"
            "border-radius: 6px; font-weight: 600; font-size: 13px;"
        )
        self._set_status("🎙️  Recording & transcribing...", COLOR['danger'])

    def _stop_mic(self):
        if self._worker:
            self._worker.stop_transcribing()
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait(3000)
        self._mic_active = False
        self.mic_btn.setText("🎙️  Start Mic Transcription")
        self.mic_btn.setStyleSheet("")
        self._set_status("● Mic stopped", COLOR['text_muted'])

    def _on_host_transcript(self, text: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}]  {text}"
        self._full_transcript += formatted + "\n"
        self.transcript_box.append(formatted)
        self._scroll_transcript()
        db_manager.append_live_transcript(self.live_meeting_id, formatted)
        if self.server:
            self.server.broadcast_transcript(formatted)

    def _on_mic_error(self, err: str):
        self._stop_mic()
        QMessageBox.critical(self, "Microphone Error",
                             f"Could not start microphone:\n\n{err}")

    # ── Participant: Client signals ───────────────────────────────────────────

    def _wire_client_signals(self):
        self._signals = ClientSignals()
        self._signals.transcript.connect(self._on_participant_transcript)
        self._signals.task_assign.connect(self._on_task_received)
        self._signals.task_bcast.connect(self._refresh_task_cards)
        self._signals.participants.connect(self._on_participants_updated)
        self._signals.meeting_end.connect(self._on_meeting_ended)
        self._signals.welcome.connect(self._on_welcome)
        self._signals.error.connect(self._on_connection_error)

        self.client.on_transcript     = lambda t: self._signals.transcript.emit(t)
        self.client.on_task_assign    = lambda t: self._signals.task_assign.emit(t)
        self.client.on_task_broadcast = lambda d: self._signals.task_bcast.emit(d)
        self.client.on_participants   = lambda p: self._signals.participants.emit(p)
        self.client.on_meeting_end    = lambda m: self._signals.meeting_end.emit(m)
        self.client.on_welcome        = lambda d: self._signals.welcome.emit(d)
        self.client.on_error          = lambda e: self._signals.error.emit(e)

    def _on_welcome(self, data: dict):
        history = data.get("transcript", "")
        if history.strip():
            self._full_transcript = history
            self.transcript_box.setPlainText(history)
            self._scroll_transcript()
        for task in data.get("tasks", []):
            self._add_task_card(task)
        self._set_status("● Connected to meeting", COLOR['success'])

    def _on_participant_transcript(self, text: str):
        self._full_transcript += text + "\n"
        self.transcript_box.append(text)
        self._scroll_transcript()

    def _on_task_received(self, task: dict):
        self._add_task_card(task)
        QMessageBox.information(
            self, "New Task Assigned",
            f"📋 Assigned to: {task.get('assigned_to_name', 'You')}\n\n"
            f"{task.get('title', '')}"
        )

    def _on_participants_updated(self, participants: list):
        self.participants_list.clear()
        self.participants_list.addItem(QListWidgetItem("👑  Host"))
        for p in participants:
            self.participants_list.addItem(
                QListWidgetItem(f"👤  {p['name']}  ({p['role']})")
            )
        count = len(participants)
        self.participant_lbl.setText(
            f"👥 {count} participant{'s' if count != 1 else ''}"
        )

    def _on_meeting_ended(self, message: str):
        self._set_status("● Meeting ended", COLOR['text_muted'])
        QMessageBox.information(self, "Meeting Ended", message)
        self.close()

    def _on_connection_error(self, error: str):
        self._set_status(f"● Error: {error}", COLOR['danger'])
        QMessageBox.warning(self, "Connection Error", error)

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def _assign_task(self):
        dlg = QuickTaskDialog(self.live_meeting_id, parent=self)
        if dlg.exec_():
            task = dlg.get_task()
            self._add_task_card(task)
            if self.server:
                self.server.broadcast_task(task)

    def _add_task_card(self, task: dict):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {COLOR['bg_dark']}; border: 1px solid {COLOR['border']};"
            "border-radius: 8px; }}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(4)

        title_lbl = QLabel(task.get("title", ""))
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {COLOR['text_primary']};"
            "background: transparent; border: none;"
        )
        card_layout.addWidget(title_lbl)

        meta = QLabel(
            f"👤 {task.get('assigned_to_name', 'Unassigned')}  "
            f"📅 {task.get('deadline', '—')}"
        )
        meta.setStyleSheet(
            f"font-size: 11px; color: {COLOR['text_muted']};"
            "background: transparent; border: none;"
        )
        card_layout.addWidget(meta)

        status_colors = {
            "Pending":     COLOR["warning"],
            "In Progress": COLOR["in_progress"],
            "Completed":   COLOR["success"],
        }
        status = task.get("status", "Pending")
        status_lbl = QLabel(f"⬤ {status}")
        status_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600;"
            f"color: {status_colors.get(status, COLOR['text_muted'])};"
            "background: transparent; border: none;"
        )
        card_layout.addWidget(status_lbl)

        count = self._tasks_layout.count()
        self._tasks_layout.insertWidget(count - 1, card)

    def _refresh_task_cards(self, data=None):
        while self._tasks_layout.count() > 1:
            item = self._tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for task in db_manager.get_tasks_for_live_meeting(self.live_meeting_id):
            self._add_task_card(task)

    # ── End / Leave ───────────────────────────────────────────────────────────

    def _end_meeting(self):
        reply = QMessageBox.question(
            self, "End Meeting",
            "End meeting for all participants?\nTranscript and summary will be saved.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self._stop_mic()

        summary = ""
        if self._full_transcript.strip():
            from ai.nlp_processor import generate_summary
            summary = generate_summary(self._full_transcript)

        db_manager.end_live_meeting(self.live_meeting_id, self._full_transcript, summary)

        if self.server:
            self.server.stop()

        self._timer.stop()
        self.close()

    def _leave_meeting(self):
        if self.client:
            self.client.disconnect()
        db_manager.remove_participant(self.live_meeting_id, self.current_user["id"])
        self._timer.stop()
        self.close()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = None):
        self.status_lbl.setText(text)
        if color:
            self.status_lbl.setStyleSheet(
                f"color: {color}; font-size: 12px;"
                "background: transparent; border: none;"
            )

    def _scroll_transcript(self):
        cursor = self.transcript_box.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.transcript_box.setTextCursor(cursor)

    def _update_elapsed(self):
        delta = datetime.datetime.now() - self._start_time
        total = int(delta.total_seconds())
        h, m, s = total // 3600, (total % 3600) // 60, total % 60
        self.elapsed_lbl.setText(f"{h:02d}:{m:02d}:{s:02d}")
        current = self.rec_dot.styleSheet()
        if "danger" in current:
            self.rec_dot.setStyleSheet("color: transparent; font-size: 18px;")
        else:
            self.rec_dot.setStyleSheet(f"color: {COLOR['danger']}; font-size: 18px;")

    def closeEvent(self, event):
        if self.is_host and self._mic_active:
            self._stop_mic()
        self._timer.stop()
        super().closeEvent(event)