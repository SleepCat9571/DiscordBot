import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import os
import requests
import threading
import random
import asyncio
from flask import Flask
from deep_translator import GoogleTranslator

# --- 設定（環境変数から読み込み） ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAIN_CH = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None # メイン（天気・挨拶）
LOG_CH = int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None # ログ（VC・削除）
WELCOME_CH = int(os.getenv("WELCOME_CHANNEL_ID")) if os.getenv("WELCOME_CHANNEL_ID") else None # 挨拶

BAD_WORDS = ["死ね", "殺す", "バカ", "ゴミ", "カス"]

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run_web(): app.run(host='0.0.0.0', port=8080)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.scheduled_task.start()

    # --- 1. ウェルカムメッセージ (専用チャンネルへ) ---
    @bot.event
    async def on_member_join(self, member):
        channel = self.get_channel(WELCOME_CH) or self.get_channel(MAIN_CH)
        if channel:
            await channel.send(f"🎊 {member.mention} さん、サーバーへようこそ！")

    # --- 2. VC入退室ログ (専用チャンネルへ) ---
    @bot.event
    async def on_voice_state_update(self, member, before, after):
        channel = self.get_channel(LOG_CH) or self.get_channel(MAIN_CH)
        if not channel: return
        if before.channel is None and after.channel is not None:
            await channel.send(f"🎤 **{member.display_name}** が **{after.channel.name}** に入室しました。")
        elif before.channel is not None and after.channel is None:
            await channel.send(f"👋 **{member.display_name}** が **{before.channel.name}** から退出しました。")

    # --- 3. メッセージ監視 & 自動ミュート ---
    async def on_message(self, message):
        if message.author.bot: return
        if any(word in message.content for word in BAD_WORDS):
            try:
                await message.author.timeout(timedelta(minutes=10))
                await message.delete()
                # ログチャンネルに通知
                log_ch = self.get_channel(LOG_CH) or message.channel
                await log_ch.send(f"🛡️ **ミュート実行**: {message.author.mention} が禁止用語を使用しました。")
                return
            except: pass
        await self.process_commands(message)

    # --- 4. 定期通知 (メインチャンネルへ) ---
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst)
        if now.strftime('%H:%M') == "08:00":
            channel = self.get_channel(MAIN_CH)
            if channel:
                await channel.send("🌅 おはようございます！今日の天気を確認しましょう。")

bot = MyBot()

# --- 削除コマンド (実行後にログを残す) ---
@bot.tree.command(name="clear", description="メッセージ削除")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 {len(deleted)}件削除しました。", ephemeral=True)
    
    # ログ送信
    log_ch = bot.get_channel(LOG_CH)
    if log_ch:
        await log_ch.send(f"🧹 **削除ログ**: {interaction.user.display_name} が {interaction.channel.name} で {len(deleted)}件のメッセージを削除しました。")

# (以下、他のコマンド類を継続...)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN: bot.run(TOKEN)
