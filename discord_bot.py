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

# 天気予報のエリア設定
WEATHER_AREAS = {
    "北海道": "016000", "東　北": "040000", "関　東": "130000",
    "関　西": "270000", "中　国": "340000", "四　国": "370000", "九州沖縄": "400000"
}

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run_web(): app.run(host='0.0.0.0', port=8080)

# 音楽再生用設定
YDL_OPTIONS = {
    'format': 'bestaudio/best', 'noplaylist': 'True', 'quiet': True,
    'no_warnings': True, 'default_search': 'auto', 'source_address': '0.0.0.0',
}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

# ==========================================
# 2. ボットクラス定義
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

    # --- 定期実行タスク (天気・挨拶) ---
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst)
        current_time = now.strftime('%H:%M')
        
        if not CHANNEL_ID: return
        channel = self.get_channel(CHANNEL_ID)
        if not channel: return

        # 朝 08:00 の全国天気
        if current_time == "08:00":
            msg = "🌅 おはようございます！全国の天気をお伝えします。\n"
            for area, code in WEATHER_AREAS.items():
                try:
                    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
                    weather = requests.get(url).json()[0]['timeSeries'][0]['areas'][0]['weathers'][0]
                    msg += f"・{area}：{weather}\n"
                except: msg += f"・{area}：取得失敗\n"
            await channel.send(msg)

        # 昼 12:00 の挨拶
        if current_time == "12:00":
            await channel.send("🕛 12時になりました。お昼休憩にしましょう！")

# ==========================================
# 3. イベント・コマンド
# ==========================================
bot = MyBot()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/help で機能確認"))
    print(f"Logged in as {bot.user.name}")

# 入室通知 ＆ ロール付与
@bot.event
async def on_member_join(member):
    if CHANNEL_ID:
        channel = bot.get_channel(CHANNEL_ID)
        if channel: await channel.send(f"🎊 {member.mention} さん、いらっしゃいませ！")
    if ROLE_ID:
        role = member.guild.get_role(ROLE_ID)
        if role:
            try: await member.add_roles(role)
            except Exception as e: print(f"Role Error: {e}")

# --- スラッシュコマンド一覧 ---

@bot.tree.command(name="help", description="ボットの機能一覧を表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 多機能ボット ヘルプメニュー", color=discord.Color.green())
    embed.add_field(name="📅 定期通知", value="08:00 全国の天気 / 12:00 お昼の挨拶", inline=False)
    embed.add_field(name="🧹 掃除", value="`/clear [数]`：メッセージをまとめて削除", inline=False)
    embed.add_field(name="🎵 音楽", value="`/play [URL]`：再生 / `/stop`：停止", inline=False)
    embed.add_field(name="👥 メンバー", value="入室時の歓迎メッセージ ＆ ロール自動付与", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clear", description="メッセージをまとめて削除します")
@app_commands.describe(amount="削除するメッセージの数(1-100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        await interaction.response.send_message("1〜100の間で指定してください。", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 {len(deleted)}件のメッセージを削除しました。", ephemeral=True)

@bot.tree.command(name="play", description="音楽再生(YouTube)")
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        await interaction.response.send_message("先にボイスチャンネルに入ってください！", ephemeral=True)
        return
    await interaction.response.defer()
    try:
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client or await channel.connect()
        if voice_client.channel != channel: await voice_client.move_to(channel)

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            source = await discord.FFmpegOpusAudio.from_probe(info['url'], **FFMPEG_OPTIONS)
            if voice_client.is_playing(): voice_client.stop()
            voice_client.play(source)
            await interaction.followup.send(f"🎵 再生中: {info['title']}")
    except Exception as e:
        await interaction.followup.send(f"エラー: 再生できませんでした(YouTubeの制限等)。")

@bot.tree.command(name="stop", description="音楽停止・退室")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ 停止しました。")
    else: await interaction.response.send_message("接続していません。", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN: bot.run(TOKEN)
