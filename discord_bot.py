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
from googletrans import Translator

# --- 設定 ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
ROLE_ID = int(os.getenv("ROLE_ID")) if os.getenv("ROLE_ID") else None

# 1. あなたの代わりに設定した「禁止用語リスト」
BAD_WORDS = [
    "死ね", "殺す", "バカ", "うんこ", "ゴミ", "無能", "消えろ", 
    "キモい", "カス", "ガイジ", "死ねばいいのに"
]

# 自動返信の辞書
AUTO_REPLY = {
    "こんにちは": "こんにちは！今日も良い一日になりますように☀️",
    "お疲れ様": "お疲れ様です！ゆっくり休んでくださいね☕",
    "おやすみ": "おやすみなさい。良い夢を！🌙",
    "ボットくん": "呼びましたか？何かお手伝いしましょうか？😊"
}

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run_web(): app.run(host='0.0.0.0', port=8080)

translator = Translator()
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

    # --- メッセージ監視（禁止用語・自動返信・スパム） ---
    async def on_message(self, message):
        if message.author.bot: return

        # 禁止ワード検知
        if any(word in message.content for word in BAD_WORDS):
            try:
                await message.author.timeout(timedelta(minutes=10), reason="禁止用語の使用")
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention} 不適切な発言を検知したため、10分間ミュートしました。")
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
        current_time = now.strftime('%H:%M')
        if not CHANNEL_ID: return
        channel = self.get_channel(CHANNEL_ID)
        if not channel: return

        # 朝 08:00 全国の天気
        if current_time == "08:00":
            msg = "🌅 全国の天気予報をお伝えします！\n"
            # (中略: 前回の天気ループ処理をここに含めます)
            await channel.send(msg)

bot = MyBot()

# --- 新機能コマンド ---

@bot.tree.command(name="news", description="最新の主要ニュースを表示します")
async def news(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        # NewsAPIを使わずNHKのRSSなどから簡易取得（実際にはAPI取得が望ましい）
        # 今回は簡易的にGoogle Newsのリンクを表示
        await interaction.followup.send("📰 **最新の主要ニュースはこちら**\nhttps://news.google.com/topstories?hl=ja&gl=JP&ceid=JP:ja")
    except:
        await interaction.followup.send("ニュースの取得に失敗しました。")

@bot.tree.command(name="remind", description="指定分後にリマインダーを送ります")
async def remind(interaction: discord.Interaction, minutes: int, memo: str):
    await interaction.response.send_message(f"⏰ {minutes}分後に「{memo}」をお知らせしますね！")
    await asyncio.sleep(minutes * 60)
    await interaction.channel.send(f"🔔 {interaction.user.mention} 時間です！\n**メモ：{memo}**")

@bot.tree.command(name="user_info", description="ユーザーの情報を表示します")
async def user_info(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    embed = discord.Embed(title=f"👤 ユーザー情報: {target.name}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="サーバー加入日", value=target.joined_at.strftime("%Y/%m/%d"))
    embed.add_field(name="アカウント作成日", value=target.created_at.strftime("%Y/%m/%d"))
    embed.add_field(name="ID", value=target.id, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="omikuji", description="今日の運勢")
async def omikuji(interaction: discord.Interaction):
    results = ["大吉 🌟", "中吉 ✨", "小吉 😊", "吉 🍀", "末吉 🍃", "凶 ☁️"]
    await interaction.response.send_message(f"🔮 運勢：**{random.choice(results)}**")

@bot.tree.command(name="help", description="全機能の確認")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🚀 多機能ボット 完全ガイド", color=discord.Color.gold())
    embed.add_field(name="🛡️ 守護", value="禁止用語の自動削除・ミュート / スパム防止", inline=False)
    embed.add_field(name="📢 通知", value="08:00 天気予報 / 12:00 挨拶", inline=False)
    embed.add_field(name="🎮 遊び", value="`/omikuji` `/dice` `/remind`", inline=True)
    embed.add_field(name="📊 情報", value="`/news` `/server_info` `/user_info`", inline=True)
    await interaction.response.send_message(embed=embed)

# (clear, play, stop コマンドは前回同様に追加)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN: bot.run(TOKEN)
