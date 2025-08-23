import discord
import google.generativeai as genai # type: ignore
from discord.ext import commands
import os

KEYWORD_LIST_PATH = os.path.join((os.path.dirname(os.path.dirname(__file__))), "data", "keyword_list.txt")
SYSTEM_RULE_PATH = os.path.join((os.path.dirname(os.path.dirname(__file__))), "data", "system_rule.txt")

def read_keyword_filter():
    with open(KEYWORD_LIST_PATH, 'r', encoding='UTF-8') as f:
        return [line.strip() for line in f if line.strip()]

def read_system_rule():
    with open(SYSTEM_RULE_PATH, 'r', encoding='UTF-8') as f:
        return f.read().strip()
    
def setup_gemini_api(bot: commands.Bot, api_key: str):
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
        print(f"錯誤：無法配置 Gemini API。檢查 API 金鑰。詳細錯誤：{e}")
        model = None
        return

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return

        is_mentioned = bot.user.mentioned_in(message)
        is_reply_to_bot = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user

        if not is_mentioned and not is_reply_to_bot:
            await bot.process_commands(message)
            return

        if model is None:
            await message.channel.send("抱歉，我目前無法連線到 Gemini API。")
            return

        user_input = message.content.replace(f'<@{bot.user.id}>', '').strip()

        if not user_input or any(keyword in user_input for keyword in prompt_injection_keywords):
            user_input = "使用者沒有輸入"
            
        try:
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
        
        await bot.process_commands(message)
