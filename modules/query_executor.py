import time
import pandas as pd
from sqlalchemy import text
from database.multi_db import get_active_engine, get_active_dialect
from modules.sql_validator import validate_sql

def _run_query(query):
    is_valid, message = validate_sql(query, dialect=get_active_dialect())
    if not is_valid:
        return None, message, 0.0, None
    try:
        engine = get_active_engine()
        dialect = get_active_dialect()
        query_plan = None
        with engine.connect() as conn:
            if dialect == "sqlite":
                try: query_plan = pd.read_sql_query(text("EXPLAIN QUERY PLAN " + query), conn)
                except Exception: query_plan = None
            elif dialect == "postgresql":
                try: query_plan = pd.read_sql_query(text("EXPLAIN " + query), conn)
                except Exception: query_plan = None
            start = time.perf_counter()
            df = pd.read_sql_query(text(query), conn)
            elapsed = (time.perf_counter() - start) * 1000
        return df, "Query executed successfully.", elapsed, query_plan
    except Exception as exc:
        return None, f"Execution error: {exc}", 0.0, None

def execute_query(query):
    df, message, _, _ = _run_query(query)
    return df, message

def execute_query_with_metrics(query):
    return _run_query(query)
