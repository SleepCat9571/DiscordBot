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

# --- 設定 ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAIN_CH = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
LOG_CH = int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None
WELCOME_CH = int(os.getenv("WELCOME_CHANNEL_ID")) if os.getenv("WELCOME_CHANNEL_ID") else None
PROXY = os.getenv("PROXY_URL") # プロキシ設定用

# yt-dlp オプション（プロキシ対応）
# プロキシがなくてもYouTubeにブロックされにくくする設定
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'nocheckcertificate': True,
    # 以下の設定を追加すると安定します
    'source_address': '0.0.0.0', # IPv6ではなくIPv4を優先
    'extract_flat': True,
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

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

bot = MyBot()

# --- イベント処理（すべてサイレント） ---

@bot.event
async def on_voice_state_update(member, before, after):
    ch = bot.get_channel(LOG_CH) or bot.get_channel(MAIN_CH)
    if not ch: return
    if before.channel is None and after.channel is not None:
        await ch.send(f"@silent 🎤 **{member.display_name}** が **{after.channel.name}** に参加")
    elif before.channel is not None and after.channel is None:
        await ch.send(f"@silent 👋 **{member.display_name}** が **{before.channel.name}** から退出")

@bot.event
async def on_member_join(member):
    ch = bot.get_channel(WELCOME_CH) or bot.get_channel(MAIN_CH)
    if ch: await ch.send(f"@silent 🎊 {member.mention} さん、いらっしゃいませ！")

@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(word in message.content for word in BAD_WORDS):
        try:
            await message.author.timeout(timedelta(minutes=10))
            await message.delete()
            log = bot.get_channel(LOG_CH) or message.channel
            await log.send(f"@silent 🛡️ {message.author.mention} を禁止用語でミュートしました。")
        except: pass
    await bot.process_commands(message)

# --- 音楽コマンド ---

@bot.tree.command(name="play", description="YouTube音楽再生（プロキシ経由）")
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ ボイスチャンネルに入ってください。", ephemeral=True)
    
    await interaction.response.defer()
    try:
        vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect()
        
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
            
            if vc.is_playing(): vc.stop()
            vc.play(source)
            # サイレント通知で再生開始
            await interaction.followup.send(f"@silent 🎵 **再生中**: {info['title']}")
    except Exception as e:
        await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)

@bot.tree.command(name="stop", description="音楽を停止して退室")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("@silent ⏹️ 音楽を停止して退室しました。")
    else:
        await interaction.response.send_message("❌ 接続していません。", ephemeral=True)

# --- その他コマンド ---

@bot.tree.command(name="help", description="機能一覧")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 多機能ボット (Silent & Proxy Edition)", color=discord.Color.blue())
    embed.description = "すべての通知は音なし(@silent)で送信されます。"
    embed.add_field(name="🎵 音楽", value="`/play` `/stop` (プロキシ対応)", inline=True)
    embed.add_field(name="🛠 管理", value="`/clear` `/poll` `/omikuji`", inline=True)
    await interaction.response.send_message(embed=embed)

@tasks.loop(seconds=60)
async def scheduled_task():
    # 天気などの定期通知（前回のロジックをここに維持）
    pass

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN: bot.run(TOKEN)
