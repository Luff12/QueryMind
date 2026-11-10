from modules.llm_engine import generate_response


def detect_intent(question):

    prompt = f"""
You are an intent classifier for an AI SQL assistant.

Classify the user's question into exactly one category:

GENERATE_SQL
EXPLAIN_SQL
FOLLOW_UP
GENERAL

Rules:
- EXPLAIN_SQL: User asks to explain, describe or clarify
  the previous SQL query.
- FOLLOW_UP: User asks a follow-up database question
  referring to previous results.
- GENERATE_SQL: User asks a new database question.
- GENERAL: User asks a general question unrelated to
  database querying.

USER QUESTION:
{question}

Return only one category:
GENERATE_SQL, EXPLAIN_SQL, FOLLOW_UP, GENERAL
"""

    result = generate_response(prompt).strip().upper()

    allowed = ["GENERATE_SQL", "EXPLAIN_SQL", "FOLLOW_UP", "GENERAL"]

    for intent in allowed:
        if intent in result:
            return intent

    return "GENERATE_SQL"
