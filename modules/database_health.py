from database.connection import get_connection
from database.schema import get_database_schema


def _quote_identifier(identifier):
    """Quote a SQLite table or column identifier."""
    return '"' + str(identifier).replace('"', '""') + '"'


def _get_table_names(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """)
    return [row[0] for row in cursor.fetchall()]


def _count_duplicate_rows(conn, table_name, column_names):
    """Count extra duplicate rows across all columns."""
    if not column_names:
        return 0

    quoted_columns = ", ".join(_quote_identifier(c) for c in column_names)
    query = f"""
        SELECT COALESCE(SUM(group_count - 1), 0)
        FROM (
            SELECT COUNT(*) AS group_count
            FROM {_quote_identifier(table_name)}
            GROUP BY {quoted_columns}
            HAVING COUNT(*) > 1
        )
    """
    cursor = conn.cursor()
    cursor.execute(query)
    return int(cursor.fetchone()[0] or 0)


def _profile_table(conn, table_name, table_schema):
    """Collect row counts and column-level quality statistics."""
    quoted_table = _quote_identifier(table_name)
    columns = table_schema.get("columns", [])

    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {quoted_table}")
    total_rows = int(cursor.fetchone()[0])

    column_profiles = []
    total_null_cells = 0
    total_blank_cells = 0

    for column in columns:
        column_name = column["name"]
        declared_type = str(column.get("type", "") or "").upper()
        quoted_column = _quote_identifier(column_name)

        cursor.execute(
            f"SELECT COUNT(*) FROM {quoted_table} " f"WHERE {quoted_column} IS NULL"
        )
        null_count = int(cursor.fetchone()[0])

        blank_count = 0
        if any(token in declared_type for token in ("TEXT", "CHAR", "CLOB")):
            cursor.execute(
                f"SELECT COUNT(*) FROM {quoted_table} "
                f"WHERE {quoted_column} IS NOT NULL "
                f"AND TRIM(CAST({quoted_column} AS TEXT)) = ''"
            )
            blank_count = int(cursor.fetchone()[0])

        total_null_cells += null_count
        total_blank_cells += blank_count

        column_profiles.append(
            {
                "column": column_name,
                "data_type": declared_type or "Not declared",
                "null_count": null_count,
                "null_percentage": (
                    null_count / total_rows * 100 if total_rows else 0.0
                ),
                "blank_count": blank_count,
                "primary_key": bool(column.get("pk", column.get("primary_key", False))),
                "not_null": bool(column.get("notnull", column.get("not_null", False))),
            }
        )

    duplicate_rows = _count_duplicate_rows(
        conn,
        table_name,
        [column["name"] for column in columns],
    )

    return {
        "table": table_name,
        "row_count": total_rows,
        "column_count": len(columns),
        "empty": total_rows == 0,
        "duplicate_rows": duplicate_rows,
        "null_cells": total_null_cells,
        "blank_cells": total_blank_cells,
        "columns": column_profiles,
        "foreign_keys": table_schema.get("foreign_keys", []),
    }


def get_database_health_report():
    """
    Analyze the SQLite database without modifying its contents.

    Duplicate rows means extra rows in identical full-row groups.
    The health score is a simple heuristic, not a formal certification.
    """
    schema = get_database_schema()
    conn = get_connection()

    try:
        table_names = _get_table_names(conn)
        table_reports = [
            _profile_table(conn, table_name, schema.get(table_name, {}))
            for table_name in table_names
        ]
    finally:
        conn.close()

    total_tables = len(table_reports)
    total_rows = sum(t["row_count"] for t in table_reports)
    empty_tables = sum(t["empty"] for t in table_reports)
    total_null_cells = sum(t["null_cells"] for t in table_reports)
    total_blank_cells = sum(t["blank_cells"] for t in table_reports)
    total_duplicate_rows = sum(t["duplicate_rows"] for t in table_reports)
    total_cells = sum(t["row_count"] * t["column_count"] for t in table_reports)

    null_percentage = total_null_cells / total_cells * 100 if total_cells else 0.0

    observations = []

    if total_tables == 0:
        observations.append(
            {
                "severity": "High",
                "message": "No user tables were found in the database.",
            }
        )

    for table in table_reports:
        if table["empty"]:
            observations.append(
                {
                    "severity": "Warning",
                    "message": f"Table '{table['table']}' contains no records.",
                }
            )

        if table["duplicate_rows"]:
            observations.append(
                {
                    "severity": "Review",
                    "message": (
                        f"Table '{table['table']}' contains "
                        f"{table['duplicate_rows']} extra duplicate row(s). "
                        "Review whether these are expected."
                    ),
                }
            )

        for column in table["columns"]:
            if column["null_count"]:
                observations.append(
                    {
                        "severity": "Review",
                        "message": (
                            f"{table['table']}.{column['column']} contains "
                            f"{column['null_count']} NULL value(s)."
                        ),
                    }
                )
            if column["blank_count"]:
                observations.append(
                    {
                        "severity": "Review",
                        "message": (
                            f"{table['table']}.{column['column']} contains "
                            f"{column['blank_count']} blank text value(s)."
                        ),
                    }
                )

    score = 100
    score -= min(empty_tables * 10, 30)
    score -= min(total_duplicate_rows * 5, 30)
    score -= min(total_null_cells * 2, 30)
    score -= min(total_blank_cells * 2, 10)
    score = max(0, score)

    if score >= 90:
        status = "Healthy"
    elif score >= 70:
        status = "Needs Review"
    else:
        status = "Attention Required"

    return {
        "health_score": score,
        "health_status": status,
        "total_tables": total_tables,
        "total_rows": total_rows,
        "empty_tables": empty_tables,
        "total_null_cells": total_null_cells,
        "total_blank_cells": total_blank_cells,
        "total_duplicate_rows": total_duplicate_rows,
        "null_percentage": null_percentage,
        "table_reports": table_reports,
        "observations": observations,
    }


if __name__ == "__main__":
    report = get_database_health_report()
    print("\n========== QUERYMIND DATABASE HEALTH ==========")
    print(f"Health score: {report['health_score']}/100")
    print(f"Status: {report['health_status']}")
    print(f"Tables: {report['total_tables']}")
    print(f"Rows: {report['total_rows']}")
    print(f"Empty tables: {report['empty_tables']}")
    print(f"NULL cells: {report['total_null_cells']}")
    print(f"Blank text cells: {report['total_blank_cells']}")
    print(f"Extra duplicate rows: {report['total_duplicate_rows']}")

    for table in report["table_reports"]:
        print(f"\nTable: {table['table']}")
        print(f"Rows: {table['row_count']}")
        print(f"Columns: {table['column_count']}")
        print(f"Duplicate rows: {table['duplicate_rows']}")
        for column in table["columns"]:
            print(
                f"  {column['column']} ({column['data_type']}): "
                f"NULL={column['null_count']}, "
                f"Blank={column['blank_count']}"
            )

    print("\nObservations:")
    if not report["observations"]:
        print("No basic data-quality issues were detected.")
    else:
        for item in report["observations"]:
            print(f"- [{item['severity']}] {item['message']}")
