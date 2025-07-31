from openai import OpenAI

client = OpenAI(
    base_url="http://0.0.0.0:4000/",
    api_key="sk-1234"
)

def call_llm(prompt: str, model: str = "kimi-k2-instruct", temperature: float = 0.1):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature
    )
    return response.choices[0].message.content