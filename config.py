import os
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv("DISCORD_BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not bot_token or not gemini_api_key:
    raise ValueError("找不到必要的環境變數")