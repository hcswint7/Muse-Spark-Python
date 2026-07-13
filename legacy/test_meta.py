import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("MODEL_API_KEY")
if not api_key:
    raise ValueError("MODEL_API_KEY is missing. Put it in your .env file.")

url = "https://api.meta.ai/v1/responses"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

payload = {
    "model": "muse-spark-1.1",
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Write a haiku about Meta."
                }
            ]
        }
    ],
    "stream": False,
}

response = requests.post(url, headers=headers, json=payload, timeout=60)

print("STATUS:", response.status_code)
print(response.text)
