import discord
import time
import requests
import base64
import io
import urllib.request
from discord import app_commands
from bot_data import BotChannelData, bot_data, export_config, append_history
from payload import prepare_payload

# -----------------------------
# Admin Slash Commands
# -----------------------------

@app_commands.command(name="whitelist", description="Whitelist the current channel.")
async def whitelist(interaction: discord.Interaction):
    if interaction.user.name.lower() != interaction.client.admin_name.lower():
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    channelid = interaction.channel.id
    if channelid not in bot_data:
        bot_data[channelid] = BotChannelData()
        await interaction.response.send_message("Channel added to the whitelist. Use slash commands to interact.")
    else:
        await interaction.response.send_message("Channel already whitelisted.")

@app_commands.command(name="blacklist", description="Remove the current channel from the whitelist.")
async def blacklist(interaction: discord.Interaction):
    if interaction.user.name.lower() != interaction.client.admin_name.lower():
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    channelid = interaction.channel.id
    if channelid in bot_data:
        del bot_data[channelid]
        await interaction.response.send_message("Channel removed from the whitelist.")
    else:
        await interaction.response.send_message("Channel is not whitelisted.")

@app_commands.command(name="maxlen", description="Set the maximum response length.")
@app_commands.describe(max_length="New maximum response length (integer)")
async def maxlen(interaction: discord.Interaction, max_length: int):
    if interaction.user.name.lower() != interaction.client.admin_name.lower():
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    if max_length > 200:
        await interaction.response.send_message("Maximum response length cannot exceed 200.", ephemeral=True)
        return
    interaction.client.config["maxlen"] = max_length
    await interaction.response.send_message(f"Maximum response length changed to {max_length}.")


@app_commands.command(name="idletime", description="Set the idle timeout for the bot.")
@app_commands.describe(idle_time="New idle timeout in seconds (integer)")
async def idletime(interaction: discord.Interaction, idle_time: int):
    if interaction.user.name.lower() != interaction.client.admin_name.lower():
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    channelid = interaction.channel.id
    currchannel = bot_data.get(channelid)
    if currchannel:
        currchannel.bot_idletime = idle_time
        await interaction.response.send_message(f"Idle timeout changed to {idle_time}.")
    else:
        await interaction.response.send_message("Channel is not whitelisted.")

@app_commands.command(name="savesettings", description="Save the bot configuration.")
async def savesettings(interaction: discord.Interaction):
    if interaction.user.name.lower() != interaction.client.admin_name.lower():
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    export_config()
    await interaction.response.send_message("Bot configuration saved.")

@app_commands.command(name="memory", description="Set the bot memory override.")
@app_commands.describe(memory="Memory override text")
async def memory(interaction: discord.Interaction, memory: str):
    if interaction.user.name.lower() != interaction.client.admin_name.lower():
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    channelid = interaction.channel.id
    currchannel = bot_data.get(channelid)
    if currchannel:
        currchannel.bot_override_memory = memory
        await interaction.response.send_message(f"Memory override set to: {memory}")
    else:
        await interaction.response.send_message("Channel is not whitelisted.")

@app_commands.command(name="backend", description="Set the bot backend override.")
@app_commands.describe(backend="Backend override text")
async def backend(interaction: discord.Interaction, backend: str):
    if interaction.user.name.lower() != interaction.client.admin_name.lower():
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    channelid = interaction.channel.id
    currchannel = bot_data.get(channelid)
    if currchannel:
        currchannel.bot_override_backend = backend
        await interaction.response.send_message("Bot backend override set.")
    else:
        await interaction.response.send_message("Channel is not whitelisted.")

# -----------------------------
# User Slash Commands
# -----------------------------

@app_commands.command(name="sleep", description="Put the bot to sleep in this channel.")
async def sleep(interaction: discord.Interaction):
    channelid = interaction.channel.id
    currchannel = bot_data.get(channelid)
    if currchannel:
        currchannel.bot_reply_timestamp = time.time() - 9999
        await interaction.response.send_message("Entering sleep mode. Use any slash command to wake me up again.")
    else:
        await interaction.response.send_message("Channel is not whitelisted.", ephemeral=True)

@app_commands.command(name="status", description="Get the bot status in this channel.")
async def status(interaction: discord.Interaction):
    channelid = interaction.channel.id
    currchannel = bot_data.get(channelid)
    if currchannel:
        lastreq = int(time.time() - currchannel.bot_reply_timestamp)
        lockmsg = "busy generating a response" if interaction.client.busy.locked() else "awaiting any new requests"
        await interaction.response.send_message(
            f"I am currently online and {lockmsg}. The last request from this channel was {lastreq} seconds ago."
        )
    else:
        await interaction.response.send_message("Channel is not whitelisted.", ephemeral=True)

@app_commands.command(name="reset", description="Reset the conversation history in this channel.")
async def reset(interaction: discord.Interaction):
    channelid = interaction.channel.id
    currchannel = bot_data.get(channelid)
    if currchannel:
        currchannel.chat_history = []
        currchannel.bot_reply_timestamp = time.time() - 9999
        await interaction.response.send_message("Cleared bot conversation history in this channel.")
    else:
        await interaction.response.send_message("Channel is not whitelisted.", ephemeral=True)

@app_commands.command(name="describe", description="Describe an uploaded image.")
@app_commands.describe(image="Image attachment to describe")
async def describe(interaction: discord.Interaction, image: discord.Attachment = None):
    channelid = interaction.channel.id
    currchannel = bot_data.get(channelid)
    if not currchannel:
        await interaction.response.send_message("Channel is not whitelisted.", ephemeral=True)
        return
    if image is None:
        await interaction.response.send_message("No image was provided.", ephemeral=True)
        return
    try:
        await interaction.response.defer()
        req = urllib.request.Request(image.url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            uploadedimg = base64.b64encode(response.read()).decode('utf-8')
        currchannel.bot_reply_timestamp = time.time()
        payload = prepare_payload(
            interaction.client.user.display_name,
            currchannel,
            interaction.client.config["maxlen"]
        )
        payload["images"] = [uploadedimg]
        payload["prompt"] = "### Instruction:\nPlease describe the image in detail.\n\n### Response:\n"
        response = requests.post(interaction.client.submit_endpoint, json=payload)
        if response.status_code == 200:
            result = response.json()["results"][0]["text"]
            await interaction.followup.send(f"Image Description: {result}")
        else:
            await interaction.followup.send("Sorry, the image transcription failed!")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")

@app_commands.command(name="draw", description="Generate an image from a prompt.")
@app_commands.describe(prompt="Prompt for image generation")
async def draw(interaction: discord.Interaction, prompt: str):
    channelid = interaction.channel.id
    currchannel = bot_data.get(channelid)
    if not currchannel:
        await interaction.response.send_message("Channel is not whitelisted.", ephemeral=True)
        return
    if interaction.client.busy.locked():
        await interaction.response.send_message("The bot is busy. Please try again later.", ephemeral=True)
        return
    try:
        await interaction.response.defer()
        currchannel.bot_reply_timestamp = time.time()
        payload = prepare_payload(
            interaction.client.user.display_name,
            currchannel,
            interaction.client.config["maxlen"]
        )
        payload["prompt"] = prompt
        response = requests.post(interaction.client.imggen_endpoint, json=payload)
        if response.status_code == 200:
            result = response.json()["images"][0]
            file = discord.File(io.BytesIO(base64.b64decode(result)), filename='drawimage.png')
            await interaction.followup.send(file=file)
        else:
            await interaction.followup.send("Sorry, the image generation failed!")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")

@app_commands.command(name="continue", description="Continue the unfinished answer.")
async def continue_response(interaction: discord.Interaction):
    channelid = interaction.channel.id
    currchannel = bot_data.get(channelid)
    if not currchannel:
        await interaction.response.send_message("Channel is not whitelisted.", ephemeral=True)
        return

    # Check if the last message in the chat history is from the bot.
    if not currchannel.chat_history or not currchannel.chat_history[-1].startswith(interaction.client.user.display_name):
        await interaction.response.send_message("No unfinished answer to continue.", ephemeral=True)
        return

    if interaction.client.busy.locked():
        await interaction.response.send_message("The bot is busy. Please try again later.", ephemeral=True)
        return

    try:
        await interaction.response.defer()
        currchannel.bot_reply_timestamp = time.time()
        payload = prepare_payload(
            interaction.client.user.display_name,
            currchannel,
            interaction.client.config["maxlen"]
        )
        response = requests.post(interaction.client.submit_endpoint, json=payload)
        if response.status_code == 200:
            result = response.json()["results"][0]["text"]
            append_history(channelid, interaction.client.user.display_name, result)
            await interaction.followup.send(result)
        else:
            await interaction.followup.send("Sorry, the continuation failed!")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")

# -----------------------------
# New Web Browsing Slash Command
# -----------------------------
import json  # Import json for debugging

@app_commands.command(name="browse", description="Search the internet using KoboldCpp's websearch.")
@app_commands.describe(query="The search query")
async def browse(interaction: discord.Interaction, query: str):
    try:
        await interaction.response.defer()
        # Use the expected payload format with key "q"
        payload = {"q": query}
        response = requests.post(interaction.client.websearch_endpoint, json=payload)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                if not data:
                    await interaction.followup.send(f"No results found for '{query}'.")
                    return
                # Format the results nicely
                formatted_results = "\n\n".join(
                    f"**{item.get('title', 'No Title')}**\n{item.get('desc', 'No Description')}\n<{item.get('url', '')}>"
                    for item in data
                )
                await interaction.followup.send(f"Search results for '{query}':\n\n{formatted_results}")
            else:
                await interaction.followup.send(f"Unexpected response format: {data}", ephemeral=True)
        else:
            await interaction.followup.send("Sorry, the web search failed!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)


# -----------------------------
# Register Commands
# -----------------------------
def setup(app: discord.Client):
    tree = app.tree
    tree.add_command(whitelist)
    tree.add_command(blacklist)
    tree.add_command(maxlen)
    tree.add_command(idletime)
    tree.add_command(savesettings)
    tree.add_command(memory)
    tree.add_command(backend)
    tree.add_command(sleep)
    tree.add_command(status)
    tree.add_command(reset)
    tree.add_command(describe)
    tree.add_command(draw)
    tree.add_command(continue_response)
    tree.add_command(browse)
