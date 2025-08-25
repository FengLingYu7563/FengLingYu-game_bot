# gemini_api.py
import discord
import google.generativeai as genai #type: ignore
from discord.ext import commands
import os

# 使用 os.path.join 來建構路徑，確保跨作業系統相容性
KEYWORD_LIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "keyword_list.txt")
SYSTEM_RULE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "system_rule.txt")

def read_keyword_filter():
    """從檔案讀取關鍵字清單"""
    try:
        with open(KEYWORD_LIST_PATH, 'r', encoding='UTF-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"警告: 找不到檔案 {KEYWORD_LIST_PATH}，將使用空關鍵字清單。")
        return []

def read_system_rule():
    """從檔案讀取系統指令"""
    try:
        with open(SYSTEM_RULE_PATH, 'r', encoding='UTF-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"警告: 找不到檔案 {SYSTEM_RULE_PATH}，將使用空系統指令。")
        return ""
    
def setup_gemini_api(bot: commands.Bot, api_key: str):
    """設定 Gemini API 並註冊 on_message 事件"""
    if not api_key:
        print("❌ 錯誤：未提供 Gemini API 金鑰。")
        return

    prompt_injection_keywords = read_keyword_filter()
    my_system_instruction = read_system_rule()
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=my_system_instruction
        )
        print("✅ Gemini API 已成功配置")
    except Exception as e:
        print(f"❌ 錯誤：無法配置 Gemini API 詳細錯誤：{e}")
        model = None
        return

    @bot.event
    async def on_message(message):
        """處理來自 Discord 的訊息"""
        # 忽略自己的訊息
        if message.author == bot.user:
            return

        is_mentioned = bot.user.mentioned_in(message)
        is_reply_to_bot = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user

        # 如果沒有被提及或回覆，則直接處理指令
        if not is_mentioned and not is_reply_to_bot:
            await bot.process_commands(message)
            return

        if model is None:
            await message.channel.send("抱歉，我目前無法連線到 Gemini API。")
            return

        user_input = message.content.replace(f'<@{bot.user.id}>', '').strip()

        # 檢查是否為空的輸入或包含關鍵字
        if not user_input or any(keyword in user_input for keyword in prompt_injection_keywords):
            user_input = "使用者沒有輸入"
            
        try:
            # 顯示「機器人正在打字中...」
            async with message.channel.typing():
                response = model.generate_content(
                    user_input,
                    stream=False,
                    generation_config=genai.types.GenerationConfig(
                        temperature=1
                    )
                )
                full_response = response.text
            
            await message.channel.send(full_response)
        except Exception as e:
            await message.channel.send(f"處理請求時發生了錯誤：{e}")
        
        # 確保在處理完後，讓 bot 繼續處理其他指令
        await bot.process_commands(message)