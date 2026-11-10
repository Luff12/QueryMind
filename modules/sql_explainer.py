from modules.llm_engine import generate_response


def explain_sql(
    query, user_question=None, query_result=None, conversation_history=None
):

    history_text = ""

    if conversation_history:

        for message in conversation_history[-6:]:

            history_text += (
                f"\n{message.get('role', '').upper()}: "
                f"{message.get('content', '')}\n"
            )

    result_text = "No query results provided."

    if query_result is not None:

        if hasattr(query_result, "to_string"):

            result_text = query_result.to_string(index=False)

        else:

            result_text = str(query_result)

    prompt = f"""
You are QueryMind, an intelligent AI database analyst.

Your task is to explain the actual SQL query,
its purpose, and its results in simple English.

USER'S ORIGINAL QUESTION:
{user_question or "Not provided"}

CONVERSATION HISTORY:
{history_text}

EXECUTED SQL QUERY:
{query}

ACTUAL DATABASE RESULTS:
{result_text}

INSTRUCTIONS:

1. Explain what this particular query answers.
2. Connect the query to the user's original question.
3. Explain the important operations used in this query.
4. Explain how the database calculated the result.
5. Refer to actual values in the results when available.
6. Explain the findings and what they mean.
7. If the question is a follow-up, use the previous conversation
   to explain the context.
8. Do not give a generic SQL tutorial.
9. Do not explain unrelated SQL clauses.
10. Never invent results or values.

FORMAT:

### What this query answers
Explain the user's actual question.

### How the result was calculated
Explain the relevant logic in this particular query.

### Understanding the results
Interpret the actual returned data.

### Conclusion
Give a short, meaningful conclusion.

Use simple English and avoid unnecessary technical details.
"""

    return generate_response(prompt)


if __name__ == "__main__":

    query = """
    SELECT product_name, SUM(quantity) AS total_quantity
    FROM sales
    GROUP BY product_name;
    """

    print(explain_sql(query, user_question="Show total sales quantity."))
