import discord
from discord.ext import commands
import os
import flask
import threading

# 其他模組
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

# 將 bot.run() 放在一個單獨的函式中
def run_discord_bot():
    try:
        # bot.run() 是 Blocking call
        print("🚀 正在啟動 Discord 機器人...")
        bot.run(bot_token)
    except Exception as e:
        print(f"❌ 機器人運行失敗: {e}")

# 在單獨的執行緒中啟動 bot
bot_thread = threading.Thread(target=run_discord_bot)
bot_thread.daemon = True

# 這部分是 Web 伺服器的核心，處理 HTTP 請求
# Cloud Run 需要這個才能正常運作
@app.route("/", methods=["GET", "POST"])
def health_check():
    # 這個端點可以用來做健康檢查，確保服務正在運行
    return flask.jsonify({"status": "healthy"}), 200

###  測試 ###

# 傳統指令
@bot.command(name="set_role")
async def set_role_legacy(ctx, *, new_role):
    """設定你在機器人這裡扮演的角色"""
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
    """設定你在機器人這裡扮演的角色"""
    try:
        user_id = interaction.user.id
        current_profile = get_user_profile(user_id)
        current_profile['current_role'] = new_role
        update_user_profile(user_id, current_profile)
        await interaction.response.send_message(f"✅ 你的角色已成功設定為：{new_role}")
    except Exception as e:
        await interaction.response.send_message(f"❌ 發生錯誤: {e}")
        print(f"斜線指令 set_role 執行失敗: {e}")
        
############
@bot.event
async def on_ready():
    """當機器人啟動時，同步斜線指令"""
    print(f"✅ 目前登入身份 --> {bot.user}")
    try:
        bot.tree.add_command(info_group)
        slash = await bot.tree.sync()
        print(f"✅ 載入 {len(slash)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步斜線指令失敗: {e}")

if not bot_thread.is_alive():
    bot_thread.start()

# if __name__ == "__main__":
#    port = int(os.environ.get("PORT", 8080))
#    app.run(host="0.0.0.0", port=port)