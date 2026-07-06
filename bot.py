import discord
from discord import app_commands
import asyncio
import os
from flask import Flask
from threading import Thread

# 設置 Intent
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 評價系統 ---
class ReviewModal(discord.ui.Modal, title='服務評價'):
    score = discord.ui.TextInput(label='請評分 (1-5星)', placeholder='請輸入數字 1-5', min_length=1, max_length=1)
    comment = discord.ui.TextInput(label='心得分享', style=discord.TextStyle.paragraph, placeholder='您的建議對我們很重要！')

    async def on_submit(self, interaction: discord.Interaction):
        REVIEW_CHANNEL_ID = 123456789012345678 # 記得修改此處
        channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
        embed = discord.Embed(title="✨ 新評價到來！", color=discord.Color.gold())
        embed.add_field(name="客戶", value=interaction.user.mention, inline=False)
        embed.add_field(name="評分", value="⭐" * int(self.score.value), inline=False)
        embed.add_field(name="心得", value=self.comment.value, inline=False)
        if channel: await channel.send(embed=embed)
        await interaction.response.send_message("感謝您的好評！頻道將在 5 秒後自動關閉。", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class ReviewButtonView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="⭐ 點此留下評價", style=discord.ButtonStyle.success)
    async def review_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReviewModal())

# --- 關單與開單邏輯 (保持不變) ---
class CloseTicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🔒 關閉客服單", style=discord.ButtonStyle.danger)
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 5 秒後刪除頻道...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="✉️ 點此開單洽詢", style=discord.ButtonStyle.secondary)
    async def ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

class TicketModal(discord.ui.Modal, title="📋 下單登記表"):
    item = discord.ui.TextInput(label="1. 欲購買項目", placeholder="例如：尋寶隊")
    amount = discord.ui.TextInput(label="2. 購買數量", placeholder="例如：5")
    currency = discord.ui.TextInput(label="3. 支付幣別", placeholder="例如：許願幣")
    game_id = discord.ui.TextInput(label="4. 遊戲 ID", placeholder="例如：1114514")
    player = discord.ui.TextInput(label="5. 陪玩人員", placeholder="例如：小明")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}")
        embed = discord.Embed(title="📥 收到新訂單預約！", color=discord.Color.green())
        # (這裡省略部分欄位加入邏輯，與你原版一致)
        await channel.send(f"{interaction.user.mention} 您好！", embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ 已建立頻道：{channel.mention}", ephemeral=True)

# --- 斜線指令註冊區 ---
@bot.event
async def on_ready():
    await bot.tree.sync() # 同步斜線指令
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    print("【系統提示】斜線指令已同步，機器人已啟動！")

@bot.tree.command(name="finish", description="發送評價按鈕")
@app_commands.checks.has_permissions(administrator=True)
async def finish(interaction: discord.Interaction):
    await interaction.response.send_message("感謝您的惠顧！請顧客點擊下方按鈕進行評價：", view=ReviewButtonView())

@bot.tree.command(name="ticket", description="發送下單面板")
@app_commands.checks.has_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    await interaction.response.send_message("⚡ X家電競 - 遊戲陪玩服務 ⚡", view=TicketView())

app = Flask('')
@app.route('/')
def home(): return "Online"
Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()

bot.run(os.getenv('DISCORD_TOKEN'))
