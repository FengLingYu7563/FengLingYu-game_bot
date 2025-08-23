import discord
from discord.ext import commands
from discord import app_commands
import os
import flask
import asyncio

# 匯入您的其他模組
from slash.info import info_group
from chat.gemini_api import setup_gemini_api
from database import get_user_profile, update_user_profile, initialize_database

# 使用你的變數名稱從環境變數中讀取金鑰
bot_token = os.getenv("DISCORD_BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not bot_token or not gemini_api_key:
    raise Exception("找不到必要的環境變數")

# 在這裡呼叫初始化函式
initialize_database()

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

# 健康檢查路由
@app.route("/", methods=["GET", "POST"])
def health_check():
    return flask.jsonify({"status": "healthy"}), 200

# 這是讓機器人運作的關鍵
@app.route("/start_bot")
def start_bot():
    asyncio.run(bot.start(bot_token))
    return "Bot started", 200

@bot.event
async def on_ready():
    print(f"✅ 目前登入身份 --> {bot.user}")
    try:
        bot.tree.add_command(info_group)
        slash = await bot.tree.sync()
        print(f"✅ 載入 {len(slash)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步斜線指令失敗: {e}")

# Cloud Run 會自動執行這個檔案並啟動 app，所以我們不需要自己呼叫 app.run()