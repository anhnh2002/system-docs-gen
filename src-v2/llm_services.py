from openai import OpenAI

client = OpenAI(
    base_url="http://0.0.0.0:4000/",
    api_key="sk-1234"
)

#kimi-k2-instruct
#qwen3-coder-480b-a35b-instruct
#qwen3-235b-a22b-thinking-2507

def call_llm(prompt: str, model: str = "kimi-k2-instruct", temperature: float = 0.0):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature
    )
    return response.choices[0].message.content