import openai

openai.api_key = "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"

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "system", "content": "You are a helpful assistant."},
              {"role": "user", "content": "Hello, can you hear me?"}]
)

print(response["choices"][0]["message"]["content"])
