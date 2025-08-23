import discord
from discord.ext import commands
from discord import app_commands
import os
import flask
import threading

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

# 協助處理設定角色和回應的輔助函式
# 這個函式將重複的邏輯集中在一個地方
async def _update_role_and_respond(user_id, new_role, responder):
    """
    Update the user's role and send a response.

    Args:
        user_id (int): The ID of the user.
        new_role (str): The new role to set.
        responder: The object to send the response (ctx or interaction).
    """
    try:
        current_profile = get_user_profile(user_id)
        current_profile['current_role'] = new_role
        update_user_profile(user_id, current_profile)
        message = f"✅ 你的角色已成功設定為：{new_role}"
        if isinstance(responder, commands.Context):
            await responder.send(message)
        else: # discord.Interaction
            await responder.response.send_message(message)
    except Exception as e:
        message = f"❌ 發生錯誤: {e}"
        if isinstance(responder, commands.Context):
            await responder.send(message)
        else: # discord.Interaction
            await responder.response.send_message(message)
        print(f"指令 set_role 執行失敗: {e}")

# 傳統指令
@bot.command(name="set_role")
async def set_role_legacy(ctx, *, new_role):
    # 調用輔助函式來處理核心邏輯
    await _update_role_and_respond(ctx.author.id, new_role, ctx)

# 斜線指令
@bot.tree.command(name="set_role", description="設定你在機器人這裡扮演的角色")
@app_commands.describe(new_role="輸入你想要設定的角色")
async def slash_set_role(interaction: discord.Interaction, new_role: str):
    # 調用輔助函式來處理核心邏輯
    await _update_role_and_respond(interaction.user.id, new_role, interaction)

@app.route("/", methods=["GET"])
def health_check():
    """健康檢查端點"""
    return flask.jsonify({"status": "healthy"}), 200

# 這是讓機器人運作的關鍵
@app.before_serving
def start_bot():
    def run_bot():
        bot.run(bot_token)
    
    threading.Thread(target=run_bot).start()

@bot.event
async def on_ready():
    print(f"✅ 目前登入身份 --> {bot.user}")
    try:
        bot.tree.add_command(info_group)
        slash = await bot.tree.sync()
        print(f"✅ 載入 {len(slash)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步斜線指令失敗: {e}")