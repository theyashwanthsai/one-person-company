import os
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def chat_completion(system, user, model="gpt-4o-mini", temperature=0.7, max_tokens=500):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ]
    
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt == 2:
                raise e
            time.sleep(2 ** attempt)
    

def chat_completion_json(system, user, model="gpt-4o-mini", temperature=0.7):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ]
    
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt == 2:
                raise e
            time.sleep(2 ** attempt)


def chat_with_history(messages, model="gpt-4o-mini", temperature=0.7, max_tokens=500):
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt == 2:
                raise e
            time.sleep(2 ** attempt)

