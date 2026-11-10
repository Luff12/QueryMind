import sqlite3
import uuid
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/querymind_history.db")


def get_history_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_history():

    conn = get_history_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            sql_query TEXT,
            created_at TEXT,
            FOREIGN KEY(session_id)
                REFERENCES chat_sessions(session_id)
                ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def create_session(title="New Conversation"):

    initialize_history()

    session_id = str(uuid.uuid4())

    conn = get_history_connection()

    conn.execute(
        """
        INSERT INTO chat_sessions
        (session_id, title, created_at)
        VALUES (?, ?, ?)
    """,
        (session_id, title, datetime.now().isoformat()),
    )

    conn.commit()
    conn.close()

    return session_id


def save_message(session_id, role, content, sql_query=None):

    conn = get_history_connection()

    conn.execute(
        """
        INSERT INTO chat_messages
        (session_id, role, content, sql_query, created_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (session_id, role, content, sql_query, datetime.now().isoformat()),
    )

    conn.commit()
    conn.close()


def get_messages(session_id):

    conn = get_history_connection()

    messages = conn.execute(
        """
        SELECT role, content, sql_query, created_at
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY message_id ASC
    """,
        (session_id,),
    ).fetchall()

    conn.close()

    return [dict(message) for message in messages]


def get_sessions():

    initialize_history()

    conn = get_history_connection()

    sessions = conn.execute("""
        SELECT session_id, title, created_at
        FROM chat_sessions
        ORDER BY created_at DESC
    """).fetchall()

    conn.close()

    return [dict(session) for session in sessions]


def delete_session(session_id):

    conn = get_history_connection()

    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        """
        DELETE FROM chat_sessions
        WHERE session_id = ?
    """,
        (session_id,),
    )

    conn.commit()
    conn.close()
