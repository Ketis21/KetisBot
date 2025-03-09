import discord
import os
import threading
import time
import base64
import io
import requests

from dotenv import load_dotenv
from bot_data import BotChannelData, bot_data, import_config, append_history
from payload import prepare_payload
import commands  # Import the slash commands module

# Load environment variables from the .env file
load_dotenv()

# Ensure required environment variables are set
required_vars = ["KAI_ENDPOINT", "BOT_TOKEN", "ADMIN_NAME"]
missing = [var for var in required_vars if os.getenv(var) is None]
if missing:
    print("Missing .env variables:", missing, "Cannot continue.")
    exit()

# Set up endpoints and configuration
KAI_ENDPOINT = os.getenv("KAI_ENDPOINT")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_NAME = os.getenv("ADMIN_NAME")

submit_endpoint = f"{KAI_ENDPOINT}/api/v1/generate"
imggen_endpoint = f"{KAI_ENDPOINT}/sdapi/v1/txt2img"

# Global configuration dictionary (e.g. max response length)
config = {"maxlen": 200}

intents = discord.Intents.all()
client = discord.Client(intents=intents)

# Attach a CommandTree to the client for slash commands
client.tree = discord.app_commands.CommandTree(client)

# Attach global variables to the client for use in slash command handlers
client.submit_endpoint = submit_endpoint
client.imggen_endpoint = imggen_endpoint
client.websearch_endpoint = f"{KAI_ENDPOINT}/api/extra/websearch"
client.busy = threading.Lock()
client.config = config
client.admin_name = ADMIN_NAME

@client.event
async def on_ready():
    import_config()
    print(f"Logged in as {client.user}")
    # Setup slash commands from the commands.py module
    commands.setup(client)
    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print("Error syncing commands:", e)

@client.event
async def on_message(message):
    # Process non-slash command messages as before
    if message.author == client.user:
        return
    channelid = message.channel.id
    if channelid not in bot_data:
        return

    append_history(channelid, message.author.display_name, message.clean_content)
    currchannel = bot_data[channelid]

    if (time.time() - currchannel.bot_reply_timestamp < currchannel.bot_idletime or
        client.user in message.mentions or
        client.user.display_name.lower() in message.clean_content.lower()):
        if client.busy.acquire(blocking=False):
            try:
                async with message.channel.typing():
                    currchannel.bot_reply_timestamp = time.time()
                    payload = prepare_payload(client.user.display_name, currchannel, client.config["maxlen"])
                    response = requests.post(submit_endpoint, json=payload)
                    if response.status_code == 200:
                        result = response.json()["results"][0]["text"]
                        append_history(channelid, client.user.display_name, result)
                        await message.channel.send(result)
            finally:
                client.busy.release()

try:
    client.run(BOT_TOKEN)
except discord.errors.LoginFailure:
    print("Bot failed to login to Discord")
