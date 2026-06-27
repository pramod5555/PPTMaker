from dotenv import load_dotenv
import os
from openai import AzureOpenAI

load_dotenv()

endpoint = "https://custom-data-maya-resource.cognitiveservices.azure.com/"
model_name = "gpt-5.4"
deployment = "gpt-5.4"
api_version = "2024-12-01-preview"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)

response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "I am going to Paris, what should I see?",
        },
    ],
    model=deployment,
    max_completion_tokens=50,
)

print(response.choices[0].message.content)
