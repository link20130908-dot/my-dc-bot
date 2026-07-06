import discord
from discord import app_commands
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# 1. 基礎設定
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. 你的 TicketView (保留你原本的邏輯)
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="點此開啟洽詢", style=discord.ButtonStyle.secondary, custom_id="ticket_button")
    async def ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 這裡放入你原本開啟 Modal 的邏輯
        await interaction.response.send_message("正在開啟客服單...", ephemeral=True)

# 3. 定義斜線指令 (這會自動出現在右側面板)
@bot.tree.command(name="ticket", description="開啟遊戲陪玩客服諮詢")
async def ticket(interaction: discord.Interaction):
    # 權限檢查
    role = discord.utils.get(interaction.guild.roles, name="老闆")
    if role not in interaction.user.roles:
        await interaction.response.send_message("❌ 權限不足！只有「老闆」才能使用此指令。", ephemeral=True)
        return

    embed = discord.Embed(
        title="⚡ X家電競 - 遊戲陪玩服務諮詢 ⚡",
        description="請點擊下方的按鈕開啟私密客單並填寫下單登記表。",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=TicketView())

# 4. 啟動與同步
@bot.event
async def on_ready():
    await bot.tree.sync() # 自動將指令同步到 Discord
    print(f"機器人已啟動: {bot.user}")
    print("斜線指令已成功註冊！")

# 5. Flask Web Server (維持 Render 運作)
app = Flask('')
@app.route('/')
def home(): return "Bot is online"
def run_web(): app.run(host='0.0.0.0', port=10000)
Thread(target=run_web).start()

# 6. 啟動
bot.run(os.getenv('DISCORD_TOKEN'))
