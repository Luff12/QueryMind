import shutil
import sqlite3
import tempfile
import time
import statistics

from pathlib import Path

from database.schema import get_database_schema

# ==========================================
# CONFIGURATION
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_DIR / "data" / "querymind.db"

INDEX_CANDIDATES = {
    "sales": [
        "customer_id",
        "employee_id",
        "product_id",
        "sale_date",
    ]
}

WARMUP_RUNS = 5
BENCHMARK_RUNS = 50


# ==========================================
# DATABASE HELPERS
# ==========================================


def quote_identifier(identifier):
    """Safely quote a SQLite identifier."""
    return '"' + identifier.replace('"', '""') + '"'


def get_sample_value(database_path, table, column):
    """Get an existing non-null value for the benchmark filter."""

    conn = sqlite3.connect(str(database_path))

    try:
        cursor = conn.cursor()

        query = (
            f"SELECT {quote_identifier(column)} "
            f"FROM {quote_identifier(table)} "
            f"WHERE {quote_identifier(column)} IS NOT NULL "
            "LIMIT 1"
        )

        cursor.execute(query)
        result = cursor.fetchone()

        return result[0] if result else None

    finally:
        conn.close()


def remove_indexes_for_column(database_path, table, column):
    """Remove explicit indexes involving the selected column."""

    conn = sqlite3.connect(str(database_path))

    try:
        cursor = conn.cursor()

        cursor.execute(f"PRAGMA index_list({quote_identifier(table)})")

        indexes = cursor.fetchall()

        for index in indexes:
            index_name = index[1]

            # SQLite automatically manages these indexes.
            if index_name.startswith("sqlite_autoindex"):
                continue

            cursor.execute(f"PRAGMA index_info({quote_identifier(index_name)})")

            indexed_columns = [row[2] for row in cursor.fetchall()]

            if column in indexed_columns:
                cursor.execute(
                    f"DROP INDEX IF EXISTS " f"{quote_identifier(index_name)}"
                )

        conn.commit()

    finally:
        conn.close()


# ==========================================
# PERFORMANCE MEASUREMENT
# ==========================================


def measure_query(database_path, query, parameter):
    """Measure query execution time and collect its query plan."""

    conn = sqlite3.connect(str(database_path))

    try:
        cursor = conn.cursor()

        cursor.execute("EXPLAIN QUERY PLAN " + query, (parameter,))

        query_plan = [row[3] for row in cursor.fetchall()]

        # Warm-up runs
        for _ in range(WARMUP_RUNS):
            cursor.execute(query, (parameter,))
            cursor.fetchall()

        execution_times = []

        # Actual benchmark runs
        for _ in range(BENCHMARK_RUNS):
            start = time.perf_counter()

            cursor.execute(query, (parameter,))
            cursor.fetchall()

            end = time.perf_counter()

            execution_times.append((end - start) * 1000)

        return {
            "average_ms": statistics.mean(execution_times),
            "median_ms": statistics.median(execution_times),
            "query_plan": query_plan,
        }

    finally:
        conn.close()


# ==========================================
# BENCHMARK ENGINE
# ==========================================


def benchmark_index(table, column):

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")

    schema = get_database_schema()

    if table not in schema:
        raise ValueError(f"Unknown table: {table}")

    available_columns = {item["name"] for item in schema[table]["columns"]}

    if column not in available_columns:
        raise ValueError(f"Unknown column: {table}.{column}")

    sample_value = get_sample_value(DATABASE_PATH, table, column)

    if sample_value is None:
        return None

    query = (
        f"SELECT * FROM {quote_identifier(table)} "
        f"WHERE {quote_identifier(column)} = ?"
    )

    index_name = f"idx_{table}_{column}"

    # Temporary directory ensures the original database is untouched.
    with tempfile.TemporaryDirectory() as temp_dir:

        temp_path = Path(temp_dir)

        before_db = temp_path / "before_index.db"
        after_db = temp_path / "after_index.db"

        shutil.copy2(DATABASE_PATH, before_db)
        shutil.copy2(DATABASE_PATH, after_db)

        # BEFORE: remove explicit indexes on this candidate column.
        remove_indexes_for_column(before_db, table, column)

        before_result = measure_query(before_db, query, sample_value)

        # AFTER: create the candidate index in the second copy.
        conn = sqlite3.connect(str(after_db))

        try:
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS "
                f"{quote_identifier(index_name)} "
                f"ON {quote_identifier(table)} "
                f"({quote_identifier(column)})"
            )
            conn.commit()

        finally:
            conn.close()

        after_result = measure_query(after_db, query, sample_value)

    before_time = before_result["median_ms"]
    after_time = after_result["median_ms"]

    if before_time > 0:
        improvement = ((before_time - after_time) / before_time) * 100
    else:
        improvement = 0

    return {
        "table": table,
        "column": column,
        "before_average": before_result["average_ms"],
        "after_average": after_result["average_ms"],
        "before_median": before_time,
        "after_median": after_time,
        "improvement_percent": improvement,
        "before_plan": before_result["query_plan"],
        "after_plan": after_result["query_plan"],
    }


# ==========================================
# RUN ALL BENCHMARKS
# ==========================================


def run_all_benchmarks():

    results = []

    for table, columns in INDEX_CANDIDATES.items():

        for column in columns:

            print(f"\nBenchmarking {table}.{column}...")

            result = benchmark_index(table, column)

            if result is None:
                print("Skipped: no non-null sample value found.")
                continue

            results.append(result)

    return results


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    print("\n========== QUERYMIND INDEX BENCHMARK ==========")

    print(f"Warm-up runs: {WARMUP_RUNS}")
    print(f"Benchmark runs: {BENCHMARK_RUNS}")

    results = run_all_benchmarks()

    for number, result in enumerate(results, start=1):

        print(f"\n{'=' * 50}")
        print(f"BENCHMARK {number}")
        print(f"Table: {result['table']}")
        print(f"Column: {result['column']}")

        print("\nBEFORE INDEX")
        print(f"Average: {result['before_average']:.6f} ms")
        print(f"Median:  {result['before_median']:.6f} ms")

        print("\nAFTER INDEX")
        print(f"Average: {result['after_average']:.6f} ms")
        print(f"Median:  {result['after_median']:.6f} ms")

        print("\nPERFORMANCE DIFFERENCE")
        print(f"{result['improvement_percent']:.2f}%")

        print("\nQUERY PLAN BEFORE INDEX")
        for detail in result["before_plan"]:
            print("-", detail)

        print("\nQUERY PLAN AFTER INDEX")
        for detail in result["after_plan"]:
            print("-", detail)

    print("\n========== BENCHMARK COMPLETED ==========")
    print("Original database was not modified.")
