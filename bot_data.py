import os
import time
import json

class BotChannelData:
    def __init__(self):
        self.chat_history = []  # List to store recent chat messages (for context)
        self.bot_reply_timestamp = time.time() - 9999  # Timestamp for when the bot last replied (initialized to a past value)
        self.bot_idletime = 120  # Idle timeout in seconds (after which the bot may stop replying)
        self.bot_botloopcount = 0  # Counter for how many times the bot loop has executed (can be used for debugging)
        self.bot_override_memory = ""  # Optional override for the bot's memory prompt (set via command)
        self.bot_override_backend = ""  # Optional override for the bot's backend (set via command)

bot_data = {}  # Global dictionary to store BotChannelData for each channel (keyed by channel ID)

def export_config():
    """
    Exports the current configuration for each channel to a JSON file.
    This includes idle time and any override values for memory or backend.
    """
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
    """
    Imports the configuration from a JSON file (if it exists) and updates bot_data accordingly.
    This allows the bot to restore channel-specific settings on startup.
    """
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
    """
    Appends a message to the conversation history for the given channel.
    Keeps the history to the latest 20 messages.
    """
    if channelid in bot_data:
        currchannel = bot_data[channelid]
        msg = f"{author}: {text}"
        currchannel.chat_history.append(msg)
        if len(currchannel.chat_history) > 20:
            currchannel.chat_history.pop(0)
