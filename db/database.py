import sqlite3, json, os
from datetime import datetime
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'meetings.db')
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # rows behave like dicts
    return conn
def init_db():
    """
    Creates the meetings table if it does not exist.
    Call this once when the app starts.
    """
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audio_url TEXT NOT NULL,
            transcript TEXT,
            summary TEXT,
            action_items TEXT, -- stored as JSON string
            sentiment TEXT, -- stored as JSON string
            report TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
def save_meeting(result: dict) -> int:
    """
    Saves one analysis result. Returns the new row id.
    """
    conn = get_connection()
    cursor = conn.execute(
        '''INSERT INTO meetings
            (audio_url, transcript, summary, action_items, sentiment, report, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (
            result.get('audio_url', ''),
            result.get('transcript', ''),
            result.get('summary', ''),
            json.dumps(result.get('action_items', [])),
            json.dumps(result.get('sentiment', {})),
            result.get('report', ''),
            datetime.utcnow().isoformat(),
        )
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id
def get_all_meetings() -> list:
    """Returns all meetings, newest first."""
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM meetings ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
def search_meetings(query: str) -> list:
    """Simple full-text search across summary and transcript."""
    conn = get_connection()
    like = f'%{query}%'
    rows = conn.execute(
        '''SELECT * FROM meetings
            WHERE summary LIKE ? OR transcript LIKE ?
            ORDER BY created_at DESC''',
        (like, like)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]  