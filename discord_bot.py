import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import os
import threading
import random
import requests
from flask import Flask
import yt_dlp

# --- 1. 設定 ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAIN_CH = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
LOG_CH = int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None
WELCOME_CH = int(os.getenv("WELCOME_CHANNEL_ID")) if os.getenv("WELCOME_CHANNEL_ID") else None
PROXY = os.getenv("PROXY_URL") 

# yt-dlp オプション（プロキシ対応）
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'proxy': PROXY,
    'nocheckcertificate': True,
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

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
        # クラス内のタスクを開始
        if not self.scheduled_task.is_running():
            self.scheduled_task.start()

    async def on_ready(self):
        print(f"✅ {self.user.name} 起動完了")
        await self.change_presence(activity=discord.Game(name="/help を見てね"))

    # --- 定期タスク (必ずクラスの中に書く) ---
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst)
        current_time = now.strftime('%H:%M')
        
        channel = self.get_channel(MAIN_CH)
        if not channel: return

        if current_time == "08:00":
            await channel.send("@silent 🌅 おはようございます！8時になりました。")
        if current_time == "12:00":
            await channel.send("@silent 🕛 12時です。お昼休みにしましょう。")

# ボットの作成
bot = MyBot()

# --- 4. イベント処理 ---

@bot.event
async def on_voice_state_update(member, before, after):
    ch = bot.get_channel(LOG_CH) or bot.get_channel(MAIN_CH)
    if not ch: return
    if before.channel is None and after.channel is not None:
        await ch.send(f"@silent 🎤 **{member.display_name}** が **{after.channel.name}** に参加")
    elif before.channel is not None and after.channel is None:
        await ch.send(f"@silent 👋 **{member.display_name}** が **{before.channel.name}** から退出")

@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(word in message.content for word in BAD_WORDS):
        try:
            await message.author.timeout(timedelta(minutes=10))
            await message.delete()
            log = bot.get_channel(LOG_CH) or message.channel
            await log.send(f"@silent 🛡️ {message.author.mention} をミュートしました。")
        except: pass
    await bot.process_commands(message)

# --- 5. 音楽コマンド ---

@bot.tree.command(name="play", description="音楽再生(Proxy対応/Silent)")
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ VCに入ってください。", ephemeral=True)
    
    await interaction.response.defer()
    try:
        vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect()
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            source = await discord.FFmpegOpusAudio.from_probe(info['url'], **FFMPEG_OPTIONS)
            if vc.is_playing(): vc.stop()
            vc.play(source)
            await interaction.followup.send(f"@silent 🎵 **再生中**: {info['title']}")
    except Exception as e:
        await interaction.followup.send(f"❌ 再生エラー: {e}", ephemeral=True)

@bot.tree.command(name="stop", description="音楽停止")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("@silent ⏹️ 停止しました。")
    else:
        await interaction.response.send_message("❌ 接続していません。", ephemeral=True)

# --- 6. 実行 ---
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN: bot.run(TOKEN)

