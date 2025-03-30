import os
import time
import json

class BotChannelData:
    def __init__(self):
        self.chat_history = []
        self.bot_reply_timestamp = time.time() - 9999
        self.bot_override_memory = ""
        self.bot_idletime = 120
        self.users = []

# Global dictionary for channel data
bot_data = {}

def export_config():
    config = []
    for channel_id, data in bot_data.items():
        config.append({
            "channel_id": channel_id,
            "bot_idletime": data.bot_idletime,
            "bot_override_memory": data.bot_override_memory,
            "chat_history": data.chat_history
        })
    with open('botsettings.json', 'w', encoding='utf-8') as file:
        json.dump(config, file, indent=2)

def import_config():
    try:
        if os.path.exists('botsettings.json'):
            with open('botsettings.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
                for item in data:
                    channel_id = item['channel_id']
                    if channel_id not in bot_data:
                        bot_data[channel_id] = BotChannelData()
                    bot_data[channel_id].bot_idletime = int(item.get('bot_idletime', 120))
                    bot_data[channel_id].bot_override_memory = item.get('bot_override_memory', "")
                    bot_data[channel_id].chat_history = item.get('chat_history', [])
    except Exception as e:
        print("Failed to load configuration:", e)

def append_history(channel_id, speaker, text):
    """Append a message to the conversation history and limit history to the last 20 messages."""
    if channel_id in bot_data:
        message = f"{speaker}: {text}"
        bot_data[channel_id].chat_history.append(message)
        if len(bot_data[channel_id].chat_history) > 20:
            bot_data[channel_id].chat_history = bot_data[channel_id].chat_history[-50:]

