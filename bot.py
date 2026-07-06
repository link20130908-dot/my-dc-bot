import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import io
import chat_exporter
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 1. 評價系統 ---
class ReviewModal(discord.ui.Modal, title='服務評價'):
    score = discord.ui.TextInput(label='請評分 (1-5星)', placeholder='請輸入 1-5', min_length=1, max_length=1)
    comment = discord.ui.TextInput(label='心得分享', style=discord.TextStyle.paragraph, placeholder='您的建議對我們很重要！')

    async def on_submit(self, interaction: discord.Interaction):
        REVIEW_CHANNEL_ID = 1523703386992676864 # 請確保正確
        channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
        embed = discord.Embed(title="✨ 新評價到來！", color=discord.Color.gold())
        embed.add_field(name="客戶", value=interaction.user.mention, inline=False)
        embed.add_field(name="評分", value="⭐" * int(self.score.value), inline=False)
        embed.add_field(name="心得", value=self.comment.value, inline=False)
        if channel: await channel.send(embed=embed)
        await interaction.response.send_message("感謝評價！頻道將在 5 秒後關閉。", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class ReviewButtonView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="⭐ 點此留下評價", style=discord.ButtonStyle.success, custom_id="unique_review_btn")
    async def review_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReviewModal())

# --- 2. 關單與存檔邏輯 ---
class CloseTicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🔒 關閉客服單", style=discord.ButtonStyle.danger, custom_id="unique_close_btn")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 自動存檔邏輯
        LOG_CHANNEL_ID = 1523703386992676864 # 存檔頻道 ID
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        transcript = await chat_exporter.chat_export(interaction.channel)
        if transcript:
            file = discord.File(io.BytesIO(transcript.encode()), filename=f"紀錄-{interaction.channel.name}.html")
            if log_channel: await log_channel.send(f"📋 **訂單存檔：{interaction.channel.name}**", file=file)

        await interaction.response.send_message("🚧 紀錄已備份，5 秒後刪除頻道...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- 3. 開單面板 ---
class TicketModal(discord.ui.Modal, title="📋 下單登記表"):
    item = discord.ui.TextInput(label="1. 欲購買項目", placeholder="例如：尋寶隊")
    amount = discord.ui.TextInput(label="2. 購買數量")
    currency = discord.ui.TextInput(label="3. 支付幣別")
    game_id = discord.ui.TextInput(label="4. 遊戲 ID")
    player = discord.ui.TextInput(label="5. 陪玩人員")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}")
        embed = discord.Embed(title="📥 收到新訂單預約！", color=discord.Color.green())
        embed.add_field(name="資訊", value=f"項目:{self.item.value}\n數量:{self.amount.value}\n幣別:{self.currency.value}\nID:{self.game_id.value}\n陪玩:{self.player.value}", inline=False)
        await channel.send(f"{interaction.user.mention} 您好！", embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ 已建立頻道：{channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="✉️ 點此開單洽詢", style=discord.ButtonStyle.primary, custom_id="unique_ticket_btn")
    async def ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

class DirectTicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🛠️ 聯絡官方客服", style=discord.ButtonStyle.primary, custom_id="unique_support_btn")
    async def direct_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        channel = await interaction.guild.create_text_channel(name=f"客服-{interaction.user.name}")
        embed = discord.Embed(title="💬 官方客服", description="請說明問題，完畢後點擊關閉。", color=discord.Color.orange())
        await channel.send(f"{interaction.user.mention} 您好！", embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ 已建立專屬頻道：{channel.mention}", ephemeral=True)

# --- 4. 啟動與指令 ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    bot.add_view(TicketView())
    bot.add_view(DirectTicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(ReviewButtonView())
    print("【系統提示】機器人已啟動！")

@bot.tree.command(name="ticket", description="發送下單面板")
async def ticket(interaction: discord.Interaction):
    embed = discord.Embed(title="⚡ X家電競 - 遊戲陪玩服務 ⚡", description="點擊下方按鈕諮詢。", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, view=TicketView())

@bot.tree.command(name="support", description="發送客服面板")
async def support(interaction: discord.Interaction):
    embed = discord.Embed(title="🛠️ 聯絡官方客服面板 🛠️", description="若有問題，請點擊下方按鈕。", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed, view=DirectTicketView())

@bot.tree.command(name="finish", description="發送評價按鈕")
async def finish(interaction: discord.Interaction):
    await interaction.response.send_message("請顧客點擊下方按鈕評價：", view=ReviewButtonView())

app = Flask('')
@app.route('/')
def home(): return "Online"
Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
bot.run(os.getenv('DISCORD_TOKEN'))
