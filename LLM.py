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

async def generate_response(prompt):
    response = await asyncio.to_thread(
    client.chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "system", "content": prompts["system"]}, {"role": "user", "content": f"Marlene, respond to this message: {prompt}"}]
    ))
    return response.choices[0].message.content