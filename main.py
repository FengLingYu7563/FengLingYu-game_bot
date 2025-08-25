import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

# model
from chat.gemini_api import setup_gemini_api
from slash.info import info_group

load_dotenv()

bot_token = os.getenv("DISCORD_BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not bot_token:
    print("❌ 警告: 找不到 DISCORD_BOT_TOKEN")
    exit()

if not gemini_api_key:
    print("❌ 警告: 找不到 GEMINI_API_KEY")

# 設定 Discord Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """當機器人啟動時觸發"""
    print(f"✅ 目前登入身份 --> {bot.user}")
    try:
        # 同步斜線指令
        slash = await bot.tree.sync()
        print(f"✅ 載入 {len(slash)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步斜線指令失敗: {e}")

bot.tree.add_command(info_group)

def main():
    """主程式啟動點"""
    
    setup_gemini_api(bot, gemini_api_key)

    print("🟢 開始運行機器人...")
    try:
        bot.run(bot_token)
    except Exception as e:
        print(f"致命錯誤：程式無法啟動。錯誤訊息：{e}")


if __name__ == "__main__":
    main()
