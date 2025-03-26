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
    """Whitelist the current channel (admin only)."""
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
    """Remove the current channel from the whitelist (admin only)."""
    if interaction.user.name.lower() != interaction.client.admin_name.lower():
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    channelid = interaction.channel.id
    if channelid in bot_data:
        del bot_data[channelid]
        await interaction.response.send_message("Channel removed from the whitelist.")
    else:
        await interaction.response.send_message("Channel is not whitelisted.")

@app_commands.command(name="maxlen", description="Set the maximum response length (max 512).")
@app_commands.describe(max_length="New maximum response length (integer)")
async def maxlen(interaction: discord.Interaction, max_length: int):
    """Set the maximum response length (admin only)."""
    if interaction.user.name.lower() != interaction.client.admin_name.lower():
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    if max_length > 512:
        await interaction.response.send_message("Maximum response length cannot exceed 512.", ephemeral=True)
        return
    interaction.client.config["maxlen"] = max_length
    await interaction.response.send_message(f"Maximum response length changed to {max_length}.")

@app_commands.command(name="idletime", description="Set the idle timeout for the bot.")
@app_commands.describe(idle_time="New idle timeout in seconds (integer)")
async def idletime(interaction: discord.Interaction, idle_time: int):
    """Set the idle timeout for the bot (admin only)."""
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
    """Save the current bot configuration (admin only)."""
    if interaction.user.name.lower() != interaction.client.admin_name.lower():
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    export_config()
    await interaction.response.send_message("Bot configuration saved.")

@app_commands.command(name="memory", description="Set the bot memory override.")
@app_commands.describe(memory="Memory override text")
async def memory(interaction: discord.Interaction, memory: str):
    """Set the bot's memory override (admin only)."""
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

# -----------------------------
# User Slash Commands
# -----------------------------

@app_commands.command(name="reset", description="Reset the conversation history in this channel.")
async def reset(interaction: discord.Interaction):
    """Reset the conversation history in the current channel."""
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
    """Describe an uploaded image using the bot's AI."""
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
    """Generate an image from a given prompt using the bot's AI."""
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
    """Continue an unfinished answer from the bot."""
    channelid = interaction.channel.id
    currchannel = bot_data.get(channelid)
    if not currchannel:
        await interaction.response.send_message("Channel is not whitelisted.", ephemeral=True)
        return
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
            # If the result is over 2000 characters, split it into chunks before sending
            if len(result) > 2000:
                chunks = [result[i:i+2000] for i in range(0, len(result), 2000)]
                for chunk in chunks:
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(result)
        else:
            await interaction.followup.send("Sorry, the continuation failed!")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")

@app_commands.command(name="browse", description="Search the web and show a summary followed by results.")
@app_commands.describe(query="The search query")
async def browse(interaction: discord.Interaction, query: str):
    try:
        # Ilmoitetaan käyttäjälle, että pyyntö on käynnissä
        await interaction.response.defer()

        # Suoritetaan web-haku käyttäen endpointia ja API:n vaatimaa payloadia (avain "q")
        search_payload = {"q": query}
        search_response = requests.post(interaction.client.websearch_endpoint, json=search_payload)
        if search_response.status_code != 200:
            await interaction.followup.send("Web search failed.", ephemeral=True)
            return

        results = search_response.json()
        if not results or not isinstance(results, list):
            await interaction.followup.send(f"No results found for '{query}'.", ephemeral=True)
            return

        # Luodaan prompt, joka sisältää web-haun tulokset
        prompt_text = f"Web search results for '{query}':\n"
        for result in results:
            title = result.get("title", "No Title")
            desc  = result.get("desc", "No Description")
            url   = result.get("url", "")
            prompt_text += f"- {title}: {desc} ({url})\n"

        # Lisätään prompt keskusteluhistoriaan käyttäjän viestinä
        channelid = interaction.channel.id
        if channelid not in bot_data:
            await interaction.followup.send("Channel is not whitelisted.", ephemeral=True)
            return
        append_history(channelid, interaction.user.display_name, prompt_text)
        currchannel = bot_data[channelid]

        # Luo generointipyynnön payload käyttäen päivitettyä keskusteluhistoriaa
        gen_payload = prepare_payload(
            interaction.client.user.display_name,
            currchannel,
            interaction.client.config["maxlen"],
            user_display_name=interaction.user.display_name
        )
        gen_response = requests.post(interaction.client.submit_endpoint, json=gen_payload)
        if gen_response.status_code == 200:
            summary = gen_response.json()["results"][0]["text"]
            append_history(channelid, interaction.client.user.display_name, summary)
            # Lähetetään tiivistelmä ensin normaalina tekstiviestinä (jaetaan osiin, jos yli 2000 merkkiä)
            if len(summary) > 2000:
                chunks = [summary[i:i+2000] for i in range(0, len(summary), 2000)]
                for chunk in chunks:
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(summary)
        else:
            await interaction.followup.send("Failed to generate summary.", ephemeral=True)
            return

        # Luodaan Embed-viesti hakutuloksista
        results_embed = discord.Embed(title=f"Search results for: {query}", color=discord.Color.blue())
        for result in results:
            title = result.get("title", "No Title")
            desc  = result.get("desc", "No Description")
            url   = result.get("url", "")
            results_embed.add_field(name=title, value=f"{desc}\n[Read more]({url})", inline=False)

        # Lähetetään hakutulokset embed-muodossa
        await interaction.followup.send(embed=results_embed)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

        
# -----------------------------
# Register Commands
# -----------------------------

def setup(app: discord.Client):
    """Register all slash commands to the client's command tree."""
    tree = app.tree  # Get the command tree from the client
    tree.add_command(whitelist)
    tree.add_command(blacklist)
    tree.add_command(maxlen)
    tree.add_command(idletime)
    tree.add_command(savesettings)
    tree.add_command(memory)
    tree.add_command(reset)
    tree.add_command(describe)
    tree.add_command(draw)
    tree.add_command(continue_response)
    tree.add_command(browse)

