import discord
from discord.ext import commands
import os
import flask
from threading import Thread
import asyncio
from dotenv import load_dotenv

# 你的其他模組
from slash.info import info_group
from chat.gemini_api import setup_gemini_api

# 載入環境變數
load_dotenv()

# 使用你的變數名稱從環境變數中讀取金鑰
bot_token = os.getenv("DISCORD_BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 這接收 HTTP 請求
app = flask.Flask(__name__)

# 將 bot.run() 放在一個單獨的函式中
def run_discord_bot():
    try:
        # bot.run() 是 Blocking call
        bot.run(bot_token)
    except Exception as e:
        print(f"❌ 機器人運行失敗: {e}")

# 在 Flask 應用啟動前，啟動 bot
@app.before_first_request
def start_bot_in_background():
    # 啟動一個新執行緒來運行 bot.run()，以免阻塞 Web 伺服器
    Thread(target=run_discord_bot).start()

    # 在這裡設定 Gemini API
    setup_gemini_api(bot, gemini_api_key)

@bot.event
async def on_ready():
    """當機器人啟動時，同步斜線指令"""
    print(f"✅ 目前登入身份 --> {bot.user}")
    try:
        # 添加斜線指令群組
        bot.tree.add_command(info_group)
        # 同步斜線指令
        slash = await bot.tree.sync()
        print(f"✅ 載入 {len(slash)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步斜線指令失敗: {e}")

# 這部分是 Web 伺服器的核心，處理 HTTP 請求
# Cloud Run 需要這個才能正常運作
@app.route("/", methods=["GET", "POST"])
def health_check():
    # 這個端點可以用來做健康檢查，確保服務正在運行
    return flask.jsonify({"status": "healthy"}), 200

# if __name__ == "__main__":
#    port = int(os.environ.get("PORT", 8080))
#    app.run(host="0.0.0.0", port=port)