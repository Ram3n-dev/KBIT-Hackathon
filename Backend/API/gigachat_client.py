import os
import uuid
import json

import load_dotenv
import requests

load_dotenv()
# аутентификация
AUTH = os.getenv("GIGACHAT_AUTH")

TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"


class GigaChatClient:
    def __init__(self):
        self.token = None

    def get_token(self):
        rq_uid = str(uuid.uuid4())

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": rq_uid,
            "Authorization": f"Basic {AUTH}",
        }

        payload = {"scope": "GIGACHAT_API_PERS"}

        response = requests.post(
            TOKEN_URL,
            headers=headers,
            data=payload,
            verify=False
        )

        self.token = response.json()["access_token"]

    def chat(self, messages):

        if not self.token:
            self.get_token()

        payload = {
            "model": "GigaChat:latest",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 256
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        response = requests.post(
            CHAT_URL,
            headers=headers,
            data=json.dumps(payload),
            verify=False
        )

        return response.json()["choices"][0]["message"]["content"]
