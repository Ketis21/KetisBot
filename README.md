# KetisBot

KetisBot is a powerful, voice-enabled AI chatbot for Discord. It leverages KoboldCpp for language generation, supports Stable Diffusion for image creation, performs web searches, and now offers voice interaction and text-to-speech playback in real-time.

## Features

- 🤖 **AI-generated responses** using KoboldCpp
- 🎤 **Voice interaction** with speech recognition and TTS
- 🌐 **Web search** capability
- 🎨 **Image generation** via Stable Diffusion
- ⚙️ **Customizable settings** for admins
- 🛠 **Slash commands** for easy interaction

## Installation

### Prerequisites

- [KoboldCpp](https://github.com/LostRuins/koboldcpp)
- Python 3.10+
- ffmpeg installed and in system PATH (required for voice and TTS)
- Discord bot token

### Setup Instructions

1. **Clone the repository:**
   ```sh
   git clone https://github.com/Ketis21/KetisBot.git
   cd KetisBot
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Create a ****`.env`**** file** in the project directory and add the following:
   ```ini
   BOT_TOKEN=your_discord_bot_token
   KAI_ENDPOINT=your_koboldcpp_api_url
   ADMIN_NAME=your_discord_username
   ```
4. **Run the bot:**
   ```sh
   python main.py
   ```

## Commands

Interact with the bot by **mentioning** it (e.g., `@KetisBot your message`).

### User Commands

- `/search [query]` – Search the internet
- `/draw [orientation] [prompt]` – Generate an image
- `/describe [image]` – Describe an uploaded image
- `/reset` – Clear chat history
- `/joinvoice` – Join your voice channel and listen
- `/leavevoice` – Leave the current voice channel

### Admin Commands

- `/maxlen [value]` – Set response length (max 512)
- `/idletime [value]` – Set bot idle timeout
- `/memory [text]` – Override bot memory
- `/settts [voice]` – Change TTS voice

## License

This project is licensed under the AGPL-3.0 license.

---
