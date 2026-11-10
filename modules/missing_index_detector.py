from database.schema import get_database_schema
from modules.index_analyzer import analyze_database_indexes

# Columns frequently used in filtering and table relationships.
# These are candidates for analysis, not guaranteed missing indexes.
INDEX_CANDIDATES = {
    "sales": [
        "customer_id",
        "employee_id",
        "product_id",
        "sale_date",
    ],
}


def detect_missing_indexes():
    """
    Identify potential index candidates by comparing
    commonly queried columns with existing indexes.

    This is a heuristic detector. It does not prove that
    an index is necessary or improve performance.
    """

    schema = get_database_schema()
    existing_indexes = analyze_database_indexes()

    recommendations = []

    for table_name, columns in INDEX_CANDIDATES.items():

        if table_name not in schema:
            continue

        # Collect columns already covered by existing indexes.
        indexed_columns = set()

        table_indexes = existing_indexes.get(table_name, {}).get("indexes", [])

        # Retrieve indexed columns using SQLite PRAGMA.
        from database.connection import get_connection

        conn = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

            for index in table_indexes:
                index_name = index["index_name"]

                cursor.execute(f'PRAGMA index_info("{index_name}")')

                for row in cursor.fetchall():
                    if row["name"]:
                        indexed_columns.add(row["name"])

        finally:
            if conn:
                conn.close()

        available_columns = {column["name"] for column in schema[table_name]["columns"]}

        for column_name in columns:

            if column_name not in available_columns:
                continue

            if column_name not in indexed_columns:

                recommendations.append(
                    {
                        "table": table_name,
                        "column": column_name,
                        "reason": (
                            "Potential index candidate because this column "
                            "is commonly used for filtering or table relationships."
                        ),
                        "sql": (
                            f"CREATE INDEX IF NOT EXISTS "
                            f"idx_{table_name}_{column_name} "
                            f"ON {table_name} ({column_name});"
                        ),
                    }
                )

    return recommendations


if __name__ == "__main__":

    print("\n========== MISSING INDEX ANALYSIS ==========\n")

    results = detect_missing_indexes()

    if not results:
        print("No potential missing indexes detected.")

    else:

        for item in results:

            print(f"Table: {item['table']}")
            print(f"Column: {item['column']}")
            print(f"Reason: {item['reason']}")
            print(f"Suggested SQL: {item['sql']}")
            print("-" * 50)

    print("\nAnalysis completed.")
