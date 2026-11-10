from database.schema import get_database_schema
from modules.llm_engine import generate_response
from database.multi_db import get_active_dialect

MAX_CORRECTION_ATTEMPTS = 3


def correct_sql(
    original_sql, error_message, user_question=None, conversation_history=None
):

    # ======================================
    # DATABASE SCHEMA
    # ======================================

    schema = get_database_schema()
    dialect = get_active_dialect()

    schema_text = ""

    for table_name, details in schema.items():

        schema_text += f"\nTable: {table_name}\n"

        schema_text += "Columns:\n"

        for column in details["columns"]:

            schema_text += f"- {column['name']} ({column['type']})\n"

        for fk in details["foreign_keys"]:

            schema_text += (
                f"- Foreign key: {fk['column']} references "
                f"{fk['references_table']}."
                f"{fk['references_column']}\n"
            )

    # ======================================
    # CONVERSATION CONTEXT
    # ======================================

    history_text = ""

    if conversation_history:

        for message in conversation_history[-6:]:

            history_text += (
                f"\n{message.get('role', '').upper()}: "
                f"{message.get('content', '')}\n"
            )

    # ======================================
    # CORRECTION PROMPT
    # ======================================

    prompt = f"""
You are an expert {dialect} SQL debugging assistant.

Your task is to correct an invalid SQL query.

USER QUESTION:
{user_question or "Not provided"}

DATABASE SCHEMA:
{schema_text}

CONVERSATION HISTORY:
{history_text}

INCORRECT SQL QUERY:
{original_sql}

DATABASE ERROR:
{error_message}

INSTRUCTIONS:

1. Identify the actual cause of the SQL error.
2. Correct the SQL query.
3. Use only tables and columns in the schema.
4. Verify JOIN relationships.
5. Use valid {dialect} syntax.
6. Preserve the original query's intended purpose.
7. Generate only SELECT statements.
8. Never generate INSERT, UPDATE, DELETE, DROP,
   ALTER, CREATE or other modification statements.
9. Do not invent database columns.
10. Do not include explanations.
11. Return only the corrected SQL query.
12. Do not include Markdown code blocks.

CORRECTED SQL:
"""

    response = generate_response(prompt)

    if response.startswith("ERROR:"):
        return response

    # ======================================
    # CLEAN RESPONSE
    # ======================================

    response = response.replace("```sql", "")
    response = response.replace("```SQL", "")
    response = response.replace("```", "")

    corrected_query = response.strip()

    if not corrected_query:
        return "ERROR: AI returned an empty SQL query."

    return corrected_query


if __name__ == "__main__":

    incorrect_sql = """
    SELECT product_name, price
    FROM products
    WHERE unknown_column > 1000;
    """

    error = "no such column: unknown_column"

    corrected = correct_sql(
        incorrect_sql, error, user_question="Show products costing more than 1000."
    )

    print("\nORIGINAL SQL:")
    print(incorrect_sql)

    print("\nCORRECTED SQL:")
    print(corrected)
