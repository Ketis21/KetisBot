import discord
import time
import requests
import base64
import io
import urllib.request
from discord import app_commands
from bot_data import BotChannelData, bot_data, export_config, append_history
from payload import prepare_payload

# === Helper Functions ===

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user is an admin by comparing with admin_name."""
    return interaction.user.name.lower() == interaction.client.admin_name.lower()

def get_channel_data(channel_id):
    """Return BotChannelData for a given channel_id. Auto-whitelist if missing."""
    if channel_id not in bot_data:
        bot_data[channel_id] = BotChannelData()
    return bot_data[channel_id]

# === Admin Slash Commands ===

@app_commands.command(name="maxlen", description="Set the maximum response length (max 512).")
@app_commands.describe(max_length="New maximum response length (integer)")
async def maxlen(interaction: discord.Interaction, max_length: int):
    """Set the maximum response length (admin only)."""
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    if max_length > 512:
        await interaction.response.send_message("Maximum response length cannot exceed 512.", ephemeral=True)
        return
    interaction.client.config["maxlen"] = max_length
    await interaction.response.send_message(f"Maximum response length changed to {max_length}.")
    export_config()

@app_commands.command(name="idletime", description="Set the idle timeout for the bot.")
@app_commands.describe(idle_time="New idle timeout in seconds (integer)")
async def idletime(interaction: discord.Interaction, idle_time: int):
    """Set the idle timeout for the bot (admin only)."""
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    currchannel = get_channel_data(interaction.channel.id)
    currchannel.bot_idletime = idle_time
    await interaction.response.send_message(f"Idle timeout changed to {idle_time}.")
    export_config()

@app_commands.command(name="memory", description="Set the bot memory override. Use '0' to reset to default memory.")
@app_commands.describe(memory="Memory override text (or '0' to reset)")
async def memory(interaction: discord.Interaction, memory: str):
    """Set the bot's memory override (admin only). Use '0' to reset to default memory."""
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    currchannel = get_channel_data(interaction.channel.id)
    if memory.strip() == "0" or memory.strip() == "":
        currchannel.bot_override_memory = ""
        await interaction.response.send_message("Memory override cleared. Using default memory.")
    else:
        currchannel.bot_override_memory = memory
        await interaction.response.send_message(f"Memory override set to: {memory}")
    export_config()

# === User Slash Commands ===

@app_commands.command(name="reset", description="Reset the conversation history in this channel.")
async def reset(interaction: discord.Interaction):
    """Reset the conversation history in the current channel."""
    currchannel = get_channel_data(interaction.channel.id)
    currchannel.chat_history = []
    currchannel.bot_reply_timestamp = time.time() - 9999
    await interaction.response.send_message("Cleared bot conversation history in this channel.")
    export_config()

@app_commands.command(name="describe", description="Describe an uploaded image.")
@app_commands.describe(image="Image attachment to describe")
async def describe(interaction: discord.Interaction, image: discord.Attachment = None):
    """Describe an uploaded image using the bot's AI."""
    currchannel = get_channel_data(interaction.channel.id)
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
    export_config()

@app_commands.command(name="draw", description="Generate an image from a prompt with predefined settings.")
@app_commands.describe(
    orientation="Select image orientation",
    prompt="Prompt for image generation"
)
@app_commands.choices(orientation=[
    app_commands.Choice(name="Square", value="square"),
    app_commands.Choice(name="Portrait", value="portrait"),
    app_commands.Choice(name="Landscape", value="landscape")
])
async def draw(interaction: discord.Interaction, orientation: app_commands.Choice[str], prompt: str):
    """
    Generate an image from a given prompt using the bot's AI with a selected orientation.
    Predefined parameters for negative prompt, steps, and CFG scale are used.
    """
    currchannel = get_channel_data(interaction.channel.id)
    if interaction.client.busy.locked():
        await interaction.response.send_message("The bot is busy. Please try again later.", ephemeral=True)
        return

    # Predefined image generation parameters.
    negative_prompt = "low quality, blurry, deformed, bad anatomy"
    steps = 20
    cfg_scale = 7.0

    # Define resolution parameters for each orientation.
    resolutions = {
        "square": {"width": 320, "height": 448},
        "portrait": {"width": 384, "height": 384},
        "landscape": {"width": 448, "height": 320}
    }
    selected = resolutions.get(orientation.value, resolutions["square"])

    try:
        await interaction.response.defer()
        currchannel.bot_reply_timestamp = time.time()
        payload = prepare_payload(
            interaction.client.user.display_name,
            currchannel,
            interaction.client.config["maxlen"]
        )
        payload["prompt"] = prompt
        payload["width"] = selected["width"]
        payload["height"] = selected["height"]
        payload["negative_prompt"] = negative_prompt
        payload["steps"] = steps
        payload["cfg_scale"] = cfg_scale

        response = requests.post(interaction.client.imggen_endpoint, json=payload)
        if response.status_code == 200:
            result = response.json()["images"][0]
            file = discord.File(io.BytesIO(base64.b64decode(result)), filename='drawimage.png')
            await interaction.followup.send(file=file)
        else:
            await interaction.response.send_message("Sorry, the image generation failed!")
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}")
    export_config()

@app_commands.command(name="browse", description="Search the web and show a summary followed by results.")
@app_commands.describe(query="The search query")
async def browse(interaction: discord.Interaction, query: str):
    """
    Perform a web search, generate a summary from the results, then display the summary and results.
    The summary is generated by sending a prompt (constructed from the web search results)
    to the text generation API, sent as plain text, followed by an Embed displaying the search results.
    """
    try:
        await interaction.response.defer()
        search_payload = {"q": query}
        search_response = requests.post(interaction.client.websearch_endpoint, json=search_payload)
        if search_response.status_code != 200:
            await interaction.followup.send("Web search failed.", ephemeral=True)
            return

        results = search_response.json()
        if not results or not isinstance(results, list):
            await interaction.followup.send(f"No results found for '{query}'.", ephemeral=True)
            return

        prompt_text = f"Web search results for '{query}':\n"
        for result in results:
            title = result.get("title", "No Title")
            desc  = result.get("desc", "No Description")
            url   = result.get("url", "")
            prompt_text += f"- {title}: {desc} ({url})\n"

        currchannel = get_channel_data(interaction.channel.id)
        append_history(interaction.channel.id, interaction.user.display_name, prompt_text)

        # Generate summary using conversation history as context.
        gen_payload = prepare_payload(
            interaction.client.user.display_name,
            currchannel,
            interaction.client.config["maxlen"],
            user_display_name=interaction.user.display_name
        )
        gen_response = requests.post(interaction.client.submit_endpoint, json=gen_payload)
        if gen_response.status_code == 200:
            summary = gen_response.json()["results"][0]["text"]
            append_history(interaction.channel.id, interaction.client.user.display_name, summary)
            if len(summary) > 2000:
                chunks = [summary[i:i+2000] for i in range(0, len(summary), 2000)]
                for chunk in chunks:
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(summary)
        else:
            await interaction.followup.send("Failed to generate summary.", ephemeral=True)
            return

        # Build an Embed with the search results.
        results_embed = discord.Embed(title=f"Search results for: {query}", color=discord.Color.blue())
        for result in results:
            title = result.get("title", "No Title")
            desc  = result.get("desc", "No Description")
            url   = result.get("url", "")
            results_embed.add_field(name=title, value=f"{desc}\n[Read more]({url})", inline=False)

        await interaction.followup.send(embed=results_embed)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
    export_config()

# === Register Commands ===

def setup(app: discord.Client):
    """Register all slash commands to the client's command tree."""
    tree = app.tree
    tree.add_command(maxlen)
    tree.add_command(idletime)
    tree.add_command(memory)
    tree.add_command(reset)
    tree.add_command(describe)
    tree.add_command(draw)
    tree.add_command(browse)

