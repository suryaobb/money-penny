import requests

class TelegramClient:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, text):
        url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
        return requests.post(url, json={'chat_id': self.chat_id, 'text': text}).json()
