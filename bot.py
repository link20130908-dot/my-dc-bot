import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from flask import Flask
from threading import Thread

# --- 設定區 ---
BOSS_ROLE_ID = 1522857740769427486  # 替換為老闆 ID
STAFF_ROLE_ID = 1522856818626400388 # 替換為員工 ID
REVIEW_CHANNEL_ID = 1523692423790727219

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_overwrites(interaction: discord.Interaction):
    """設定頻道權限：僅老闆、員工、發單者可見"""
    boss_role = interaction.guild.get_role(BOSS_ROLE_ID)
    staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
    return {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        boss_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

def is_boss(interaction: discord.Interaction):
    """權限檢查：是否為老闆"""
    return any(role.id == BOSS_ROLE_ID for role in interaction.user.roles)

# --- 1. 評價與關單邏輯 ---
class ReviewModal(discord.ui.Modal, title='服務評價'):
    score = discord.ui.TextInput(label='請評分 (1-5星)', placeholder='輸入 1-5', min_length=1, max_length=1)
    comment = discord.ui.TextInput(label='心得分享', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.score.value)
            if not (1 <= val <= 5): raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ 請輸入 1-5 的數字！", ephemeral=True)
        
        channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
        embed = discord.Embed(title="✨ 新評價", color=discord.Color.gold())
        embed.add_field(name="客戶", value=interaction.user.mention)
        embed.add_field(name="評分", value="⭐" * val)
        embed.add_field(name="心得", value=self.comment.value)
        if channel: await channel.send(embed=embed)
        await interaction.response.send_message("感謝好評！", ephemeral=True)
        await asyncio.sleep(2)
        await interaction.channel.delete()

class CloseTicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🔒 關閉視窗", style=discord.ButtonStyle.danger, custom_id="close_btn")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 頻道將刪除...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

# --- 2. 開單介面 ---
class TicketModal(discord.ui.Modal, title="下單表"):
    item = discord.ui.TextInput(label="項目")
    amount = discord.ui.TextInput(label="數量")
    async def on_submit(self, interaction: discord.Interaction):
        channel = await interaction.guild.create_text_channel(name=f"單-{interaction.user.name}", overwrites=get_overwrites(interaction))
        await channel.send(f"✅ 訂單已建立，員工請協助處理。", view=CloseTicketView())
        await interaction.response.send_message(f"已開啟：{channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="✉️ 下單", style=discord.ButtonStyle.primary, custom_id="ticket_btn")
    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

# --- 3. 指令與啟動 ---
@bot.tree.command(name="ticket", description="發送下單面板(限老闆)")
@app_commands.check(is_boss)
async def ticket(interaction: discord.Interaction):
    await interaction.response.send_message("⚡ 電競服務區", view=TicketView())

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("❌ 權限不足。", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    print("【系統】已啟動")

app = Flask('')
@app.route('/')
def home(): return "Online"
Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
bot.run(os.getenv('DISCORD_TOKEN'))
