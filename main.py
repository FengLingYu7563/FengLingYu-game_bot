import discord
from discord.ext import commands
import os
from slash.info import info_group
from config import bot_token, gemini_api_key
from chat.gemini_api import setup_gemini_api

intents = discord.Intents.default() 
bot = commands.Bot(command_prefix="!", intents=intents)
        
@bot.event
async def on_ready():
    """當機器人啟動時，同步斜線指令"""
    bot.tree.add_command(info_group)
    slash = await bot.tree.sync()
    print(f"✅ 目前登入身份 --> {bot.user}")
    print(f"✅ 載入 {len(slash)} 個斜線指令")

setup_gemini_api(bot, gemini_api_key)

# 啟動 Bot
bot.run(bot_token)