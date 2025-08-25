import discord
from discord.ext import commands
from discord import app_commands
import os
import flask
import threading

# 匯入你的其他模組
from slash.info import info_group
from chat.gemini_api import setup_gemini_api
from database import get_user_profile, update_user_profile

# 從環境變數中讀取金鑰
bot_token = os.getenv("DISCORD_BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not bot_token or not gemini_api_key:
    print("警告: 找不到必要的環境變數，部分功能可能無法使用。")

# 在這裡只定義 Bot 和 App，不做任何會失敗的操作
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

app = flask.Flask(__name__)

# ===== 傳統指令定義 =====
@bot.command(name="set_role")
async def set_role_legacy(ctx: commands.Context, *, new_role: str):
    try:
        user_id = ctx.author.id
        current_profile = get_user_profile(user_id)
        current_profile['current_role'] = new_role
        update_user_profile(user_id, current_profile)
        await ctx.send(f"✅ 你的角色已成功設定為：{new_role}")
    except Exception as e:
        await ctx.send(f"❌ 發生錯誤: {e}")
        print(f"傳統指令 set_role 執行失敗: {e}")

# ===== 斜線指令定義 =====
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

# 將 info_group 添加到 bot.tree
bot.tree.add_command(info_group)


# ===== 服務啟動邏輯 =====
def run_bot():
    """在一個獨立的執行緒中運行機器人"""
    try:
        bot.run(bot_token)
    except Exception as e:
        print(f"機器人啟動失敗: {e}")

@app.route("/", methods=["GET"])
def health_check():
    """健康檢查端點"""
    return flask.jsonify({"status": "healthy"}), 200

def main():
    # 設置 Gemini API
    setup_gemini_api(bot, gemini_api_key)
    
    # 在一個獨立的執行緒中運行機器人
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # 在主執行緒中運行 Flask 伺服器來處理健康檢查
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    main()

@bot.event
async def on_ready():
    print(f"✅ 目前登入身份 --> {bot.user}")
    try:
        slash = await bot.tree.sync()
        print(f"✅ 載入 {len(slash)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步斜線指令失敗: {e}")