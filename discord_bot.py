import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, date, timedelta, timezone
import os
import requests
import threading
import random
from flask import Flask
import yt_dlp
from googletrans import Translator # 追加

# --- 設定 ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
ROLE_ID = int(os.getenv("ROLE_ID")) if os.getenv("ROLE_ID") else None
WEATHER_AREAS = {
    "北海道": "016000", "東　北": "040000", "関　東": "130000",
    "関　西": "270000", "中　国": "340000", "四　国": "370000", "九州沖縄": "400000"
}

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run_web(): app.run(host='0.0.0.0', port=8080)

translator = Translator()

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

        if current_time == "08:00":
            msg = "🌅 全国の天気予報をお伝えします！\n"
            for area, code in WEATHER_AREAS.items():
                try:
                    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
                    weather = requests.get(url).json()[0]['timeSeries'][0]['areas'][0]['weathers'][0]
                    msg += f"・{area}：{weather}\n"
                except: msg += f"・{area}：取得失敗\n"
            await channel.send(msg)

# --- 実行 ---
bot = MyBot()

# リアクションによる自動翻訳機能
@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name in ["🇯🇵", "🇺🇸", "🇬🇧"]:
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        lang = "ja" if payload.emoji.name == "🇯🇵" else "en"
        res = translator.translate(message.content, dest=lang)
        await channel.send(f"🌍 **翻訳結果 ({lang})**: {res.text}")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/help で確認"))
    print(f"Logged in as {bot.user.name}")

# --- スラッシュコマンド追加 ---

@bot.tree.command(name="omikuji", description="今日の運勢を占います")
async def omikuji(interaction: discord.Interaction):
    results = ["大吉 🌟", "中吉 ✨", "小吉 😊", "吉 🍀", "末吉 🍃", "凶 ☁️"]
    await interaction.response.send_message(f"🔮 運勢結果：**{random.choice(results)}**")

@bot.tree.command(name="dice", description="サイコロを振ります")
async def dice(interaction: discord.Interaction, sides: int = 6):
    result = random.randint(1, sides)
    await interaction.response.send_message(f"🎲 {sides}面ダイス：**{result}**")

@bot.tree.command(name="server_info", description="サーバーの情報を表示します")
async def server_info(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"🏰 {guild.name} の情報", color=discord.Color.blue())
    embed.add_field(name="メンバー数", value=f"{guild.member_count}人")
    embed.add_field(name="作成日", value=guild.created_at.strftime("%Y/%m/%d"))
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clear", description="メッセージ削除")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 {len(deleted)}件削除しました。", ephemeral=True)

@bot.tree.command(name="help", description="機能一覧")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 最強ボット機能一覧", color=discord.Color.gold())
    embed.add_field(name="🎮 エンタメ", value="`/omikuji` `/dice`", inline=True)
    embed.add_field(name="🛠️ ツール", value="`/clear` `/server_info`", inline=True)
    embed.add_field(name="🎵 音楽", value="`/play` `/stop`", inline=True)
    embed.add_field(name="🌍 翻訳", value="メッセージに国旗リアクションしてね", inline=False)
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN: bot.run(TOKEN)
