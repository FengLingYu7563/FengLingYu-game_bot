import discord
from discord.ext import commands
from discord import app_commands
import os
import flask
import threading

# 匯入你的其他模組
from chat.gemini_api import setup_gemini_api
from database import get_user_profile, update_user_profile, initialize_database

# 使用你的變數名稱從環境變數中讀取金鑰
bot_token = os.getenv("DISCORD_BOT_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not bot_token or not gemini_api_key:
    # 這裡可以選擇不直接拋出錯誤，讓程式繼續運行，但會缺少功能
    print("警告: 找不到必要的環境變數，部分功能可能無法使用。")

# 在這裡只定義 Bot 和 App，不做任何會失敗的操作
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

app = flask.Flask(__name__)

# ===== 斜線指令群組定義 (直接放在這裡，確保沒有匯入問題) =====
# 創建一個新的斜線指令群組來處理 /info
info_group = app_commands.Group(name="info", description="查詢各種遊戲資訊")

@info_group.command(name="boss", description="查詢 Boss 的資料")
async def info_boss(interaction: discord.Interaction):
    """
    查詢 Boss 的資料
    Args:
        interaction: 互動物件
    """
    try:
        await interaction.response.send_message("你成功執行了 /info boss 指令！")
        print("✅ /info boss 指令已成功執行")

    except Exception as e:
        await interaction.response.send_message(f"❌ 查詢 Boss 資料時發生錯誤: {e}")
        print(f"查詢 Boss 資料時發生錯誤: {e}")
        
# 將 group 加入 bot.tree
# bot.tree.add_command(info_group)
# ===== 斜線指令群組定義結束 =====


# ===== 傳統指令定義 =====
@bot.command(name="set_role")
async def set_role_legacy(ctx: commands.Context, *, new_role: str):
    """
    設定你在機器人這裡扮演的角色
    Args:
        ctx: 指令的上下文
        new_role: 使用者輸入的角色名稱
    """
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
    """
    設定你在機器人這裡扮演的角色
    Args:
        interaction: 互動物件
        new_role: 使用者輸入的角色名稱
    """
    try:
        user_id = interaction.user.id
        current_profile = get_user_profile(user_id)
        current_profile['current_role'] = new_role
        update_user_profile(user_id, current_profile)
        await interaction.response.send_message(f"✅ 你的角色已成功設定為：{new_role}")
    except Exception as e:
        await interaction.response.send_message(f"❌ 發生錯誤: {e}")
        print(f"斜線指令 set_role 執行失敗: {e}")


@app.route("/", methods=["GET"])
def health_check():
    """健康檢查端點"""
    return flask.jsonify({"status": "healthy"}), 200

# 這是讓機器人運作的關鍵
def start_bot_thread():
    # 在這裡呼叫所有初始化程式碼
    try:
        initialize_database()
        setup_gemini_api(bot, gemini_api_key)
        print("✅ 所有服務初始化完成")
    except Exception as e:
        print(f"初始化服務失敗: {e}")
        # 如果初始化失敗，讓程式終止，Cloud Run 會重啟
        return

    # 在這個獨立的執行緒中運行機器人
    try:
        bot.run(bot_token)
    except Exception as e:
        print(f"機器人啟動失敗: {e}")

# 在檔案被載入時，直接啟動一個獨立的執行緒來運行機器人
# 這個操作對 Gunicorn 來說是安全的，因為它不屬於任何請求
threading.Thread(target=start_bot_thread, daemon=True).start()

@bot.event
async def on_ready():
    print(f"✅ 目前登入身份 --> {bot.user}")
    try:
        # 將 info_group 添加到 bot.tree
        bot.tree.add_command(info_group)
        # 進行同步
        slash = await bot.tree.sync()
        print(f"✅ 載入 {len(slash)} 個斜線指令")
    except Exception as e:
        print(f"❌ 同步斜線指令失敗: {e}")