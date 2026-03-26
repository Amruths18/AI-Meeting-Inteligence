"""
ui/styles.py
Centralized color palette, fonts, and stylesheet for the entire application.
"""

from PyQt5.QtGui import QFont, QColor


# ── Color Palette ─────────────────────────────────────────────────────────────
COLOR = {
    "bg_dark":      "#1E1E2E",
    "bg_mid":       "#2A2A3E",
    "bg_card":      "#313147",
    "accent":       "#7C6AF7",
    "accent_hover": "#9B8BFF",
    "accent2":      "#4ECDC4",
    "danger":       "#FF6B6B",
    "warning":      "#FFD93D",
    "success":      "#6BCB77",
    "text_primary": "#EAEAF5",
    "text_muted":   "#8888AA",
    "border":       "#3D3D5C",
    "pending":      "#FFD93D",
    "in_progress":  "#4ECDC4",
    "completed":    "#6BCB77",
}

# ── Main Stylesheet ───────────────────────────────────────────────────────────
APP_STYLESHEET = f"""
/* ── Global ── */
QWidget {{
    background-color: {COLOR['bg_dark']};
    color: {COLOR['text_primary']};
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {COLOR['accent']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {COLOR['accent_hover']};
}}
QPushButton:pressed {{
    background-color: #5E50CC;
}}
QPushButton:disabled {{
    background-color: {COLOR['bg_card']};
    color: {COLOR['text_muted']};
}}
QPushButton#danger_btn {{
    background-color: {COLOR['danger']};
}}
QPushButton#danger_btn:hover {{
    background-color: #FF8E8E;
}}
QPushButton#secondary_btn {{
    background-color: {COLOR['bg_card']};
    color: {COLOR['text_primary']};
    border: 1px solid {COLOR['border']};
}}
QPushButton#secondary_btn:hover {{
    background-color: {COLOR['bg_mid']};
}}

/* ── Line Edits ── */
QLineEdit {{
    background-color: {COLOR['bg_mid']};
    border: 1.5px solid {COLOR['border']};
    border-radius: 8px;
    padding: 0px 14px;
    color: {COLOR['text_primary']};
    font-size: 14px;
    min-height: 42px;
    selection-background-color: {COLOR['accent']};
}}
QLineEdit:focus {{
    border: 1.5px solid {COLOR['accent']};
    background-color: {COLOR['bg_mid']};
}}
QLineEdit::placeholder {{
    color: {COLOR['text_muted']};
}}
QTextEdit {{
    background-color: {COLOR['bg_card']};
    border: 1px solid {COLOR['border']};
    border-radius: 6px;
    padding: 8px 10px;
    color: {COLOR['text_primary']};
    font-size: 13px;
}}
QTextEdit:focus {{
    border: 1px solid {COLOR['accent']};
}}
QComboBox, QDateEdit {{
    background-color: {COLOR['bg_card']};
    border: 1px solid {COLOR['border']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {COLOR['text_primary']};
    font-size: 13px;
    min-height: 36px;
}}
QComboBox:focus, QDateEdit:focus {{
    border: 1px solid {COLOR['accent']};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR['bg_card']};
    border: 1px solid {COLOR['border']};
    selection-background-color: {COLOR['accent']};
    color: {COLOR['text_primary']};
}}

/* ── Tables ── */
QTableWidget {{
    background-color: {COLOR['bg_mid']};
    border: 1px solid {COLOR['border']};
    border-radius: 8px;
    gridline-color: {COLOR['border']};
    selection-background-color: {COLOR['accent']};
}}
QTableWidget::item {{
    padding: 6px 10px;
}}
QHeaderView::section {{
    background-color: {COLOR['bg_card']};
    color: {COLOR['text_muted']};
    padding: 8px;
    border: none;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}}

/* ── Scroll Bars ── */
QScrollBar:vertical {{
    background: {COLOR['bg_mid']};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COLOR['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR['accent']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Labels ── */
QLabel#title_label {{
    font-size: 22px;
    font-weight: 700;
    color: {COLOR['text_primary']};
}}
QLabel#subtitle_label {{
    font-size: 13px;
    color: {COLOR['text_muted']};
}}
QLabel#section_label {{
    font-size: 14px;
    font-weight: 600;
    color: {COLOR['accent']};
}}

/* ── Tab Widget ── */
QTabWidget::pane {{
    border: 1px solid {COLOR['border']};
    border-radius: 8px;
    background: {COLOR['bg_mid']};
}}
QTabBar::tab {{
    background: {COLOR['bg_card']};
    color: {COLOR['text_muted']};
    padding: 8px 20px;
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background: {COLOR['accent']};
    color: white;
}}
QTabBar::tab:hover {{
    color: {COLOR['text_primary']};
}}

/* ── GroupBox ── */
QGroupBox {{
    border: 1px solid {COLOR['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    font-weight: 600;
    color: {COLOR['text_muted']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}}

/* ── Progress Bar ── */
QProgressBar {{
    background-color: {COLOR['bg_card']};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {COLOR['accent']};
    border-radius: 4px;
}}

/* ── Message Box ── */
QMessageBox {{
    background-color: {COLOR['bg_mid']};
}}
"""


def badge_style(status: str) -> str:
    """Return an inline HTML badge for a task status string."""
    colors = {
        "Pending":     (COLOR["pending"],     "#333"),
        "In Progress": (COLOR["in_progress"], "#fff"),
        "Completed":   (COLOR["success"],      "#fff"),
        "done":        (COLOR["success"],      "#fff"),
        "processing":  (COLOR["in_progress"], "#fff"),
        "pending":     (COLOR["warning"],      "#333"),
        "failed":      (COLOR["danger"],       "#fff"),
    }
    bg, fg = colors.get(status, (COLOR["bg_card"], COLOR["text_primary"]))
    return (
        f'<span style="background:{bg};color:{fg};'
        f'padding:2px 8px;border-radius:10px;font-size:11px;'
        f'font-weight:600;">{status}</span>'
    )