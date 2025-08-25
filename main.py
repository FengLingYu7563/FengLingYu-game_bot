import discord
from discord.ext import commands
from discord import app_commands
import os
import flask
import threading

from slash.info import info_group
from chat.gemini_api import setup_gemini_api
from database import get_user_profile, update_user_profile, initialize_database

bot_token = os.getenv("DISCORD_BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not bot_token or not gemini_api_key:
    print("警告: 找不到必要的環境變數，部分功能可能無法使用。")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

app = flask.Flask(__name__)

@bot.command(name="set_role")
async def set_role_legacy(ctx: commands.Context, *, new_role: str):
    try:
        user_id = ctx.author.id
        print(f"嘗試更新使用者 {user_id} 的角色為 {new_role}")
        current_profile = get_user_profile(user_id)
        current_profile['current_role'] = new_role
        update_user_profile(user_id, current_profile)
        await ctx.send(f"✅ 你的角色已成功設定為：{new_role}")
    except Exception as e:
        await ctx.send(f"❌ 發生錯誤: {e}")
        print(f"傳統指令 set_role 執行失敗: {e}")

@bot.tree.command(name="set_role", description="設定你在機器人這裡扮演的角色")
@app_commands.describe(new_role="輸入你想要設定的角色")
async def slash_set_role(interaction: discord.Interaction, new_role: str):
    try:
        user_id = interaction.user.id
        print(f"嘗試更新使用者 {user_id} 的角色為 {new_role}")
        current_profile = get_user_profile(user_id)
        current_profile['current_role'] = new_role
        update_user_profile(user_id, current_profile)
        await interaction.response.send_message(f"✅ 你的角色已成功設定為：{new_role}")
    except Exception as e:
        await interaction.response.send_message(f"❌ 發生錯誤: {e}")
        print(f"斜線指令 set_role 執行失敗: {e}")

@app.route("/", methods=["GET"])
def health_check():
    return flask.jsonify({"status": "healthy"}), 200

def start_bot_thread():
    try:
        initialize_database()
        setup_gemini_api(bot, gemini_api_key)
        print("✅ 所有服務初始化完成")
    except Exception as e:
        print(f"初始化服務失敗: {e}")
        return

    try:
        bot.run(bot_token)
    except Exception as e:
        print(f"機器人啟動失敗: {e}")

threading.Thread(target=start_bot_thread, daemon=True).start()

@bot.event
async def on_ready():
    print(f"✅ 目前登入身份 --> {bot.user}")
    try:
        bot.tree.add_command(info_group)
        slash = await bot.tree.sync()
        print(f"✅ 載入 {len(slash)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步斜線指令失敗: {e}")