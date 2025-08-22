import discord
from discord.ext import commands
import os
import flask
import threading

# 你的其他模組
from slash.info import info_group
from chat.gemini_api import setup_gemini_api

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