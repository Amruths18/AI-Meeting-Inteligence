# 🎙️ Meeting Analyzer – AI-Powered Desktop Application

A fully offline desktop application that transcribes meeting audio, generates summaries, and extracts action items using AI.

---

## 🗂️ Project Structure

```
meeting_analyzer/
├── main.py                        ← Application entry point
├── requirements.txt               ← Python dependencies
├── database/
│   ├── __init__.py
│   ├── db_manager.py              ← All SQLite CRUD operations
│   └── schema.sql                 ← Database schema + seed data
├── ai/
│   ├── __init__.py
│   ├── transcriber.py             ← OpenAI Whisper speech-to-text
│   └── nlp_processor.py          ← spaCy summary + task extraction
├── ui/
│   ├── __init__.py
│   ├── styles.py                  ← App-wide color palette & stylesheet
│   ├── login_window.py            ← Login screen
│   ├── upload_window.py           ← Audio upload + processing dialog
│   ├── meeting_detail.py          ← Transcript / Summary / Tasks viewer
│   ├── admin_dashboard.py         ← Admin main window
│   └── employee_dashboard.py      ← Employee main window
└── data/                          ← Created automatically at runtime
    ├── meeting_analyzer.db
    └── audio_files/
```

---

## ⚙️ Installation

### Step 1 – Create a virtual environment (recommended)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
```

### Step 2 – Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 – Download the spaCy language model
```bash
python -m spacy download en_core_web_sm
```

### Step 4 – Run the application
```bash
python main.py
```

---

## 🔐 Default Login

| Role     | Username | Password |
|----------|----------|----------|
| Admin    | admin    | admin    |

Admins can create new employee accounts from the **Users** tab.

---

## 🧠 How AI Processing Works

1. **Upload** – Admin selects a `.mp3`, `.wav`, `.m4a`, or similar audio file.
2. **Transcription** – OpenAI Whisper converts speech to text **100% offline**.
3. **Summarisation** – spaCy performs extractive summarisation (top sentences by TF-IDF frequency score).
4. **Task Extraction** – Rule-based NLP detects action verbs, named entities (people), and deadline phrases.
5. **Storage** – Results are saved to a local SQLite database.
6. **Dashboard** – Admin reviews and assigns extracted tasks; employees update task status.

---

## 🤖 Whisper Model Options

Edit `ai/transcriber.py` → `DEFAULT_MODEL` to change the model:

| Model  | Size  | Speed  | Accuracy  |
|--------|-------|--------|-----------|
| tiny   | 39 MB | Fastest| Lower     |
| base   | 74 MB | Fast   | Good ✅    |
| small  | 244 MB| Medium | Better    |
| medium | 769 MB| Slow   | Very Good |
| large  | 1.5 GB| Slowest| Best      |

> The model is downloaded once on first use and cached locally.

---

## 📦 Dependencies

| Package         | Purpose                        |
|-----------------|--------------------------------|
| PyQt5           | Desktop GUI framework          |
| openai-whisper  | Offline speech-to-text AI      |
| spacy           | NLP (summarisation, NER)       |
| numpy           | Numerical support for Whisper  |
| sqlite3         | Built-in Python database       |

---

## 👥 User Roles

### 👨‍💼 Admin
- Upload and process meeting recordings
- View full transcripts and AI summaries
- Assign extracted tasks to employees
- Add / remove user accounts
- Monitor all task progress

### 👨‍💻 Employee
- View personally assigned tasks
- Update task status (Pending → In Progress → Completed)
- Filter tasks by status

---

## 🔒 Privacy & Security
- All audio processing is **100% offline** — no data leaves your machine
- Passwords are stored as **SHA-256 hashes** (never plain text)
- Audio files are stored locally in `data/audio_files/`
