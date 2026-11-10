from modules.sql_generator import generate_sql

history = [
    {"role": "user", "content": "Show the top 5 products by revenue."},
    {"role": "assistant", "content": "Here are the top 5 products."},
]

question = "Which one has the highest price?"

sql = generate_sql(question, conversation_history=history)

print("\nFOLLOW-UP QUESTION:")
print(question)

print("\nGENERATED SQL:")
print(sql)
