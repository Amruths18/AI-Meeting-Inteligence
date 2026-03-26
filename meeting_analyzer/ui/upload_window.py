"""
ui/upload_window.py
Dialog for uploading a meeting audio file and triggering offline AI processing.
Runs Whisper + NLP in a background thread so the UI stays responsive.
"""

import os
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QProgressBar, QTextEdit,
    QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

from ai.transcriber import transcribe_audio, format_transcript_with_timestamps, is_supported_format
from ai.nlp_processor import process_transcript
from database import db_manager
from ui.styles import COLOR

AUDIO_STORAGE = Path(__file__).parent.parent / "data" / "audio_files"


# ── Background Worker ─────────────────────────────────────────────────────────

class ProcessingWorker(QObject):
    """Runs Whisper + NLP off the main thread."""

    progress   = pyqtSignal(str)          # status message updates
    finished   = pyqtSignal(dict)         # result payload
    error      = pyqtSignal(str)          # error message

    def __init__(self, audio_path: str, meeting_id: int):
        super().__init__()
        self.audio_path  = audio_path
        self.meeting_id  = meeting_id

    def run(self):
        try:
            # Step 1: Transcription
            self.progress.emit("🎙️  Transcribing audio with Whisper AI...")
            result = transcribe_audio(
                self.audio_path,
                progress_callback=lambda msg: self.progress.emit(f"🎙️  {msg}")
            )
            transcript_plain = result["text"]
            transcript_timed = format_transcript_with_timestamps(result["segments"])
            display_transcript = transcript_timed if transcript_timed else transcript_plain

            # Step 2: NLP
            self.progress.emit("🧠  Analysing transcript with NLP...")
            nlp_result = process_transcript(transcript_plain)

            # Step 3: Persist
            self.progress.emit("💾  Saving results to database...")
            db_manager.update_meeting_results(
                self.meeting_id,
                display_transcript,
                nlp_result["summary"]
            )

            self.finished.emit({
                "meeting_id":  self.meeting_id,
                "transcript":  display_transcript,
                "summary":     nlp_result["summary"],
                "tasks":       nlp_result["tasks"],
                "language":    result.get("language", "en")
            })

        except Exception as exc:
            db_manager.update_meeting_status(self.meeting_id, "failed")
            self.error.emit(str(exc))


# ── Upload Dialog ─────────────────────────────────────────────────────────────

class UploadWindow(QDialog):
    """
    Modal dialog.
    Emits `processing_done(result_dict)` when AI processing completes.
    """

    processing_done = pyqtSignal(dict)

    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.selected_file = ""
        self.setWindowTitle("Upload Meeting Audio")
        self.setMinimumWidth(540)
        self.setModal(True)
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # Header
        title = QLabel("Upload Meeting Recording")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR['text_primary']};"
        )
        layout.addWidget(title)

        hint = QLabel("Supported formats: MP3, WAV, M4A, MP4, OGG, FLAC")
        hint.setStyleSheet(f"color: {COLOR['text_muted']}; font-size: 12px;")
        layout.addWidget(hint)

        # Meeting title
        layout.addWidget(self._label("Meeting Title"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Sprint Planning – Week 12")
        layout.addWidget(self.title_input)

        # File chooser
        layout.addWidget(self._label("Audio File"))
        file_row = QHBoxLayout()
        self.file_label = QLineEdit()
        self.file_label.setPlaceholderText("No file selected")
        self.file_label.setReadOnly(True)
        file_row.addWidget(self.file_label)
        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("secondary_btn")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # Status / Progress
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLOR['accent2']}; font-size: 12px;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)   # indeterminate
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Log area (shows live status)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(100)
        self.log_area.setStyleSheet(
            f"background: {COLOR['bg_mid']}; font-size: 12px; font-family: monospace;"
        )
        self.log_area.hide()
        layout.addWidget(self.log_area)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary_btn")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.upload_btn = QPushButton("Process Meeting")
        self.upload_btn.setFixedWidth(150)
        self.upload_btn.clicked.connect(self._start_processing)
        btn_row.addWidget(self.upload_btn)
        layout.addLayout(btn_row)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {COLOR['text_muted']};"
        )
        return lbl

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "",
            "Audio Files (*.mp3 *.wav *.m4a *.mp4 *.ogg *.flac *.webm)"
        )
        if path:
            self.selected_file = path
            self.file_label.setText(os.path.basename(path))

    def _start_processing(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Title", "Please enter a meeting title.")
            return
        if not self.selected_file:
            QMessageBox.warning(self, "No File", "Please select an audio file.")
            return
        if not is_supported_format(self.selected_file):
            QMessageBox.warning(self, "Unsupported Format",
                                "Please choose an MP3, WAV, M4A, or similar audio file.")
            return

        # Copy audio to app storage
        AUDIO_STORAGE.mkdir(parents=True, exist_ok=True)
        dest = AUDIO_STORAGE / Path(self.selected_file).name
        shutil.copy2(self.selected_file, dest)

        # Create DB record
        meeting_id = db_manager.create_meeting(
            title, str(dest), self.current_user["id"]
        )
        db_manager.update_meeting_status(meeting_id, "processing")

        # Lock UI
        self.upload_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.title_input.setEnabled(False)
        self.progress_bar.show()
        self.log_area.show()
        self._log("Starting offline AI processing…")

        # Start background thread
        self._thread = QThread()
        self._worker = ProcessingWorker(str(dest), meeting_id)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._log)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)

        self._thread.start()

    def _log(self, msg: str):
        self.log_area.append(msg)
        self.status_label.setText(msg)

    def _on_finished(self, result: dict):
        self.progress_bar.hide()
        self._log("✅  Processing complete!")
        self.processing_done.emit(result)
        self.accept()

    def _on_error(self, error_msg: str):
        self.progress_bar.hide()
        self.upload_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.title_input.setEnabled(True)
        self._log(f"❌  Error: {error_msg}")
        QMessageBox.critical(self, "Processing Failed",
                             f"An error occurred during processing:\n\n{error_msg}")
