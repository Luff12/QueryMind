from modules.llm_engine import generate_response
from database.schema import get_database_schema


def optimize_sql(
    query,
    user_question=None,
    query_plan=None,
):
    """
    Analyze SQL and suggest performance improvements.
    Does not execute or automatically replace the original query.
    """

    # Get database schema
    schema = get_database_schema()

    schema_text = ""

    for table_name, details in schema.items():
        columns = [
            f"{column['name']} ({column['type']})" for column in details["columns"]
        ]

        schema_text += f"\nTable: {table_name}\n" f"Columns: {', '.join(columns)}\n"

    # Convert query plan into readable text
    if query_plan is not None:
        plan_text = query_plan.to_string(index=False)
    else:
        plan_text = "Query execution plan unavailable."

    # Original question context
    question_text = user_question or "Not provided."

    prompt = f"""
You are an expert SQLite database performance engineer.

Analyze the SQL query and provide practical optimization suggestions.

USER QUESTION:
{question_text}

DATABASE SCHEMA:
{schema_text}

SQL QUERY:
{query}

SQLITE QUERY EXECUTION PLAN:
{plan_text}

INSTRUCTIONS:

1. Explain whether the query is reasonably efficient.
2. Identify table scans and possible index opportunities.
3. Identify unnecessary SELECT * usage.
4. Review JOIN, WHERE, GROUP BY and ORDER BY operations.
5. Suggest indexes only when they are justified by the query.
6. Provide an optimized SQL version if meaningful improvements are possible.
7. Preserve the original query's intended results.
8. Do not invent tables or columns.
9. Do not suggest destructive database operations.
10. If the query is already efficient, say so.

FORMAT YOUR RESPONSE:

### Performance Assessment
### Issues Identified
### Optimization Suggestions
### Optimized SQL
### Expected Benefits

Be specific to this query. Avoid generic SQL tutorials.

Do not claim that an optimization was benchmarked unless
actual benchmark measurements were provided.
"""

    response = generate_response(prompt)

    return response


if __name__ == "__main__":

    test_query = """
    SELECT *
    FROM sales
    WHERE customer_id = 1;
    """

    result = optimize_sql(
        query=test_query,
        user_question="Show sales made by customer 1.",
    )

    print("\nAI SQL OPTIMIZATION REPORT:\n")
    print(result)
