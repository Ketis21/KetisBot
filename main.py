import discord
import os
import threading
import time
import base64
import io
import requests

from dotenv import load_dotenv
from discord.ext.voice_recv import VoiceRecvClient  # <-- ADDED IMPORT
from bot_data import BotChannelData, get_channel_data, bot_data, import_config, export_config, append_history
from payload import prepare_payload
import commands

# Load environment variables
load_dotenv()
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
config = {"maxlen": 512}

intents = discord.Intents.all()
client = discord.Client(
    intents=intents,
    voice_client_class=VoiceRecvClient  # <-- KEY CHANGE: Enable voice reception
)

# Attach CommandTree and global variables to the client
client.tree = discord.app_commands.CommandTree(client)
client.submit_endpoint = submit_endpoint
client.imggen_endpoint = f"{KAI_ENDPOINT}/sdapi/v1/txt2img"
client.websearch_endpoint = f"{KAI_ENDPOINT}/api/extra/websearch"
client.transcribe_endpoint = f"{KAI_ENDPOINT}/api/extra/transcribe"
client.tts_endpoint = f"{KAI_ENDPOINT}/api/extra/tts"
client.busy = threading.Lock()
client.config = config
client.admin_name = ADMIN_NAME

@client.event
async def on_ready():
    import_config()
    print(f"Logged in as {client.user}")
    commands.setup(client)
    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print("Error syncing commands:", e)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel_id = message.channel.id

    currchannel = get_channel_data(channel_id)

    # Track the user by display name
    if message.author.display_name not in currchannel.users:
        currchannel.users.append(message.author.display_name)

    # Append incoming message to history
    append_history(channel_id, message.author.display_name, message.clean_content)

    # Check if bot should respond
    if (time.time() - currchannel.bot_reply_timestamp < currchannel.bot_idletime or
        client.user in message.mentions or
        client.user.display_name.lower() in message.clean_content.lower()):
        if client.busy.acquire(blocking=False):
            try:
                async with message.channel.typing():
                    currchannel.bot_reply_timestamp = time.time()
                    payload = prepare_payload(
                        client.user.display_name,
                        currchannel,
                        client.config["maxlen"],
                        user_display_name=message.author.display_name
                    )
                    response = requests.post(submit_endpoint, json=payload)
                    if response.status_code == 200:
                        result = response.json()["results"][0]["text"]
                        append_history(channel_id, client.user.display_name, result)
                        if len(result) > 2000:
                            chunks = [result[i:i+2000] for i in range(0, len(result), 2000)]
                            for chunk in chunks:
                                await message.channel.send(chunk)
                        else:
                            await message.channel.send(result)
                        export_config()
                    else:
                        await message.channel.send("Sorry, the generation failed.")
            finally:
                client.busy.release()

try:
    client.run(BOT_TOKEN)
except discord.errors.LoginFailure:
    print("Bot failed to login to Discord")

