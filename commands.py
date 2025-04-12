import discord
import time
import base64
import asyncio
import re
from io import BytesIO

import aiohttp
from discord import app_commands
from discord.ext import voice_recv
from pydub import AudioSegment

# Local modules
from bot_data import BotChannelData, get_channel_data, bot_data, export_config, append_history
from payload import prepare_payload

# === Asynchronous HTTP Helper Functions ===

async def async_post_bytes(url: str, data: dict, timeout: int = 60):
    """
    Perform an asynchronous POST request and return the raw bytes response.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=timeout) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Status code: {resp.status}, body: {text}")
                return await resp.read()
    except Exception as e:
        print(f"❌ async_post_bytes error: {e}")
        return None

async def async_post_json(url: str, data: dict, timeout: int = 60):
    """
    Perform an asynchronous POST request and return the JSON response.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=timeout) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Status code: {resp.status}, body: {text}")
                return await resp.json()
    except Exception as e:
        print(f"❌ async_post_json error: {e}")
        return None

async def async_get_bytes(url: str, timeout: int = 30, headers: dict = None):
    """
    Perform an asynchronous GET request and return the raw bytes response.
    """
    headers = headers or {'User-Agent': 'Mozilla/5.0'}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Status code: {resp.status}, body: {text}")
                return await resp.read()
    except Exception as e:
        print(f"❌ async_get_bytes error: {e}")
        return None

# === TTS Helper Function ===

async def speak_text(vc: discord.VoiceClient, text: str, client: discord.Client, channel_id: int):
    try:
        currchannel = get_channel_data(channel_id)
        selected_voice = getattr(currchannel, "tts_voice", "kobo")  # default fallback

        tts_response = await async_post_bytes(
            client.tts_endpoint,
            data={"input": text, "voice": selected_voice},
            timeout=120
        )

        if not tts_response:
            print("TTS failed: No response received.")
            return

        tts_audio = BytesIO(tts_response)
        tts_audio.seek(0)

        temp_path = "/tmp/kobold_tts.wav"
        with open(temp_path, "wb") as f:
            f.write(tts_audio.read())

        if not vc.is_playing():
            vc.play(discord.FFmpegPCMAudio(temp_path))
        else:
            print("🔇 Bot is already playing audio.")
    except Exception as e:
        print("TTS playback error:", e)

def is_admin(interaction: discord.Interaction) -> bool:
    """
    Check if a user has administrative privileges.
    (Replace with your own admin check as necessary.)
    """
    return interaction.user.guild_permissions.administrator

# === Admin Slash Commands ===

@app_commands.command(name="maxlen", description="Set the maximum response length (max 512).")
@app_commands.describe(max_length="New maximum response length (integer)")
async def maxlen(interaction: discord.Interaction, max_length: int):
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    if max_length > 512:
        await interaction.response.send_message("Maximum response length cannot exceed 512.", ephemeral=True)
        return
    interaction.client.config["maxlen"] = max_length
    export_config()
    await interaction.response.send_message(f"Maximum response length changed to {max_length}.")

@app_commands.command(name="idletime", description="Set the idle timeout for the bot.")
@app_commands.describe(idle_time="New idle timeout in seconds (integer)")
async def idletime(interaction: discord.Interaction, idle_time: int):
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    currchannel = get_channel_data(interaction.channel.id)
    currchannel.bot_idletime = idle_time
    export_config()
    await interaction.response.send_message(f"Idle timeout changed to {idle_time}.")

@app_commands.command(name="memory", description="Set the bot memory override. Use '0' to reset to default memory.")
@app_commands.describe(memory="Memory override text (or '0' to reset)")
async def memory(interaction: discord.Interaction, memory: str):
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
    
@app_commands.command(name="settts", description="Set the TTS provider and voice (admin only).")
@app_commands.choices(voice=[
    app_commands.Choice(name="Kobo", value="kobo"),
    app_commands.Choice(name="Cheery", value="cheery"),
    app_commands.Choice(name="Sleepy", value="sleepy"),
    app_commands.Choice(name="Shouty", value="shouty"),
    app_commands.Choice(name="Chatty", value="chatty"),
])
async def settts(interaction: discord.Interaction, voice: app_commands.Choice[str]):
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    currchannel = get_channel_data(interaction.channel.id)
    currchannel.tts_voice = voice.value
    export_config()
    await interaction.response.send_message(f"TTS voice set to **{voice.name}**.")
    export_config()

# === User Slash Commands ===

@app_commands.command(name="reset", description="Reset the conversation history in this channel.")
async def reset(interaction: discord.Interaction):
    currchannel = get_channel_data(interaction.channel.id)
    currchannel.chat_history = []
    currchannel.bot_reply_timestamp = time.time() - 9999
    export_config()
    await interaction.response.send_message("Cleared bot conversation history in this channel.")
    export_config()

@app_commands.command(name="describe", description="Describe an uploaded image.")
@app_commands.describe(image="Image attachment to describe")
async def describe(interaction: discord.Interaction, image: discord.Attachment = None):
    if not image:
        await interaction.response.send_message("No image was provided.", ephemeral=True)
        return

    currchannel = get_channel_data(interaction.channel.id)
    try:
        await interaction.response.defer()

        # Download the image using aiohttp
        img_bytes = await async_get_bytes(image.url)
        if img_bytes is None:
            await interaction.followup.send("Failed to download the image.", ephemeral=True)
            return
        uploadedimg = base64.b64encode(img_bytes).decode('utf-8')

        currchannel.bot_reply_timestamp = time.time()
        payload = prepare_payload(
            interaction.client.user.display_name, currchannel, interaction.client.config["maxlen"]
        )
        payload["images"] = [uploadedimg]
        payload["prompt"] = "### Instruction:\nPlease describe the image in detail.\n\n### Response:\n"

        resp = await async_post_json(interaction.client.submit_endpoint, data=payload)
        if resp is not None:
            result = resp["results"][0]["text"]
            await interaction.followup.send(f"Image Description: {result}")
        else:
            await interaction.followup.send("Sorry, the image transcription failed!")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")
    export_config()

@app_commands.command(name="draw", description="Generate an image from a prompt with predefined settings.")
@app_commands.describe(orientation="Select image orientation", prompt="Prompt for image generation")
@app_commands.choices(orientation=[
    app_commands.Choice(name="Square", value="square"),
    app_commands.Choice(name="Portrait", value="portrait"),
    app_commands.Choice(name="Landscape", value="landscape")
])
async def draw(interaction: discord.Interaction, orientation: app_commands.Choice[str], prompt: str):
    currchannel = get_channel_data(interaction.channel.id)
    if interaction.client.busy.locked():
        await interaction.response.send_message("The bot is busy. Please try again later.", ephemeral=True)
        return

    resolutions = {
        "square": {"width": 384, "height": 384},
        "portrait": {"width": 320, "height": 448},
        "landscape": {"width": 448, "height": 320}
    }
    selected = resolutions.get(orientation.value, resolutions["square"])

    negative_prompt = "low quality, blurry, deformed, bad anatomy"
    steps = 20
    cfg_scale = 7.0

    try:
        await interaction.response.defer()
        currchannel.bot_reply_timestamp = time.time()
        payload = prepare_payload(
            interaction.client.user.display_name, currchannel, interaction.client.config["maxlen"]
        )
        payload.update({
            "prompt": prompt,
            "width": selected["width"],
            "height": selected["height"],
            "negative_prompt": negative_prompt,
            "steps": steps,
            "cfg_scale": cfg_scale
        })

        resp = await async_post_json(interaction.client.imggen_endpoint, data=payload)
        if resp is not None:
            result = resp["images"][0]
            file = discord.File(BytesIO(base64.b64decode(result)), filename='drawimage.png')
            await interaction.followup.send(file=file)
        else:
            await interaction.response.send_message("Sorry, the image generation failed!")
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}")
    export_config()

@app_commands.command(name="search", description="Search the web and show a summary followed by results.")
@app_commands.describe(query="The search query")
async def search(interaction: discord.Interaction, query: str):
    try:
        await interaction.response.defer()

        search_payload = {"q": query}
        search_resp = await async_post_json(interaction.client.websearch_endpoint, data=search_payload)
        if not search_resp:
            await interaction.followup.send("Web search failed.", ephemeral=True)
            return

        # Expecting search_resp to be a list of results
        results = search_resp
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

        gen_payload = prepare_payload(
            interaction.client.user.display_name,
            currchannel,
            interaction.client.config["maxlen"],
            user_display_name=interaction.user.display_name
        )

        gen_resp = await async_post_json(interaction.client.submit_endpoint, data=gen_payload)
        if gen_resp is not None:
            summary = gen_resp["results"][0]["text"]
            append_history(interaction.channel.id, interaction.client.user.display_name, summary)
            if len(summary) > 2000:
                for chunk in (summary[i:i+2000] for i in range(0, len(summary), 2000)):
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(summary)
        else:
            await interaction.followup.send("Failed to generate summary.", ephemeral=True)
            return

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

# === Voice Commands ===

@app_commands.command(name="joinvoice", description="Join the voice channel and start continuous listening.")
async def joinvoice(interaction: discord.Interaction):
    """
    Command for the bot to join the user's voice channel and start continuous listening for trigger phrases.
    """
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You are not connected to a voice channel.", ephemeral=True)
        return

    try:
        vc = interaction.guild.voice_client
        if not vc:
            # Connect using the voice receiver client from discord-ext-voice-recv
            vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        await interaction.response.send_message(f"Joined voice channel: **{interaction.user.voice.channel.name}**")

        if not hasattr(vc, "voice_listener_task"):
            vc.voice_listener_task = asyncio.create_task(
                voice_listener(vc, interaction.channel, interaction.client)
            )
    except Exception as e:
        await interaction.response.send_message(f"Failed to join voice channel: {e}", ephemeral=True)
    export_config()

async def voice_listener(vc: discord.VoiceClient, text_channel: discord.TextChannel, client: discord.Client):
    """
    Continuously listens to the voice channel, buffers audio, detects silence,
    and processes transcriptions for trigger phrases. When detected, sends
    commands to generate a bot response.
    """
    audio_buffer = BytesIO()
    buffer_lock = asyncio.Lock()
    last_packet_time = time.time()
    last_speaker = None
    loop = asyncio.get_running_loop()

    bot_name = client.user.display_name
    maxlen = client.config["maxlen"]
    submit_endpoint = client.submit_endpoint
    transcribe_endpoint = client.transcribe_endpoint
    tts_endpoint = client.tts_endpoint

    def callback(user: discord.Member, packet: voice_recv.VoiceData):
        nonlocal last_packet_time
        try:
            asyncio.run_coroutine_threadsafe(write_audio(packet.pcm, user), loop)
            last_packet_time = time.time()
        except Exception as e:
            print(f"Error scheduling audio write: {e}")

    async def write_audio(pcm_data: bytes, user: discord.Member):
        nonlocal audio_buffer, last_packet_time, last_speaker
        async with buffer_lock:
            try:
                audio_buffer.write(pcm_data)
                last_packet_time = time.time()
                last_speaker = user
            except Exception as e:
                print(f"Error writing audio: {e}")

    vc.listen(voice_recv.BasicSink(callback))
    SILENCE_TIMEOUT = 1.2  # seconds of silence to trigger processing

    while True:
        await asyncio.sleep(0.5)
        current_time = time.time()
        if current_time - last_packet_time < SILENCE_TIMEOUT:
            continue

        async with buffer_lock:
            if audio_buffer.getbuffer().nbytes == 0:
                continue

            audio = AudioSegment(
                data=audio_buffer.getvalue(),
                sample_width=2,
                frame_rate=48000,
                channels=2
            ).set_channels(1).set_frame_rate(16000).set_sample_width(2).normalize(headroom=0.5)

            # Reset the audio buffer
            audio_buffer.truncate(0)
            audio_buffer.seek(0)

        # Export the audio to WAV format
        wav_buffer = BytesIO()
        audio.export(wav_buffer, format="wav", codec="pcm_s16le", parameters=["-ar", "16000", "-ac", "1"])
        base64_audio = base64.b64encode(wav_buffer.getvalue()).decode('utf-8')

        transcribe_payload = {
            "audio_data": base64_audio,
            "langcode": "en",
            "suppress_non_speech": True,
            "prompt": f"The user is saying commands to a voice assistant named '{bot_name}'."
        }

        try:
            trans_response = await async_post_json(transcribe_endpoint, data=transcribe_payload, timeout=120)
            if not trans_response:
                print("Transcription API failed.")
                continue

            transcribed_text = trans_response.get("text", "").strip().lower()
            if not transcribed_text:
                continue

            # Check for the trigger phrase (e.g., "hey bot")
            if re.search(r"\b(hey[, ]+)?bot\b", transcribed_text, re.IGNORECASE):
                print("✅ Trigger phrase matched.")
                channel_id = text_channel.id
                speaker_name = last_speaker.display_name if last_speaker else "Voice User"

                # Update channel data with the speaker
                currchannel = get_channel_data(channel_id)
                if speaker_name not in currchannel.users:
                    currchannel.users.append(speaker_name)
                append_history(channel_id, speaker_name, transcribed_text)

                currchannel.bot_reply_timestamp = time.time()
                bot_payload = prepare_payload(bot_name, currchannel, maxlen)
                bot_resp = await async_post_json(submit_endpoint, data=bot_payload)
                if bot_resp is not None:
                    bot_reply = bot_resp["results"][0]["text"]
                    append_history(channel_id, bot_name, bot_reply)
                    # Speak the bot's reply in the voice channel
                    await speak_text(vc, bot_reply, client, channel_id=text_channel.id)
                else:
                    print(f"Voice transcription: {transcribed_text} - Bot failed to respond.")
        except Exception as e:
            print("Error during transcription:", e)

        export_config()
        
@app_commands.command(name="leavevoice", description="Leave the voice channel and stop listening.")
async def leavevoice(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and hasattr(vc, "voice_listener_task"):
        vc.voice_listener_task.cancel()
    if vc:
        await vc.disconnect()
    await interaction.response.send_message("Left the voice channel.")

# === Register Commands ===

def setup(app: discord.Client):
    """
    Register all slash commands to the client's command tree.
    """
    tree = app.tree
    tree.add_command(maxlen)
    tree.add_command(idletime)
    tree.add_command(memory)
    tree.add_command(settts)
    tree.add_command(reset)
    tree.add_command(describe)
    tree.add_command(draw)
    tree.add_command(search)
    tree.add_command(joinvoice)
    tree.add_command(leavevoice)

