-- ============================================================
-- Meeting Analyzer - Database Schema
-- ============================================================

-- Users table (Admin + Employee)
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,
    full_name   TEXT    NOT NULL,
    role        TEXT    NOT NULL CHECK(role IN ('admin', 'employee')),
    created_at  TEXT    DEFAULT (datetime('now'))
);

-- Meetings table (uploaded recordings)
CREATE TABLE IF NOT EXISTS meetings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    audio_path      TEXT,
    transcript      TEXT,
    summary         TEXT,
    uploaded_by     INTEGER REFERENCES users(id),
    created_at      TEXT    DEFAULT (datetime('now')),
    status          TEXT    DEFAULT 'pending' CHECK(status IN ('pending','processing','done','failed'))
);

-- Live Meetings table (real-time sessions)
CREATE TABLE IF NOT EXISTS live_meetings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    host_id         INTEGER REFERENCES users(id),
    host_ip         TEXT,
    port            INTEGER,
    transcript      TEXT    DEFAULT '',
    summary         TEXT    DEFAULT '',
    started_at      TEXT    DEFAULT (datetime('now')),
    ended_at        TEXT,
    status          TEXT    DEFAULT 'active' CHECK(status IN ('active','ended'))
);

-- Live Meeting Participants
CREATE TABLE IF NOT EXISTS live_participants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    live_meeting_id INTEGER REFERENCES live_meetings(id) ON DELETE CASCADE,
    user_id         INTEGER REFERENCES users(id),
    joined_at       TEXT    DEFAULT (datetime('now')),
    left_at         TEXT
);

-- Tasks table (shared between uploaded & live meetings)
CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id      INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    live_meeting_id INTEGER REFERENCES live_meetings(id) ON DELETE CASCADE,
    title           TEXT    NOT NULL,
    description     TEXT,
    assigned_to     INTEGER REFERENCES users(id),
    deadline        TEXT,
    status          TEXT    DEFAULT 'Pending' CHECK(status IN ('Pending','In Progress','Completed')),
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now'))
);

-- Seed default admin account
INSERT OR IGNORE INTO users (username, password, full_name, role)
VALUES (
    'admin',
    '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918',
    'System Administrator',
    'admin'
);