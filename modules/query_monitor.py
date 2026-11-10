from pathlib import Path
import sqlite3
from datetime import datetime, timezone


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "querymind_monitor.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            source TEXT NOT NULL,
            question TEXT,
            sql_query TEXT NOT NULL,
            execution_time_ms REAL,
            rows_returned INTEGER,
            columns_returned INTEGER,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def log_query_execution(
    sql_query,
    execution_time_ms,
    rows_returned,
    columns_returned,
    question="",
    session_id=None,
    source="Chat",
):
    """Persist one successful query execution in a separate monitoring database."""
    conn = _connect()
    try:
        conn.execute("""
            INSERT INTO query_executions (
                session_id, source, question, sql_query,
                execution_time_ms, rows_returned, columns_returned, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(session_id) if session_id is not None else None,
            str(source),
            str(question or ""),
            str(sql_query),
            float(execution_time_ms) if execution_time_ms is not None else None,
            int(rows_returned) if rows_returned is not None else 0,
            int(columns_returned) if columns_returned is not None else 0,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ))
        conn.commit()
    finally:
        conn.close()


def get_query_execution_history(limit=5000):
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT id, session_id, source, question, sql_query,
                   execution_time_ms, rows_returned, columns_returned, created_at
            FROM query_executions
            ORDER BY id DESC
            LIMIT ?
        """, (int(limit),)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def clear_query_execution_history():
    """Clear monitoring events only; does not touch the application database."""
    conn = _connect()
    try:
        conn.execute("DELETE FROM query_executions")
        conn.commit()
    finally:
        conn.close()
