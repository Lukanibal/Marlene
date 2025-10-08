from openai import OpenAI
import os

# Initialize OpenAI client
client = OpenAI(
    # If environment variables are not configured, replace with the Model Studio API Key: api_key="sk-xxx"
    api_key=os.getenv("QWEN_TOKEN"),
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

messages = [
        {"role":"user","content":"hi"}
    ]

completion = client.chat.completions.create(
    model="qwen-plus-latest",
    messages=messages,
    stream=True,
    top_p=0.8,
    temperature=0.7,
    extra_body={
        "enable_thinking": True,
        "thinking_budget": 40
    }
)

reasoning_content = ""  # Complete reasoning process
answer_content = ""  # Complete response
is_answering = False  # Whether entering the response phase
print("=" * 20 + "Thinking Process" + "=" * 20 )

for chunk in completion:
    if not chunk.choices:
        print("Usage:")
        print(chunk.usage)
        continue

    delta = chunk.choices[0].delta

    # Only collect reasoning content
    if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
        if not is_answering:
            print(delta.reasoning_content, end="", flush=True)
        reasoning_content += delta.reasoning_content

    # Received content, starting to respond
    if hasattr(delta, "content") and delta.content:
        if not is_answering:
            print("=" * 20 + "Complete Response" + "=" * 20)
            is_answering = True
        print(delta.content, end="", flush=True)
        answer_content += delta.content