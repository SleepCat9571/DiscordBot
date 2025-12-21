import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, date, timedelta, timezone
import os
import requests
import threading
import asyncio
from flask import Flask
import yt_dlp

# ==========================================
# 1. 設定・環境変数
# ==========================================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
ROLE_ID = int(os.getenv("ROLE_ID")) if os.getenv("ROLE_ID") else None # 追加：自動付与するロールID
AREA_CODE = "130000" # 東京

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run_web(): app.run(host='0.0.0.0', port=8080)

# 音楽再生用設定
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

# ==========================================
# 2. ボットクラス
# ==========================================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True # ユーザー入室検知に必要
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.scheduled_task.start()

    # --- 機能① & ④：特定の時間にメッセージ ＆ 天気予報 ---
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst)
        current_time = now.strftime('%H:%M')
        
        if not CHANNEL_ID: return
        channel = self.get_channel(CHANNEL_ID)
        if not channel: return

        # 朝 08:00 の通知（天気 ＋ メッセージ）
        if current_time == "08:00":
            try:
                url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{AREA_CODE}.json"
                data = requests.get(url).json()
                weather = data[0]['timeSeries'][0]['areas'][0]['weathers'][0]
                msg = f"🌅 おはようございます！現在の時刻は {current_time} です。\n☀️ 今日の天気：{weather}"
            except:
                msg = f"🌅 おはようございます！時刻は {current_time} です。（天気の取得に失敗しました）"
            await channel.send(msg)

# ==========================================
# 3. イベント処理
# ==========================================
bot = MyBot()

# --- 機能② & ③：ウェルカムメッセージ ＆ ロール自動付与 ---
@bot.event
async def on_member_join(member):
    # メッセージ送信
    if CHANNEL_ID:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"🎊 {member.mention} さん、サーバーへようこそ！")
    
    # ロール付与
    if ROLE_ID:
        role = member.guild.get_role(ROLE_ID)
        if role:
            try:
                await member.add_roles(role)
                print(f"Assign role to {member.name}")
            except Exception as e:
                print(f"Role Error: {e}")

# --- 機能⑤：音楽を流すコマンド ---
@bot.tree.command(name="play", description="YouTubeの音楽を再生します")
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        await interaction.response.send_message("先にボイスチャンネルに入ってください！", ephemeral=True)
        return

    await interaction.response.defer()
    
    channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    if not voice_client:
        voice_client = await channel.connect()
    elif voice_client.channel != channel:
        await voice_client.move_to(channel)

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
            
            if voice_client.is_playing():
                voice_client.stop()
            
            voice_client.play(source)
            await interaction.followup.send(f"🎵 再生中: {info['title']}")
        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")

@bot.tree.command(name="stop", description="音楽を停止してボットを退室させます")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ 停止して退室しました。")
    else:
        await interaction.response.send_message("ボットはボイスチャンネルにいません。", ephemeral=True)

# 起動確認
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN:
        bot.run(TOKEN)
