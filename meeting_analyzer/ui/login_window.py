"""
ui/login_window.py
Login screen — handles Admin and Employee authentication.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QIcon

from database.db_manager import authenticate_user
from ui.styles import COLOR


class LoginWindow(QWidget):
    """Emits `login_successful(user_dict)` on valid credentials."""

    login_successful = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Meeting Analyzer – Login")
        self.setFixedSize(480, 600)
        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(50, 36, 50, 36)
        root.setSpacing(0)

        # Logo / Icon area
        logo_lbl = QLabel("🎙️")
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("font-size: 56px; padding: 0px; margin: 0px;")
        root.addWidget(logo_lbl)

        root.addSpacing(8)

        # App title
        title = QLabel("Meeting Analyzer")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {COLOR['text_primary']};"
            "background: transparent; border: none;"
        )
        root.addWidget(title)

        root.addSpacing(4)

        subtitle = QLabel("AI-Powered Meeting Intelligence")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            f"font-size: 13px; color: {COLOR['text_muted']};"
            "background: transparent; border: none;"
        )
        root.addWidget(subtitle)

        root.addSpacing(28)

        # Card frame
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {COLOR['bg_card']};"
            f"  border: 1px solid {COLOR['border']};"
            f"  border-radius: 14px;"
            f"}}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(0)

        # Sign-in heading
        sign_in = QLabel("Sign In")
        sign_in.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLOR['text_primary']};"
            "background: transparent; border: none;"
        )
        card_layout.addWidget(sign_in)

        card_layout.addSpacing(20)

        # Username label
        card_layout.addWidget(self._field_label("Username"))
        card_layout.addSpacing(6)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(46)
        self.username_input.setStyleSheet(
            f"QLineEdit {{"
            f"  background-color: {COLOR['bg_mid']};"
            f"  border: 1.5px solid {COLOR['border']};"
            f"  border-radius: 8px;"
            f"  padding: 0px 14px;"
            f"  color: {COLOR['text_primary']};"
            f"  font-size: 14px;"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border: 1.5px solid {COLOR['accent']};"
            f"  background-color: {COLOR['bg_mid']};"
            f"}}"
        )
        self.username_input.returnPressed.connect(self._on_login)
        card_layout.addWidget(self.username_input)

        card_layout.addSpacing(16)

        # Password label
        card_layout.addWidget(self._field_label("Password"))
        card_layout.addSpacing(6)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setFixedHeight(46)
        self.password_input.setStyleSheet(
            f"QLineEdit {{"
            f"  background-color: {COLOR['bg_mid']};"
            f"  border: 1.5px solid {COLOR['border']};"
            f"  border-radius: 8px;"
            f"  padding: 0px 14px;"
            f"  color: {COLOR['text_primary']};"
            f"  font-size: 14px;"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border: 1.5px solid {COLOR['accent']};"
            f"  background-color: {COLOR['bg_mid']};"
            f"}}"
        )
        self.password_input.returnPressed.connect(self._on_login)
        card_layout.addWidget(self.password_input)

        card_layout.addSpacing(10)

        # Error label (hidden by default)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(
            f"color: {COLOR['danger']}; font-size: 12px;"
            "background: transparent; border: none;"
        )
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setFixedHeight(20)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        card_layout.addSpacing(16)

        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setFixedHeight(48)
        self.login_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {COLOR['accent']};"
            f"  color: white;"
            f"  border: none;"
            f"  border-radius: 8px;"
            f"  font-size: 15px;"
            f"  font-weight: 700;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {COLOR['accent_hover']};"
            f"}}"
            f"QPushButton:pressed {{"
            f"  background-color: #5E50CC;"
            f"}}"
            f"QPushButton:disabled {{"
            f"  background-color: {COLOR['bg_card']};"
            f"  color: {COLOR['text_muted']};"
            f"}}"
        )
        self.login_btn.clicked.connect(self._on_login)
        card_layout.addWidget(self.login_btn)

        root.addWidget(card)
        root.addStretch()

        # Footer hint
        hint = QLabel("Default admin: admin / admin")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            f"color: {COLOR['text_muted']}; font-size: 12px;"
            "background: transparent; border: none;"
        )
        root.addWidget(hint)

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {COLOR['text_muted']}; font-size: 13px; font-weight: 600;"
            "background: transparent; border: none;"
        )
        return lbl

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _on_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self._show_error("Please enter both username and password.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in...")

        user = authenticate_user(username, password)

        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In")

        if user:
            self.error_label.hide()
            self.password_input.clear()
            self.login_successful.emit(user)
        else:
            self._show_error("Invalid username or password.")

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()
        self.password_input.clear()
        self.password_input.setFocus()