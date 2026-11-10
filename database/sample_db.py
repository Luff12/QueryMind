import sqlite3
from pathlib import Path

DB_PATH = Path("data/querymind.db")


def create_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name TEXT,
        city TEXT,
        email TEXT
    );

    CREATE TABLE IF NOT EXISTS employees (
        employee_id INTEGER PRIMARY KEY,
        employee_name TEXT,
        department TEXT,
        salary REAL
    );

    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT,
        category TEXT,
        price REAL
    );

    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        employee_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        sale_date TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY(employee_id) REFERENCES employees(employee_id),
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    );
    """)

    cursor.executemany(
        "INSERT OR IGNORE INTO customers VALUES (?, ?, ?, ?)",
        [
            (1, "Arun", "Kochi", "arun@example.com"),
            (2, "Rahul", "Thiruvalla", "rahul@example.com"),
            (3, "Anjali", "Trivandrum", "anjali@example.com"),
            (4, "Meera", "Kottayam", "meera@example.com"),
            (5, "Vishnu", "Pathanamthitta", "vishnu@example.com"),
        ],
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO employees VALUES (?, ?, ?, ?)",
        [
            (1, "John", "Sales", 35000),
            (2, "Priya", "Marketing", 42000),
            (3, "Akhil", "Sales", 38000),
            (4, "Neha", "HR", 40000),
        ],
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?)",
        [
            (1, "Laptop", "Electronics", 55000),
            (2, "Mouse", "Accessories", 700),
            (3, "Keyboard", "Accessories", 1200),
            (4, "Monitor", "Electronics", 12000),
            (5, "Headphones", "Accessories", 2500),
        ],
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO sales VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, 1, 1, 1, 2, "2026-10-01"),
            (2, 2, 3, 2, 5, "2026-10-02"),
            (3, 3, 1, 3, 3, "2026-10-03"),
            (4, 4, 2, 4, 1, "2026-10-04"),
            (5, 5, 3, 5, 4, "2026-10-05"),
            (6, 1, 2, 2, 2, "2026-10-06"),
            (7, 3, 1, 1, 1, "2026-10-07"),
            (8, 2, 3, 4, 2, "2026-10-08"),
        ],
    )

    conn.commit()
    conn.close()

    print("QueryMind database created successfully!")


if __name__ == "__main__":
    create_database()
