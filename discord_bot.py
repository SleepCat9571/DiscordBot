import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, date
import os
import requests
import threading
from flask import Flask

# ==========================================
# 1. 外部サービス・環境設定
# ==========================================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
TARGET_DATE = date(2026, 1, 1)  # カウントダウン目標
AREA_CODE = "130000"           # 天気地域（東京）

# Render用ダミーサーバー
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

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
        # スラッシュコマンドを同期
        await self.tree.sync()
        # 定期実行タスクを開始
        self.super_announcement.start()

    # --- 定期通知タスク (1分ごとに実行) ---
    @tasks.loop(seconds=60)
    async def super_announcement(self):
        if not CHANNEL_ID: return
        
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        channel = self.get_channel(CHANNEL_ID)
        if not channel: return

        # 【朝 08:00】天気とカウントダウン
        if current_time == "08:00":
            # 特定日通知 (お正月)
            if now.month == 1 and now.day == 1:
                await channel.send("🌅 あけましておめでとうございます！")

            # カウントダウン
            diff = (TARGET_DATE - date.today()).days
            countdown_msg = f"📅 目標日まであと {diff} 日です！" if diff > 0 else "🎊 当日です！"
            
            # 天気予報
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

        # 【毎月1日 09:00】コミュニティ記念日
        if now.day == 1 and current_time == "09:00":
            guild = channel.guild
            # サーバー設立日との差分を計算
            created_at = guild.created_at.replace(tzinfo=None)
            months_old = (now.year - created_at.year) * 12 + (now.month - created_at.month)
            await channel.send(f"✨【記念日】今日でサーバー誕生から {months_old + 1} か月目です！おめでとうございます！")

# ==========================================
# 3. イベント・コマンド処理
# ==========================================
bot = MyBot()

@bot.event
async def on_ready():
    # ステータスを設定
    await bot.change_presence(activity=discord.Game(name="/help を入力してね"))
    print(f"Logged in as {bot.user.name}")

@bot.event
async def on_member_join(member):
    if CHANNEL_ID:
        channel = bot.get_channel(CHANNEL_ID)
        if channel: await channel.send(f"ようこそ {member.mention} さん！🎉")

# スラッシュコマンド /help
@bot.tree.command(name="help", description="機能一覧を表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 ボット機能ガイド", color=discord.Color.blue())
    embed.add_field(name="/help", value="このメニューを表示", inline=False)
    embed.add_field(name="朝 08:00", value="天気とカウントダウン通知", inline=False)
    embed.add_field(name="昼 12:00", value="お昼の挨拶", inline=False)
    embed.add_field(name="毎月1日 09:00", value="サーバー設立記念通知", inline=False)
    embed.add_field(name="目標日", value=f"{TARGET_DATE}", inline=False)
    await interaction.response.send_message(embed=embed)

# ==========================================
# 4. 実行
# ==========================================
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("TOKENが見つかりません。")
