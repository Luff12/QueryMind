import sqlglot
from sqlglot import exp


def validate_sql(query, dialect=None):
    if dialect is None:
        try:
            from database.multi_db import get_active_dialect
            dialect = get_active_dialect()
        except Exception:
            dialect = "sqlite"
    dialect = {"postgresql": "postgres", "mariadb": "mysql"}.get(dialect, dialect)

    if not query or not query.strip():
        return False, "SQL query is empty."

    try:
        # Parse SQL using the active database dialect.
        statements = sqlglot.parse(query, read=dialect)

        # Reject multiple statements
        if len(statements) != 1:
            return False, "Only one SQL statement is allowed."

        parsed = statements[0]

        if parsed is None:
            return False, "Invalid SQL query."

        # Allow only SELECT statements
        if not isinstance(parsed, exp.Query):
            return False, "Only SELECT queries are permitted."

        # Reject modifying or administrative operations
        forbidden = (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Drop,
            exp.Create,
            exp.Alter,
            exp.Command,
        )

        for node in parsed.walk():
            if isinstance(node, forbidden):
                return False, "Unsafe SQL operation detected."

        return True, "SQL query validated successfully."

    except sqlglot.errors.ParseError as e:
        return False, f"SQL syntax error: {e}"

    except Exception as e:
        return False, f"Validation error: {e}"


if __name__ == "__main__":

    test_queries = [
        "SELECT * FROM customers",
        "SELECT * FROM products WHERE price > 1000",
        "DELETE FROM customers",
        "DROP TABLE employees",
        "UPDATE employees SET salary = 50000",
        "SELECT * FROM sales; DROP TABLE customers;",
    ]

    for query in test_queries:

        valid, message = validate_sql(query)

        print("\nQuery:", query)
        print("Valid:", valid)
        print("Message:", message)
