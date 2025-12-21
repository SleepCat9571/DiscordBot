import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, date, timedelta, timezone # timezoneを追加
import os
import requests
import threading
from flask import Flask

# ==========================================
# 1. 外部サービス・環境設定
# ==========================================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
TARGET_DATE = date(2026, 1, 1)
AREA_CODE = "130000"

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run_web(): app.run(host='0.0.0.0', port=8080)

# ==========================================
# 2. ボットクラスの定義
# ==========================================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        self.super_announcement.start()

    @tasks.loop(seconds=60)
    async def super_announcement(self):
        if not CHANNEL_ID: return
        
        # --- ここで日本時間を取得するように修正 ---
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst) 
        current_time = now.strftime('%H:%M')
        channel = self.get_channel(CHANNEL_ID)
        if not channel: return

        # 【朝 08:00】天気とカウントダウン
        if current_time == "08:00":
            if now.month == 1 and now.day == 1:
                await channel.send("🌅 あけましておめでとうございます！")

            diff = (TARGET_DATE - now.date()).days
            countdown_msg = f"📅 目標日まであと {diff} 日です！" if diff > 0 else "🎊 当日です！"
            
            try:
                url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{AREA_CODE}.json"
                data = requests.get(url).json()
                weather = data[0]['timeSeries'][0]['areas'][0]['weathers'][0]
                weather_msg = f"☀️ 今日の天気：{weather}"
                if "雨" in weather: weather_msg += " ☔傘を忘れずに！"
            except:
                weather_msg = "天気情報の取得に失敗しました。"

            await channel.send(f"【朝の定期連絡】\n{countdown_msg}\n{weather_msg}")

        # 【昼 12:00】お昼の挨拶
        if current_time == "12:00":
            await channel.send("🕛 12時になりました。お昼ご飯を食べて、午後も頑張りましょう！")

        # 【毎月1日 09:00】記念日通知
        if now.day == 1 and current_time == "09:00":
            guild = channel.guild
            created_at = guild.created_at.replace(tzinfo=None)
            months_old = (now.year - created_at.year) * 12 + (now.month - created_at.month)
            await channel.send(f"✨ 今日でサーバー誕生から {months_old + 1} か月目です！")

# ==========================================
# 3. イベント処理
# ==========================================
bot = MyBot()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/help を入力してね"))
    print(f"Logged in as {bot.user.name} (JST Mode)")

@bot.event
async def on_member_join(member):
    if CHANNEL_ID:
        channel = bot.get_channel(CHANNEL_ID)
        if channel: await channel.send(f"ようこそ {member.mention} さん！🎉")

@bot.tree.command(name="help", description="機能一覧を表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 ボット機能ガイド", color=discord.Color.blue())
    embed.add_field(name="/help", value="このメニューを表示", inline=False)
    embed.add_field(name="通知時刻", value="朝 08:00 / 昼 12:00 (日本時間)", inline=False)
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN:
        bot.run(TOKEN)




