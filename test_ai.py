from ai_engine import generate_response

success, response = generate_response(
    "Explain artificial intelligence in simple words"
)

print("Success:", success)
print("Response:")
print(response)