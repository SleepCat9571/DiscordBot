import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, date, timedelta, timezone
import os
import requests
import threading
import random
import asyncio
from flask import Flask
import yt_dlp
from deep_translator import GoogleTranslator # 修正版

# --- 設定 ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
ROLE_ID = int(os.getenv("ROLE_ID")) if os.getenv("ROLE_ID") else None

BAD_WORDS = ["死ね", "殺す", "バカ", "ゴミ", "カス"] # 禁止用語
AUTO_REPLY = {"こんにちは": "こんにちは！😊", "お疲れ様": "お疲れ様です！☕"}

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run_web(): app.run(host='0.0.0.0', port=8080)

user_msg_times = {}

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.scheduled_task.start()

    async def on_message(self, message):
        if message.author.bot: return
        # 禁止用語ミュート
        if any(word in message.content for word in BAD_WORDS):
            try:
                await message.author.timeout(timedelta(minutes=10))
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention} 不適切な発言のためミュートしました。")
                return
            except: pass
        # 自動返信
        for key, val in AUTO_REPLY.items():
            if key in message.content:
                await message.channel.send(val)
                break
        await self.process_commands(message)

    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst)
        if now.strftime('%H:%M') == "08:00" and CHANNEL_ID:
            ch = self.get_channel(CHANNEL_ID)
            if ch: await ch.send("🌅 8時です。おはようございます！")

bot = MyBot()

# 翻訳機能 (修正版)
@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name in ["🇯🇵", "🇺🇸"]:
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        target = "ja" if payload.emoji.name == "🇯🇵" else "en"
        try:
            translated = GoogleTranslator(source='auto', target=target).translate(message.content)
            await channel.send(f"🌍 **翻訳 ({target})**: {translated}")
        except: pass

@bot.tree.command(name="help", description="機能一覧")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("⚙️ **機能一覧**: /omikuji, /clear, /play, /stop, /remind, /user_info\n🌍 **翻訳**: 旗リアクション\n🛡️ **管理**: 禁止用語自動ミュート")

@bot.tree.command(name="omikuji", description="おみくじ")
async def omikuji(interaction: discord.Interaction):
    await interaction.response.send_message(f"🔮 運勢: {random.choice(['大吉','中吉','小吉','吉'])}")

@bot.tree.command(name="clear", description="削除")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 {len(deleted)}件削除しました。", ephemeral=True)

@bot.tree.command(name="remind", description="リマインダー(分)")
async def remind(interaction: discord.Interaction, minutes: int, memo: str):
    await interaction.response.send_message(f"⏰ {minutes}分後に通知します。")
    await asyncio.sleep(minutes * 60)
    await interaction.channel.send(f"🔔 {interaction.user.mention} 時間です！: {memo}")

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN: bot.run(TOKEN)
