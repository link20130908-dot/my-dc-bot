import discord
from discord.ext import commands
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
        # 【重要】請將下方 ID 換成你伺服器「評價頻道」的 ID
        REVIEW_CHANNEL_ID = 123456789012345678 
        channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
        
        embed = discord.Embed(title="✨ 新評價到來！", color=discord.Color.gold())
        embed.add_field(name="客戶", value=interaction.user.mention, inline=False)
        embed.add_field(name="評分", value="⭐" * int(self.score.value), inline=False)
        embed.add_field(name="心得", value=self.comment.value, inline=False)
        
        if channel: await channel.send(embed=embed)
        await interaction.response.send_message("感謝您的好評！頻道將在 5 秒後自動關閉。", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- 1. 關單邏輯 (已整合評價) ---
class CloseTicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="🔒 關閉客服單", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="老闆")
        if role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 只有「老闆」有權限關閉！", ephemeral=True)
            return
        # 點擊關單後，先彈出評價視窗
        await interaction.response.send_modal(ReviewModal())

# --- 2. 直接開單邏輯 ---
class DirectTicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🛠️ 聯絡官方客服", style=discord.ButtonStyle.primary, custom_id="direct_ticket_button")
    async def direct_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        admin_role = discord.utils.get(guild.roles, name="老闆")
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), 
                      interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                      guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await guild.create_text_channel(name=f"客服-{interaction.user.name}", overwrites=overwrites)
        embed = discord.Embed(title="💬 官方客服已專屬為您服務", description="請說明您的問題。處理完畢後，請點擊下方按鈕。", color=discord.Color.orange())
        await channel.send(f"{admin_role.mention if admin_role else ''} {interaction.user.mention}", embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ 已建立頻道：{channel.mention}", ephemeral=True)

# --- 3. 彈窗開單邏輯 ---
class TicketModal(discord.ui.Modal):
    def __init__(self): super().__init__(title="📋 下單登記表", custom_id="ticket_modal_submit")
    item = discord.ui.TextInput(label="1. 欲購買項目", placeholder="例如：尋寶隊", required=True)
    amount = discord.ui.TextInput(label="2. 購買數量", placeholder="例如：5", required=True)
    currency = discord.ui.TextInput(label="3. 支付幣別", placeholder="例如：許願幣", required=True)
    game_id = discord.ui.TextInput(label="4. 遊戲 ID", placeholder="例如：1114514", required=True)
    player = discord.ui.TextInput(label="5. 陪玩人員", placeholder="例如：小明", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        admin_role = discord.utils.get(guild.roles, name="老闆")
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), 
                      interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                      guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)
        embed = discord.Embed(title="📥 收到新訂單預約！", color=discord.Color.green())
        embed.add_field(name="項目", value=self.item.value, inline=False)
        embed.add_field(name="數量", value=self.amount.value, inline=False)
        embed.add_field(name="幣別", value=self.currency.value, inline=False)
        embed.add_field(name="遊戲 ID", value=self.game_id.value, inline=False)
        embed.add_field(name="陪玩", value=self.player.value, inline=False)
        await channel.send(f"{admin_role.mention if admin_role else ''} {interaction.user.mention}", embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ 已建立專屬頻道：{channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="✉️ 點此開單洽詢", style=discord.ButtonStyle.secondary, custom_id="ticket_button")
    async def ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

# --- 4. 系統初始化與指令 ---
@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(DirectTicketView())
    bot.add_view(CloseTicketView())
    print("【系統提示】機器人已啟動！")

@bot.command()
@commands.has_role("老闆")
async def ticket(ctx):
    embed = discord.Embed(title="⚡ X家電競 - 遊戲陪玩服務 ⚡", description="點擊下方按鈕開始諮詢（需填寫表單）。", color=discord.Color.blue())
    await ctx.send(embed=embed, view=TicketView())

@bot.command()
@commands.has_role("老闆")
async def support(ctx):
    embed = discord.Embed(title=" 🛠️ 聯絡官方客服面板 🛠️", description="若有問題，請點擊下方按鈕直接建立專屬客服單。", color=discord.Color.orange())
    await ctx.send(embed=embed, view=DirectTicketView())

# --- 5. Web 服務 ---
app = Flask('')
@app.route('/')
def home(): return "Online"
Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()

bot.run(os.getenv('DISCORD_TOKEN'))
