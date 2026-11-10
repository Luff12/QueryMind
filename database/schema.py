from sqlalchemy import inspect
from database.multi_db import get_active_engine, get_active_dialect

def get_database_schema():
    """Return a normalized schema for SQLite, PostgreSQL or MySQL."""
    engine = get_active_engine()
    inspector = inspect(engine)
    schema = {}
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        pk_cols = set((inspector.get_pk_constraint(table_name) or {}).get("constrained_columns") or [])
        foreign_keys = inspector.get_foreign_keys(table_name)
        schema[table_name] = {
            "columns": [{"name": c["name"], "type": str(c.get("type", "UNKNOWN")), "primary_key": c["name"] in pk_cols} for c in columns],
            "foreign_keys": [{"column": (fk.get("constrained_columns") or [""])[0], "references_table": fk.get("referred_table", ""), "references_column": (fk.get("referred_columns") or [""])[0]} for fk in foreign_keys],
        }
    return schema

if __name__ == "__main__":
    import json
    print(json.dumps(get_database_schema(), indent=4))
