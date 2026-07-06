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

# --- 1. 關單邏輯 ---
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # 持久化

    @discord.ui.button(label="🔒 關閉客服單", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="老闆")
        if role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 只有「老闆」有權限關閉！", ephemeral=True)
            return

        await interaction.response.send_message("🚧 5 秒後刪除頻道...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- 2. 【全新功能】點擊直接開單（不跳彈窗） ---
class DirectTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # 持久化

    @discord.ui.button(label="🛠️ 聯絡官方客服", style=discord.ButtonStyle.primary, custom_id="direct_ticket_button")
    async def direct_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. 立即延遲回應，防止建立頻道時間過長導致超時
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        admin_role = discord.utils.get(guild.roles, name="老闆")
        
        # 2. 設定頻道權限（只允許該用戶、機器人、老闆查看）
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # 3. 建立頻道
        channel = await guild.create_text_channel(name=f"客服-{interaction.user.name}", overwrites=overwrites)
        
        # 4. 在新頻道發送歡迎訊息與關單按鈕
        embed = discord.Embed(
            title="💬 官方客服已專屬為您服務", 
            description="請在下方說明您的問題，管理團隊將會盡快回覆您。\n處理完畢後，請點擊下方按鈕關閉頻道。", 
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"申請人: {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        
        await channel.send(f"{admin_role.mention if admin_role else ''} {interaction.user.mention} 您好！", embed=embed, view=CloseTicketView())
        
        # 5. 回覆用戶建立成功
        await interaction.followup.send(f"✅ 已為您建立專屬客服頻道：{channel.mention}", ephemeral=True)

# --- 3. 原有的彈窗開單邏輯 ---
class TicketModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📋 下單登記表", custom_id="ticket_modal_submit")

    item = discord.ui.TextInput(label="1. 欲購買項目", placeholder="例：尋寶隊", required=True, custom_id="modal_item")
    amount = discord.ui.TextInput(label="2. 購買數量", placeholder="例：5", required=True, custom_id="modal_amount")
    currency = discord.ui.TextInput(label="3. 支付幣別", placeholder="例：許願幣", required=True, custom_id="modal_currency")
    game_id = discord.ui.TextInput(label="4. 遊戲 ID", placeholder="例：1114514", required=True, custom_id="modal_game_id")
    player = discord.ui.TextInput(label="5. 陪玩人員", placeholder="例：小明", required=True, custom_id="modal_player")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        admin_role = discord.utils.get(guild.roles, name="老闆")
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)
        
        embed = discord.Embed(title="📥 收到新訂單預約！", color=discord.Color.green())
        embed.add_field(name="項目", value=self.item.value, inline=False)
        embed.add_field(name="數量", value=self.amount.value, inline=False)
        embed.add_field(name="幣別", value=self.currency.value, inline=False)
        embed.add_field(name="遊戲 ID", value=self.game_id.value, inline=False)
        embed.add_field(name="陪玩", value=self.player.value, inline=False)
        
        await channel.send(f"{admin_role.mention if admin_role else ''} {interaction.user.mention} 您好！", embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ 已建立專屬頻道：{channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✉️ 點此開單洽詢", style=discord.ButtonStyle.secondary, custom_id="ticket_button")
    async def ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

# --- 4. 系統初始化與指令 ---
@bot.event
async def on_ready():
    # 註冊所有持久化視圖（包含新舊按鈕）
    bot.add_view(TicketView())
    bot.add_view(DirectTicketView())
    bot.add_view(CloseTicketView())
    print("【系統提示】機器人已啟動！")

# 指令 1：發送原本的下單登記面板
@bot.command()
@commands.has_role("老闆")
async def ticket(ctx):
    embed = discord.Embed(title="⚡ X家電競 - 遊戲陪玩服務 ⚡", description="點擊下方按鈕開始諮詢（需填寫表單）。", color=discord.Color.blue())
    await ctx.send(embed=embed, view=TicketView())

# 指令 2：發送「直接建立頻道」的客服面板
@bot.command()
@commands.has_role("老闆")
async def support(ctx):
    embed = discord.Embed(title=" 🛠️ 聯絡官方客服面板 🛠️", description="若有任何權限、申訴或其他問題，請點擊下方按鈕直接建立專屬客服單頻道。", color=discord.Color.orange())
    await ctx.send(embed=embed, view=DirectTicketView())

# --- 5. Web 服務 ---
app = Flask('')
@app.route('/')
def home(): return "Online"
Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()

bot.run(os.getenv('DISCORD_TOKEN'))
