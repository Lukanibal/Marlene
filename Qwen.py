import os
from openai import OpenAI
from dotenv import load_dotenv
from prompts import prompts
import asyncio

load_dotenv()



client = OpenAI(
    # The API keys for the Singapore and Beijing regions are different. To obtain an API key: https://www.alibabacloud.com/help/en/model-studio/get-api-key
    api_key=os.getenv("QWEN_TOKEN"), 
    # The following is the base_url for the Singapore region. If you use a model in the Beijing region, replace the base_url with https://dashscope.aliyuncs.com/compatible-mode/v1
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)

async def generate_response(prompt, think=False, chat=[]):
    if think:
        completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompt}
        ] + chat,
        stream=True,
        top_p=0.8,
        temperature=0.7,
        extra_body={
            "enable_thinking": True,
            "thinking_budget": 100
        }
    )

        reasoning_content = ""  # Complete reasoning process
        answer_content = ""  # Complete response
        is_answering = False  # Whether entering the response phase

        print("=" * 20 + "Thinking Process" + "=" * 20)

        for chunk in completion:
            if not chunk.choices:
                print("Usage:")
                print(chunk.usage)
                continue

            delta = chunk.choices[0].delta

            # Collect reasoning content
            if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                if not is_answering:
                    print(delta.reasoning_content, end="", flush=True)
                reasoning_content += delta.reasoning_content

            # Collect the final response content
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    print("=" * 20 + "Complete Response" + "=" * 20)
                    is_answering = True
                print(delta.content, end="", flush=True)
                answer_content += delta.content

        return answer_content

    else:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "system", "content": prompts["system"]}, {"role": "user", "content": f"Marlene, respond to this message: {prompt}"}]
        )
        return response.choices[0].message.content