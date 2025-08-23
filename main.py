# main.py
import discord
from discord.ext import commands
from discord import app_commands
import os
import flask
import threading
import json
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai # type: ignore

# 匯入您的其他模組
from slash.info import info_group
from chat.gemini_api import setup_gemini_api
from database import get_user_profile, update_user_profile

# 使用你的變數名稱從環境變數中讀取金鑰
bot_token = os.getenv("DISCORD_BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not bot_token or not gemini_api_key:
    raise Exception("找不到必要的環境變數")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 這接收 HTTP 請求
app = flask.Flask(__name__)

setup_gemini_api(bot, gemini_api_key)

# 傳統指令
@bot.command(name="set_role")
async def set_role_legacy(ctx, *, new_role):
    try:
        user_id = ctx.author.id
        current_profile = get_user_profile(user_id)
        current_profile['current_role'] = new_role
        update_user_profile(user_id, current_profile)
        await ctx.send(f"✅ 你的角色已成功設定為：{new_role}")
    except Exception as e:
        await ctx.send(f"❌ 發生錯誤: {e}")
        print(f"傳統指令 set_role 執行失敗: {e}")

# 斜線指令
@bot.tree.command(name="set_role", description="設定你在機器人這裡扮演的角色")
@app_commands.describe(new_role="輸入你想要設定的角色")
async def slash_set_role(interaction: discord.Interaction, new_role: str):
    try:
        user_id = interaction.user.id
        current_profile = get_user_profile(user_id)
        current_profile['current_role'] = new_role
        update_user_profile(user_id, current_profile)
        await interaction.response.send_message(f"✅ 你的角色已成功設定為：{new_role}")
    except Exception as e:
        await interaction.response.send_message(f"❌ 發生錯誤: {e}")
        print(f"斜線指令 set_role 執行失敗: {e}")

@app.route("/", methods=["GET", "POST"])
def health_check():
    return flask.jsonify({"status": "healthy"}), 200

# 這是讓機器人運作的關鍵
@app.route("/start_bot", methods=["POST"])
async def start_bot_endpoint():
    if not bot.is_ready():
        print("🤖 正在從 /start_bot 端點啟動機器人...")
        try:
            await bot.start(bot_token)
            return "Bot started", 200
        except Exception as e:
            return f"Error starting bot: {e}", 500
    else:
        return "Bot is already running", 200

@bot.event
async def on_ready():
    print(f"✅ 目前登入身份 --> {bot.user}")
    try:
        bot.tree.add_command(info_group)
        slash = await bot.tree.sync()
        print(f"✅ 載入 {len(slash)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步斜線指令失敗: {e}")

# 直接在這裡啟動機器人，而不是在一個單獨的執行緒中
# bot.run() 是阻塞的，所以我們使用 bot.start() 和 aiohttp
# 在 Cloud Run 環境中，我們將使用 Gunicorn 來管理這個
if __name__ == "__main__":
    # 在本地測試時，您可以使用這段程式碼
    # app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    # bot.run(bot_token)
    pass
