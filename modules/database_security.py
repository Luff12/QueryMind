import re
from database.connection import get_connection
from database.schema import get_database_schema
from modules.query_monitor import get_query_execution_history


SENSITIVE_NAME_PATTERNS = {
    "Personal information": (
        "email", "phone", "mobile", "address", "birth", "dob",
        "passport", "ssn", "aadhaar", "aadhar"
    ),
    "Authentication / secret data": (
        "password", "passwd", "secret", "token", "api_key",
        "private_key", "credential"
    ),
    "Financial information": (
        "card", "account_number", "bank", "upi", "salary",
        "payment"
    ),
}

RISKY_SQL_PATTERNS = {
    "Data modification statement": r"\b(INSERT|UPDATE|DELETE|REPLACE)\b",
    "Schema modification statement": r"\b(CREATE|ALTER|DROP|TRUNCATE)\b",
    "Database attachment or detachment": r"\b(ATTACH|DETACH)\b",
    "Potentially sensitive database command": r"\b(PRAGMA|VACUUM)\b",
}


def _finding(severity, category, item, detail, recommendation):
    return {
        "severity": severity,
        "category": category,
        "item": item,
        "detail": detail,
        "recommendation": recommendation,
    }


def run_database_security_audit():
    """
    Run read-only SQLite configuration, integrity, schema-name and query-history checks.
    This is a heuristic audit, not a penetration test or a full access-control review.
    """
    findings = []
    schema = get_database_schema()
    sensitive_columns = []

    for table_name, table_info in schema.items():
        for column in table_info.get("columns", []):
            column_name = str(column.get("name", ""))
            lowered = column_name.lower()
            for category, terms in SENSITIVE_NAME_PATTERNS.items():
                if any(term in lowered for term in terms):
                    sensitive_columns.append({
                        "table": table_name,
                        "column": column_name,
                        "category": category,
                    })
                    findings.append(_finding(
                        "Warning",
                        "Sensitive column",
                        f"{table_name}.{column_name}",
                        f"Column name suggests {category.lower()} may be stored here.",
                        "Restrict access to this field, avoid exposing it in broad queries, "
                        "and apply appropriate protection to the underlying data."
                    ))
                    break

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys")
        foreign_keys_enabled = bool(cursor.fetchone()[0])

        if not foreign_keys_enabled:
            findings.append(_finding(
                "High",
                "SQLite configuration",
                "foreign_keys",
                "Foreign-key enforcement is disabled for this connection.",
                "Enable PRAGMA foreign_keys = ON for every application connection "
                "and verify that the setting is applied before transactions."
            ))
        else:
            findings.append(_finding(
                "Info",
                "SQLite configuration",
                "foreign_keys",
                "Foreign-key enforcement is enabled for this connection.",
                "Keep this enabled and continue validating relationships."
            ))

        cursor.execute("PRAGMA journal_mode")
        journal_mode = str(cursor.fetchone()[0])

        if journal_mode.lower() == "off":
            findings.append(_finding(
                "Warning",
                "SQLite configuration",
                "journal_mode",
                "SQLite journal mode is OFF.",
                "Use a journaling mode appropriate for your deployment and backup strategy."
            ))

        cursor.execute("PRAGMA integrity_check")
        integrity_rows = [str(row[0]) for row in cursor.fetchall()]
        integrity_ok = integrity_rows == ["ok"]

        if not integrity_ok:
            findings.append(_finding(
                "High",
                "Database integrity",
                "integrity_check",
                "; ".join(integrity_rows[:10]),
                "Stop writes, create a safe backup, and investigate database integrity "
                "before attempting repair."
            ))
        else:
            findings.append(_finding(
                "Info",
                "Database integrity",
                "integrity_check",
                "SQLite integrity_check returned OK.",
                "Continue maintaining regular backups."
            ))

        cursor.execute("PRAGMA foreign_key_check")
        fk_rows = cursor.fetchall()
        if fk_rows:
            findings.append(_finding(
                "High",
                "Referential integrity",
                "foreign_key_check",
                f"{len(fk_rows)} foreign-key violation(s) detected.",
                "Review the affected child and parent records and correct the data "
                "using a controlled, backed-up process."
            ))
        else:
            findings.append(_finding(
                "Info",
                "Referential integrity",
                "foreign_key_check",
                "No foreign-key violations were detected.",
                "Keep foreign-key enforcement enabled for future writes."
            ))

    finally:
        conn.close()

    # Inspect only SQL executions recorded by QueryMind's monitoring module.
    history = get_query_execution_history(limit=5000)
    risky_history = []
    select_star = []

    for record in history:
        sql = str(record.get("sql_query") or "")
        for category, pattern in RISKY_SQL_PATTERNS.items():
            if re.search(pattern, sql, flags=re.IGNORECASE):
                risky_history.append({
                    "id": record.get("id"),
                    "source": record.get("source"),
                    "category": category,
                    "sql_query": sql,
                    "created_at": record.get("created_at"),
                })
                break

        if re.search(r"\bSELECT\s+\*", sql, flags=re.IGNORECASE):
            select_star.append({
                "id": record.get("id"),
                "source": record.get("source"),
                "sql_query": sql,
                "created_at": record.get("created_at"),
            })

    if risky_history:
        findings.append(_finding(
            "High",
            "Query history",
            "Potentially risky SQL",
            f"{len(risky_history)} monitored query/queries contain modification, "
            "schema, attachment or sensitive command keywords.",
            "Review each statement and confirm it was expected. Query history is "
            "a record of SQL text, not proof that the statement was executed."
        ))
    else:
        findings.append(_finding(
            "Info",
            "Query history",
            "Potentially risky SQL",
            "No monitored SQL statements matched the configured risky-keyword rules.",
            "Continue validating every generated query before execution."
        ))

    if select_star:
        findings.append(_finding(
            "Warning",
            "Query history",
            "SELECT * usage",
            f"{len(select_star)} monitored query/queries use SELECT *.",
            "Select only the columns required. This reduces accidental exposure "
            "of sensitive fields and can reduce unnecessary data transfer."
        ))

    return {
        "findings": findings,
        "sensitive_columns": sensitive_columns,
        "risky_queries": risky_history,
        "select_star_queries": select_star,
        "history_scanned": len(history),
        "tables_scanned": len(schema),
        "foreign_keys_enabled": foreign_keys_enabled,
        "journal_mode": journal_mode,
        "integrity_ok": integrity_ok,
        "foreign_key_violation_count": len(fk_rows),
    }
