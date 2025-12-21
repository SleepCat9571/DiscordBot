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
ROLE_ID = int(os.getenv("ROLE_ID")) if os.getenv("ROLE_ID") else None

# 天気予報のエリア設定（代表地）
WEATHER_AREAS = {
    "北海道": "016000", # 札幌
    "東　北": "040000", # 仙台
    "関　東": "130000", # 東京
    "関　西": "270000", # 大阪
    "中　国": "340000", # 広島
    "四　国": "370000", # 香川
    "九州沖縄": "400000" # 福岡
}

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run_web(): app.run(host='0.0.0.0', port=8080)

# 音楽再生用設定 (エラー回避用のオプションを追加)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0', # IPv6エラー回避
}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

# ==========================================
# 2. ボット本体
# ==========================================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.scheduled_task.start()

    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst)
        current_time = now.strftime('%H:%M')
        
        if not CHANNEL_ID: return
        channel = self.get_channel(CHANNEL_ID)
        if not channel: return

        # 朝 08:00 の全国天気通知
        if current_time == "08:00":
            msg = "🌅 おはようございます！全国の天気予報をお伝えします。\n"
            
            for area_name, code in WEATHER_AREAS.items():
                try:
                    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
                    data = requests.get(url).json()
                    weather = data[0]['timeSeries'][0]['areas'][0]['weathers'][0]
                    msg += f"・{area_name}：{weather}\n"
                except:
                    msg += f"・{area_name}：取得失敗\n"
            
            await channel.send(msg)

# ==========================================
# 3. イベント・コマンド
# ==========================================
bot = MyBot()

@bot.event
async def on_member_join(member):
    if CHANNEL_ID:
        channel = bot.get_channel(CHANNEL_ID)
        if channel: await channel.send(f"🎊 {member.mention} さん、サーバーへようこそ！")
    if ROLE_ID:
        role = member.guild.get_role(ROLE_ID)
        if role:
            try: await member.add_roles(role)
            except: pass

@bot.tree.command(name="play", description="YouTube再生(※制限により失敗する場合があります)")
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        await interaction.response.send_message("先にボイスチャンネルに入ってください！", ephemeral=True)
        return

    await interaction.response.defer()
    
    try:
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client
        if not voice_client:
            voice_client = await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
            
            if voice_client.is_playing(): voice_client.stop()
            voice_client.play(source)
            await interaction.followup.send(f"🎵 再生中: {info['title']}")
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました。\n※YouTubeの制限により現在このURLは再生できません。\n詳細: {e}")

@bot.tree.command(name="stop", description="音楽停止")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ 停止しました。")
    else:
        await interaction.response.send_message("接続していません。", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN:
        bot.run(TOKEN)
