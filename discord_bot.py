import discord
from discord.ext import commands, tasks
from datetime import datetime
import os
from flask import Flask
import threading

# --- 1. Render用のダミーWebサーバー設定 ---
# これがないとRenderの無料枠では10分ほどで停止してしまいます
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    # Renderは8080ポートを期待することが多いため
    app.run(host='0.0.0.0', port=8080)

# 別スレッドでWebサーバーを起動
threading.Thread(target=run_web).start()

# --- 2. Discordボットの基本設定 ---
intents = discord.Intents.default()
intents.members = True          # 入室検知用
intents.message_content = True  # メッセージ読み取り用

bot = commands.Bot(command_prefix="!", intents=intents)

# 環境変数から設定を読み込む（Renderの管理画面で設定するもの）
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# チャンネルIDは数値である必要があるため int() で変換
CHANNEL_ID_STR = os.getenv("CHANNEL_ID")
CHANNEL_ID = int(CHANNEL_ID_STR) if CHANNEL_ID_STR else None

# --- 3. 定期通知機能 ---
@tasks.loop(seconds=60)
async def scheduled_announcements():
    if CHANNEL_ID is None:
        return

    now = datetime.now()
    current_time = now.strftime('%H:%M')

    # 【毎日12:00の通知】
    if current_time == "12:00":
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send("こんにちは！ご飯を食べましたか？")
            print(f"[{now}] 12:00の挨拶を送信しました。")

    # 【毎月1日の 09:00 の通知】
    if now.day == 1 and current_time == "09:00":
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            guild = channel.guild
            # サーバー設立日との差分を計算
            created_at = guild.created_at.replace(tzinfo=None)
            months_old = (now.year - created_at.year) * 12 + (now.month - created_at.month)
            
            await channel.send(f"✨【記念日】今日でコミュニティ誕生から {months_old + 1} か月目です！おめでとうございます！")
            print(f"[{now}] 1ヶ月記念メッセージを送信しました。")

# --- 4. ウェルカムメッセージ機能 ---
@bot.event
async def on_member_join(member):
    if CHANNEL_ID:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"いらっしゃいませ！ {member.mention} さん、サーバーへようこそ！🎉")

# --- 5. 起動時処理 ---
@bot.event
async def on_ready():
    print(f"--- 起動完了: {bot.user.name} ---")
    # 参加しているサーバー名を出力（確認用）
    for guild in bot.guilds:
        print(f"参加中のサーバー: {guild.name}")
    
    if not scheduled_announcements.is_running():
        scheduled_announcements.start()

# ボットの起動
if TOKEN:
    bot.run(TOKEN)
else:
    print("エラー: DISCORD_BOT_TOKEN が設定されていません。")
