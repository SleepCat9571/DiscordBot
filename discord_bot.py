from flask import Flask
import threading

# Renderで動かすためのダミーサーバー
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# スレッドでWebサーバーを動かす
threading.Thread(target=run_web).start()

# --- ここから下に、今までのDiscordボットのコードを貼る ---

import discord
from discord.ext import commands, tasks
from datetime import datetime
import asyncio

# --- 設定（ここを自分のものに書き換える） ---
CHANNEL_ID = 1434201468663234640  # 通知を送るチャンネルID
TOKEN = "MTQ1MTk5MzM0MjEwMjczNzEyOQ.Gag7LH.Uxr7TZEbSrmvfZSEvEm_yX2rTfvXlqABhYKG3c"      # ボットのトークン

intents = discord.Intents.default()
intents.members = True          # 入室検知用
intents.message_content = True  # メッセージ読み取り用

bot = commands.Bot(command_prefix="!", intents=intents)

# 1. 毎月1日の「●か月目」通知 ＆ 2. 毎日12:00の挨拶
@tasks.loop(seconds=60)
async def scheduled_announcements():
    now = datetime.now()
    current_time = now.strftime('%H:%M')

    # 【毎日12:00の通知】
    if current_time == "12:00":
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send("こんにちは！12時です！ご飯を食べましたか？")
            print(f"[{now}] 12:00の挨拶を送信しました。")

    # 【毎月1日の 09:00 の通知】
    if now.day == 1 and current_time == "09:00":
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            guild = channel.guild
            # サーバー設立日との差分を計算（簡易版：月数の差）
            created_at = guild.created_at.replace(tzinfo=None)
            months_old = (now.year - created_at.year) * 12 + (now.month - created_at.month)
            
            await channel.send(f"✨【記念日】今日でサーバー誕生から {months_old + 1} か月目です！おめでとうございます！")
            print(f"[{now}] 1ヶ月記念メッセージを送信しました。")

# 3. 誰かが入ってきたときのウェルカムメッセージ
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(f"いらっしゃいませ！ {member.mention} さん、サーバーへようこそ！🎉")

@bot.event
async def on_ready():
    print(f"--- 起動完了: {bot.user.name} ---")
    if not scheduled_announcements.is_running():
        scheduled_announcements.start()


bot.run(TOKEN)
