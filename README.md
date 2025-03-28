# KetisBot

KetisBot is a powerful AI chatbot for Discord, utilizing **KoboldCpp** for text generation, **web browsing**, and **image creation**. It supports **slash commands** for easy interaction and allows customization via admin commands.

## Features

- 🤖 **AI-generated responses** using KoboldCpp
- 🌐 **Web search** capability via `/browse`
- 🎨 **Image generation** via Stable Diffusion
- ⚙️ **Customizable settings** for admins
- 🛠 **Slash commands** for easy interaction

## Installation

### Prerequisites

- [KoboldCpp](https://github.com/LostRuins/koboldcpp)
- Python 3.10+
- `discord.py` library
- `requests` library
- `dotenv` for environment variables

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
   KAI_IMG_ENDPOINT=your_koboldcpp_img_url
   ADMIN_NAME=your_discord_username
   ```
4. **Run the bot:**
   ```sh
   python main.py
   ```

## Commands

**Note:** The bot must be **whitelisted** in a channel before use. Use `/whitelist` to enable commands in a channel. Additionally, interact with the bot by **mentioning** it (e.g., `@KetisBot your message`).

### User Commands

- `/browse [query]` – Search the internet
- `/draw [prompt]` – Generate an image
- `/describe [image]` – Describe an uploaded image
- `/reset` – Clear chat history

### Admin Commands

- `/maxlen [value]` – Set response length (max 512)
- `/idletime [value]` – Set bot idle timeout
- `/memory [text]` – Override bot memory

## License

This project is licensed under the MIT License.

---
