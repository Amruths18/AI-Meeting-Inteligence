"""
ui/join_meeting_dialog.py
Dialog for employees to enter host IP and port to join a live meeting.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
from ui.styles import COLOR


class JoinMeetingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Join Live Meeting")
        self.setFixedSize(400, 310)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(0)

        icon = QLabel("🔗")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 40px; background: transparent; border: none;")
        layout.addWidget(icon)

        layout.addSpacing(8)

        title = QLabel("Join Live Meeting")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR['text_primary']};"
            "background: transparent; border: none;"
        )
        layout.addWidget(title)

        layout.addSpacing(4)

        sub = QLabel("Enter the connection details shared by the host")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"font-size: 12px; color: {COLOR['text_muted']};"
            "background: transparent; border: none;"
        )
        layout.addWidget(sub)

        layout.addSpacing(24)

        ip_lbl = QLabel("Host IP Address")
        ip_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {COLOR['text_muted']};"
            "background: transparent; border: none;"
        )
        layout.addWidget(ip_lbl)
        layout.addSpacing(6)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("e.g.  192.168.1.10")
        self.ip_input.setFixedHeight(44)
        self.ip_input.setStyleSheet(
            f"QLineEdit {{ background: {COLOR['bg_mid']}; border: 1.5px solid {COLOR['border']};"
            f"border-radius: 8px; padding: 0 14px; color: {COLOR['text_primary']}; font-size: 14px; }}"
            f"QLineEdit:focus {{ border-color: {COLOR['accent']}; }}"
        )
        layout.addWidget(self.ip_input)

        layout.addSpacing(12)

        port_lbl = QLabel("Port")
        port_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {COLOR['text_muted']};"
            "background: transparent; border: none;"
        )
        layout.addWidget(port_lbl)
        layout.addSpacing(6)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("e.g.  54321")
        self.port_input.setFixedHeight(44)
        self.port_input.setStyleSheet(
            f"QLineEdit {{ background: {COLOR['bg_mid']}; border: 1.5px solid {COLOR['border']};"
            f"border-radius: 8px; padding: 0 14px; color: {COLOR['text_primary']}; font-size: 14px; }}"
            f"QLineEdit:focus {{ border-color: {COLOR['accent']}; }}"
        )
        self.port_input.returnPressed.connect(self._on_join)
        layout.addWidget(self.port_input)

        layout.addSpacing(20)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondary_btn")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        join = QPushButton("Join Meeting")
        join.setFixedHeight(44)
        join.clicked.connect(self._on_join)
        btn_row.addWidget(join)
        layout.addLayout(btn_row)

    def _on_join(self):
        ip   = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        if not ip:
            QMessageBox.warning(self, "Missing", "Please enter the host IP address.")
            return
        if not port.isdigit():
            QMessageBox.warning(self, "Invalid", "Port must be a number.")
            return
        self._ip   = ip
        self._port = int(port)
        self.accept()

    def get_connection(self) -> tuple:
        return self._ip, self._port