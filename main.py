import discord
from discord.ext import commands
from discord import app_commands
import os
import flask
import threading
import json
import firebase_admin
from firebase_admin import credentials, firestore

# --- 全局變數 ---
db = None
user_cache = {}
cache_lock = threading.Lock()

# --- 資料庫初始化函式 ---
def initialize_database():
    """初始化 Firebase 和 Firestore 連線"""
    global db
    if firebase_admin._apps:
        print("警告: Firebase 已初始化，跳過重新初始化。")
        return

    try:
        cred_json_str = os.getenv("FIREBASE_ADMIN_CREDENTIALS")
        if cred_json_str:
            print("偵測到 FIREBASE_ADMIN_CREDENTIALS 環境變數。")
            cred_obj = json.loads(cred_json_str)
            cred = credentials.Certificate(cred_obj)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase 已成功初始化 (模式: 服務帳號憑證)")
        else:
            print("未找到 FIREBASE_ADMIN_CREDENTIALS，嘗試使用 ApplicationDefault。")
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
            print("✅ Firebase 已成功初始化 (模式: 應用預設憑證)")

        db = firestore.client()
        print("✅ Firestore 客戶端已成功建立。")
    except Exception as e:
        print(f"❌ Firebase 初始化失敗: {e}")
        db = None
        raise e

def get_user_profile(user_id):
    """從 Firestore 或快取中獲取使用者資料"""
    if db is None:
        raise Exception("資料庫未初始化，無法執行 get_user_profile。")

    with cache_lock:
        if user_id in user_cache:
            return user_cache[user_id]
            
    doc_ref = db.collection('user_profiles').document(str(user_id))
    try:
        doc = doc_ref.get()
        if doc.exists:
            profile = doc.to_dict()
            with cache_lock:
                user_cache[user_id] = profile
            return profile
        else:
            return {
                "current_role": "冒險者",
                "discord_id": str(user_id),
                "gpt_notes": "",
                "keywords": []
            }
    except Exception as e:
        print(f"❌ 從 Firestore 讀取使用者 {user_id} 資料失敗: {e}")
        raise e

def update_user_profile(user_id, profile_data):
    """更新 Firestore 中的使用者資料，並同步更新快取"""
    if db is None:
        raise Exception("資料庫未初始化，無法執行 update_user_profile。")

    doc_ref = db.collection('user_profiles').document(str(user_id))
    try:
        doc_ref.set(profile_data, merge=True)
        with cache_lock:
            user_cache[user_id] = profile_data
        print(f"✅ 使用者 {user_id} 的資料已更新")
    except Exception as e:
        print(f"❌ 更新 Firestore 使用者 {user_id} 資料失敗: {e}")
        raise e

# --- Discord 和 Gemini API 初始化 ---
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

# 確保你匯入所有需要的模組
# from slash.info import info_group
# from chat.gemini_api import setup_gemini_api

# --- 指令定義 ---
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
# bot.tree.add_command(info_group)


# --- 服務啟動邏輯 ---
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
    # 在主函式中明確地呼叫初始化函式
    try:
        initialize_database()
        # setup_gemini_api(bot, gemini_api_key)
        print("✅ 所有服務初始化完成")
    except Exception as e:
        print(f"初始化服務失敗: {e}")
        return
    
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