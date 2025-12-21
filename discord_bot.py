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
import yt_dlp
from deep_translator import GoogleTranslator

# --- 1. 設定（環境変数） ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAIN_CH = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
LOG_CH = int(os.getenv("LOG_CHANNEL_ID")) if os.getenv("LOG_CHANNEL_ID") else None
WELCOME_CH = int(os.getenv("WELCOME_CHANNEL_ID")) if os.getenv("WELCOME_CHANNEL_ID") else None

BAD_WORDS = ["死ね", "殺す", "バカ", "ゴミ", "カス"]
WEATHER_AREAS = {
    "北海道": "016000", "東　北": "040000", "関　東": "130000",
    "関　西": "270000", "中　国": "340000", "四　国": "370000", "九州沖縄": "400000"
}

# 音楽再生用設定
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True', 'quiet': True}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

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
        self.scheduled_task.start()

    async def on_ready(self):
        print(f"✅ {self.user.name} 起動完了")
        await self.change_presence(activity=discord.Game(name="/help をチェック！"))

    # --- 定期タスク (天気・挨拶) ---
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst)
        current_time = now.strftime('%H:%M')
        
        channel = self.get_channel(MAIN_CH)
        if not channel: return

        # 朝 08:00 の全国天気
        if current_time == "08:00":
            msg = "🌅 全国の天気予報です\n"
            for area, code in WEATHER_AREAS.items():
                try:
                    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
                    weather = requests.get(url).json()[0]['timeSeries'][0]['areas'][0]['weathers'][0]
                    msg += f"・{area}：{weather}\n"
                except: msg += f"・{area}：取得失敗\n"
            await channel.send(msg)

        # 昼 12:00 の挨拶
        if current_time == "12:00":
            await channel.send("🕛 12時になりました。お昼休憩にしましょう！☕")

bot = MyBot()

# --- 4. イベント処理 ---

@bot.event
async def on_member_join(member):
    ch = bot.get_channel(WELCOME_CH) or bot.get_channel(MAIN_CH)
    if ch: await ch.send(f"🎊 {member.mention} さん、いらっしゃいませ！")

@bot.event
async def on_voice_state_update(member, before, after):
    ch = bot.get_channel(LOG_CH) or bot.get_channel(MAIN_CH)
    if not ch: return
    if before.channel is None and after.channel is not None:
        await ch.send(f"🎤 **{member.display_name}** が **{after.channel.name}** に参加")
    elif before.channel is not None and after.channel is None:
        await ch.send(f"👋 **{member.display_name}** が **{before.channel.name}** から退出")

@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(word in message.content for word in BAD_WORDS):
        try:
            await message.author.timeout(timedelta(minutes=10))
            await message.delete()
            log = bot.get_channel(LOG_CH) or message.channel
            await log.send(f"🛡️ {message.author.mention} を禁止用語使用でミュートしました。")
            return
        except: pass
    await bot.process_commands(message)

# --- 5. スラッシュコマンド ---

@bot.tree.command(name="play", description="YouTube音楽再生")
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("先にVCに入ってください", ephemeral=True)
    await interaction.response.defer()
    try:
        vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect()
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            source = await discord.FFmpegOpusAudio.from_probe(info['url'], **FFMPEG_OPTIONS)
            if vc.is_playing(): vc.stop()
            vc.play(source)
            await interaction.followup.send(f"🎵 再生中: {info['title']}")
    except:
        await interaction.followup.send("再生に失敗しました。")

@bot.tree.command(name="stop", description="音楽停止・退室")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ 停止して退室しました。")
    else:
        await interaction.response.send_message("接続していません。", ephemeral=True)

@bot.tree.command(name="help", description="機能一覧")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 サーバー管理・多機能ボット", color=discord.Color.gold())
    embed.add_field(name="🎵 音楽", value="`/play [URL]` `/stop`", inline=True)
    embed.add_field(name="🧹 管理", value="`/clear` `/remind` `/set_nick`", inline=True)
    embed.add_field(name="🎮 遊び", value="`/omikuji` `/slot` `/poll`", inline=True)
    embed.add_field(name="📢 通知", value="08:00 天気 / 12:00 挨拶\n入退室ログ / 禁止ワード監視", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clear", description="メッセージ削除")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    log = bot.get_channel(LOG_CH)
    if log: await log.send(f"🧹 {interaction.user.name} が {len(deleted)}件削除しました。")
    await interaction.followup.send(f"✅ {len(deleted)}件削除しました。", ephemeral=True)

# --- 6. 実行 ---
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN: bot.run(TOKEN)
