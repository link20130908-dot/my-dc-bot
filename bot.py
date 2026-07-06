import discord
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------
# 1. 關單邏輯 (限「客服人員」使用)
# ---------------------------------------------------------
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 關閉客服單", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 權限檢查：檢查是否有「客服人員」身分組或管理員權限
        role = discord.utils.get(interaction.guild.roles, name="老闆")
        if role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 錯誤：只有「老闆」有權限關閉此單！", ephemeral=True)
            return

        await interaction.response.send_message("🚧 本客服單即將在 5 秒後自動關閉並刪除...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# ---------------------------------------------------------
# 2. 彈窗表單邏輯
# ---------------------------------------------------------
class TicketModal(discord.ui.Modal, title="📋 下單登記表"):
    item = discord.ui.TextInput(label="1. 欲購買項目", placeholder="例：尋寶隊 全包單", required=True)
    amount = discord.ui.TextInput(label="2. 購買數量", placeholder="例：5", required=True)
    currency = discord.ui.TextInput(label="3. 支付幣別", placeholder="例：許願幣", required=True)
    game_id = discord.ui.TextInput(label="4. 您的遊戲 ID", placeholder="例：1114514", required=True)
    player = discord.ui.TextInput(label="5. 陪玩人員", placeholder="例：小明", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(name=f"ticket-{user.name}", overwrites=overwrites)
        
        embed = discord.Embed(title="📥 收到新訂單預約！", color=discord.Color.green())
        embed.add_field(name="項目", value=self.item.value, inline=False)
        embed.add_field(name="數量", value=self.amount.value, inline=False)
        embed.add_field(name="幣別", value=self.currency.value, inline=False)
        embed.add_field(name="遊戲 ID", value=self.game_id.value, inline=False)
        embed.add_field(name="陪玩", value=self.player.value, inline=False)
        
        await channel.send(f"{user.mention} 您好！客服人員已收到您的資料。", embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ 已為您建立專屬頻道：{channel.mention}", ephemeral=True)

# ---------------------------------------------------------
# 3. 開單面板與權限檢查
# ---------------------------------------------------------
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✉️ 點此開單洽詢", style=discord.ButtonStyle.secondary, custom_id="ticket_button")
    async def ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    print("【系統提示】完整權限版機器人已啟動！")

@bot.command()
@commands.has_role("老闆") # 限制輸入指令權限
async def ticket(ctx):
    embed = discord.Embed(
        title="⚡ X家電競 - 遊戲陪玩服務諮詢 ⚡",
        description="請點擊下方的按鈕開啟私密客單並填寫下單登記表。",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

@ticket.error
async def ticket_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("❌ 權限不足！只有「老闆」才能使用此指令。", ephemeral=True)
import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "機器人運行中"

def run_web():
    app.run(host='0.0.0.0', port=10000)

# 啟動 Web 服務線程
t = Thread(target=run_web)
t.start()

# Discord 機器人啟動部分
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
