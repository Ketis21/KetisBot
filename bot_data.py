import os
import time
import json

class BotChannelData:
    def __init__(self):
        self.chat_history = []
        self.bot_reply_timestamp = time.time() - 9999
        self.bot_hasfilter = True  # This flag is no longer used; NSFW filtering has been removed
        self.bot_idletime = 120
        self.bot_botloopcount = 0
        self.bot_override_memory = ""
        self.bot_override_backend = ""

bot_data = {}

def export_config():
    config = [
        {
            "key": key,
            "bot_idletime": data.bot_idletime,
            "bot_override_memory": data.bot_override_memory,
            "bot_override_backend": data.bot_override_backend
        }
        for key, data in bot_data.items()
    ]
    with open('botsettings.json', 'w') as file:
        json.dump(config, file, indent=2)

def import_config():
    try:
        if os.path.exists('botsettings.json'):
            with open('botsettings.json', 'r') as file:
                data = json.load(file)
                for d in data:
                    channelid = d['key']
                    if channelid not in bot_data:
                        bot_data[channelid] = BotChannelData()
                    bot_data[channelid].bot_idletime = int(d['bot_idletime'])
                    bot_data[channelid].bot_override_memory = d['bot_override_memory']
                    bot_data[channelid].bot_override_backend = d['bot_override_backend']
    except Exception as e:
        print("Failed to read settings:", e)

def append_history(channelid, author, text):
    if channelid in bot_data:
        currchannel = bot_data[channelid]
        msg = f"{author}: {text[:1000]}"
        currchannel.chat_history.append(msg)
        if len(currchannel.chat_history) > 20:
            currchannel.chat_history.pop(0)
