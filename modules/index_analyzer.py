from database.connection import get_connection


def get_existing_indexes():
    """
    Retrieve all existing indexes from the SQLite database.
    """

    conn = None
    indexes = []

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                name,
                tbl_name,
                sql
            FROM sqlite_master
            WHERE type = 'index'
            AND name NOT LIKE 'sqlite_autoindex%'
            ORDER BY tbl_name, name;
        """)

        rows = cursor.fetchall()

        for row in rows:
            indexes.append(
                {
                    "index_name": row["name"],
                    "table_name": row["tbl_name"],
                    "create_statement": row["sql"],
                }
            )

        return indexes

    except Exception as e:
        print(f"Index analysis error: {e}")
        return []

    finally:
        if conn:
            conn.close()


def get_table_indexes(table_name):
    """
    Retrieve indexes belonging to a specific table.
    """

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Table name is passed as a bound parameter.
        cursor.execute(
            "SELECT name FROM sqlite_master " "WHERE type = 'table' AND name = ?",
            (table_name,),
        )

        if cursor.fetchone() is None:
            return []

        cursor.execute(f'PRAGMA index_list("{table_name}")')

        return [
            {
                "index_name": row["name"],
                "unique": bool(row["unique"]),
                "origin": row["origin"],
            }
            for row in cursor.fetchall()
        ]

    except Exception as e:
        print(f"Table index error: {e}")
        return []

    finally:
        if conn:
            conn.close()


def analyze_database_indexes():
    """
    Analyze indexes across all user tables.
    """

    conn = None
    report = {}

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
        """)

        tables = [row["name"] for row in cursor.fetchall()]

        for table in tables:

            cursor.execute(f'PRAGMA index_list("{table}")')

            indexes = []

            for index in cursor.fetchall():

                indexes.append(
                    {
                        "index_name": index["name"],
                        "unique": bool(index["unique"]),
                        "origin": index["origin"],
                    }
                )

            report[table] = {
                "total_indexes": len(indexes),
                "indexes": indexes,
            }

        return report

    except Exception as e:
        print(f"Database index analysis error: {e}")
        return {}

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":

    print("\n========== DATABASE INDEX ANALYSIS ==========\n")

    report = analyze_database_indexes()

    for table, details in report.items():

        print(f"\nTable: {table}")
        print(f"Total Indexes: {details['total_indexes']}")

        if details["indexes"]:

            for index in details["indexes"]:

                print(
                    f"  - {index['index_name']} "
                    f"| Unique: {index['unique']} "
                    f"| Origin: {index['origin']}"
                )

        else:
            print("  No indexes found.")

    print("\n========== CUSTOM INDEXES ==========\n")

    for index in get_existing_indexes():

        print(f"Index: {index['index_name']}")
        print(f"Table: {index['table_name']}")
        print(f"SQL: {index['create_statement']}")
        print("-" * 40)
