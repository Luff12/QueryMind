"""Multi-database SQLAlchemy connection manager for QueryMind.

Connection credentials live only in the current Streamlit session.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

DEFAULT_SQLITE_URL = "sqlite:///data/querymind.db"

def _session_state():
    try:
        import streamlit as st
        return st.session_state
    except Exception:
        return {}

def _config():
    return _session_state().get("querymind_db_config", {"url": DEFAULT_SQLITE_URL, "dialect": "sqlite", "label": "Local SQLite"})

@lru_cache(maxsize=8)
def _engine_for_url(url: str):
    from sqlalchemy import create_engine
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, future=True, connect_args=connect_args)

def get_active_engine():
    cfg = _config()
    url = cfg.get("url") or DEFAULT_SQLITE_URL
    if url.startswith("sqlite:///data/"):
        Path("data").mkdir(exist_ok=True)
    return _engine_for_url(url)

def get_active_dialect():
    return _config().get("dialect", "sqlite")

def get_active_database_label():
    return _config().get("label", "Local SQLite")

def set_active_connection(url: str, dialect: str, label: str):
    # URL is held in session state only; do not persist passwords to disk.
    state = _session_state()
    state["querymind_db_config"] = {"url": url, "dialect": dialect, "label": label}
    _engine_for_url.cache_clear()

def test_connection(url: str):
    from sqlalchemy import create_engine, text
    engine = None
    try:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Connection successful."
    except Exception as exc:
        return False, str(exc)
    finally:
        if engine is not None:
            engine.dispose()

def reset_connection():
    _session_state()["querymind_db_config"] = {"url": DEFAULT_SQLITE_URL, "dialect": "sqlite", "label": "Local SQLite"}
    _engine_for_url.cache_clear()
