from utils.history import create_session, save_message, get_messages, get_sessions

# Create conversation
session_id = create_session("Sales Analysis")

# Save user message
save_message(session_id, "user", "Show top 5 products by revenue.")

# Save AI response
save_message(
    session_id,
    "assistant",
    "Here are the top 5 products.",
    "SELECT * FROM products LIMIT 5;",
)

# Retrieve messages
print("\nCHAT HISTORY:")

messages = get_messages(session_id)

for message in messages:
    print("\nRole:", message["role"])
    print("Content:", message["content"])
    print("SQL:", message["sql_query"])

print("\nSAVED SESSIONS:")
print(get_sessions())
