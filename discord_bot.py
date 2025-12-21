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

# --- 1. 設定（環境変数） ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAIN_CH = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
LOG_CH = int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None
WELCOME_CH = int(os.getenv("WELCOME_CHANNEL_ID")) if os.getenv("WELCOME_CHANNEL_ID") else None

BAD_WORDS = ["死ね", "殺す", "バカ", "ゴミ", "カス"]

# --- 2. Flask（Render維持用） ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- 3. ボットクラス定義 ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.scheduled_task.start() # クラス内のタスクを開始

    async def on_ready(self):
        print(f"✅ Logged in as {self.user.name}")
        await self.change_presence(activity=discord.Game(name="/help を見てね"))

    # 定期タスクをクラスの中に定義
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst)
        current_time = now.strftime('%H:%M')
        
        if current_time == "08:00":
            ch = self.get_channel(MAIN_CH)
            if ch: await ch.send("🌅 おはようございます！8時になりました。今日の天気を確認しましょう。")

# ボットの作成
bot = MyBot()

# --- 4. イベント処理 ---

@bot.event
async def on_member_join(member):
    target_ch = bot.get_channel(WELCOME_CH) or bot.get_channel(MAIN_CH)
    if target_ch:
        await target_ch.send(f"🎊 {member.mention} さん、サーバーへようこそ！")

@bot.event
async def on_voice_state_update(member, before, after):
    target_ch = bot.get_channel(LOG_CH) or bot.get_channel(MAIN_CH)
    if not target_ch: return
    if before.channel is None and after.channel is not None:
        await target_ch.send(f"🎤 **{member.display_name}** が **{after.channel.name}** に入室")
    elif before.channel is not None and after.channel is None:
        await target_ch.send(f"👋 **{member.display_name}** が **{before.channel.name}** から退出")

@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(word in message.content for word in BAD_WORDS):
        try:
            await message.author.timeout(timedelta(minutes=10))
            await message.delete()
            log_ch = bot.get_channel(LOG_CH) or message.channel
            await log_ch.send(f"🛡️ **ミュート**: {message.author.mention} が禁止用語を使用。")
            return
        except: pass
    await bot.process_commands(message)

# --- 5. コマンド定義 ---

@bot.tree.command(name="help", description="機能一覧")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🚀 ボット機能ガイド", color=discord.Color.blue())
    embed.add_field(name="コマンド", value="`/omikuji` `/clear` `/slot` `/poll` `/remind`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clear", description="メッセージ削除")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_cmd(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 {len(deleted)}件削除しました。", ephemeral=True)

@bot.tree.command(name="omikuji", description="おみくじ")
async def omikuji_cmd(interaction: discord.Interaction):
    res = random.choice(["大吉🌟", "中吉✨", "小吉😊", "吉🍀", "凶☁️"])
    await interaction.response.send_message(f"🔮 運勢: **{res}**")

# --- 6. 実行 ---
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN:
        bot.run(TOKEN)
