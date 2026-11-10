from collections import defaultdict

import sqlglot
from sqlglot import exp


def _safe_name(value):
    return str(value) if value is not None else "unknown"


def analyze_sql_lineage(sql_query, dialect="sqlite"):
    """
    Extract table-level and projection-level lineage from a SQL SELECT query.

    This is static SQL analysis only: it does not execute the query.
    Complex constructs, wildcard projections, ambiguous unqualified columns,
    and nested/CTE semantics may require manual review.
    """
    dialect = {"postgresql": "postgres", "mariadb": "mysql"}.get(dialect, dialect)
    if not sql_query or not str(sql_query).strip():
        raise ValueError("Enter a SQL query to analyze.")

    statements = sqlglot.parse(str(sql_query), read=dialect)
    if not statements or len(statements) != 1 or statements[0] is None:
        raise ValueError("Provide exactly one valid SQL statement.")

    tree = statements[0]
    if not isinstance(tree, exp.Query):
        raise ValueError("Only SELECT-style queries can be analyzed.")

    table_alias_map = {}
    source_tables = []

    for table in tree.find_all(exp.Table):
        table_name = table.name
        if not table_name:
            continue

        alias = table.alias_or_name
        database = table.db
        catalog = table.catalog
        full_name = ".".join(
            part for part in (catalog, database, table_name) if part
        )
        if full_name not in source_tables:
            source_tables.append(full_name)
        table_alias_map[alias.lower()] = full_name
        table_alias_map[table_name.lower()] = full_name

    if not source_tables:
        raise ValueError(
            "No source tables were found. This tracker currently focuses on "
            "queries that read from named database tables."
        )

    # Extract join relationships from ON predicates.
    join_relationships = []
    seen_joins = set()
    for join in tree.find_all(exp.Join):
        on_expression = join.args.get("on")
        if on_expression is None:
            continue

        for equality in on_expression.find_all(exp.EQ):
            left = equality.this
            right = equality.expression
            if not isinstance(left, exp.Column) or not isinstance(right, exp.Column):
                continue

            left_table = table_alias_map.get(
                (left.table or "").lower(),
                left.table or "Unresolved"
            )
            right_table = table_alias_map.get(
                (right.table or "").lower(),
                right.table or "Unresolved"
            )
            relationship = {
                "left": f"{left_table}.{left.name}",
                "right": f"{right_table}.{right.name}",
                "condition": equality.sql(dialect=dialect),
            }
            signature = (
                relationship["left"],
                relationship["right"],
                relationship["condition"],
            )
            if signature not in seen_joins:
                seen_joins.add(signature)
                join_relationships.append(relationship)

    # Use the main SELECT projections. For nested queries, SQLGlot's outer
    # SELECT is preferred; referenced source columns are still collected
    # from each projection expression.
    select_node = tree if isinstance(tree, exp.Select) else tree.find(exp.Select)
    if select_node is None:
        raise ValueError("Could not identify a SELECT projection in this query.")

    projections = []
    for projection in select_node.expressions:
        output_name = projection.alias_or_name or projection.sql(dialect=dialect)
        referenced_columns = []
        for column in projection.find_all(exp.Column):
            source_alias = (column.table or "").lower()
            source_table = table_alias_map.get(source_alias)

            if source_table is None:
                if column.table:
                    source_table = column.table
                elif len(source_tables) == 1:
                    source_table = source_tables[0]
                else:
                    source_table = "Unresolved source"

            source_column = "*" if isinstance(column.this, exp.Star) else column.name
            source_reference = f"{source_table}.{source_column}"

            if source_reference not in referenced_columns:
                referenced_columns.append(source_reference)

        if isinstance(projection, exp.Star) or (
            isinstance(projection, exp.Column) and isinstance(projection.this, exp.Star)
        ):
            referenced_columns = [
                f"{table}.*" for table in source_tables
            ]

        projections.append({
            "output_column": _safe_name(output_name),
            "source_columns": referenced_columns,
            "expression": projection.sql(dialect=dialect),
        })

    # Collect all referenced columns for an overall source-field inventory.
    source_columns = []
    for projection in projections:
        for source_column in projection["source_columns"]:
            if source_column not in source_columns:
                source_columns.append(source_column)

    return {
        "source_tables": source_tables,
        "source_columns": source_columns,
        "join_relationships": join_relationships,
        "projections": projections,
        "sql": str(sql_query),
        "dialect": dialect,
        "notes": [
            "Lineage is inferred from SQL syntax; it does not prove actual runtime data movement.",
            "Unqualified columns in multi-table queries may be marked as unresolved.",
            "CTEs, nested queries, wildcard projections and complex expressions should be reviewed manually.",
        ],
    }
