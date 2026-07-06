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
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 關閉客服單", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="老闆")
        if role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 只有「老闆」有權限關閉！", ephemeral=True)
            return

        await interaction.response.send_message("🚧 5 秒後刪除頻道...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- 2. 彈窗邏輯 (已優化為 defer 模式) ---
class TicketModal(discord.ui.Modal, title="📋 下單登記表"):
    item = discord.ui.TextInput(label="1. 欲購買項目", placeholder="例：尋寶隊", required=True)
    amount = discord.ui.TextInput(label="2. 購買數量", placeholder="例：5", required=True)
    currency = discord.ui.TextInput(label="3. 支付幣別", placeholder="例：許願幣", required=True)
    game_id = discord.ui.TextInput(label="4. 遊戲 ID", placeholder="例：1114514", required=True)
    player = discord.ui.TextInput(label="5. 陪玩人員", placeholder="例：小明", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        # 立即延遲回應，避免超時
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

        # 建立頻道
        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.id}", overwrites=overwrites)
        
        embed = discord.Embed(title="📥 收到新訂單預約！", color=discord.Color.green())
        embed.add_field(name="項目", value=self.item.value, inline=False)
        embed.add_field(name="數量", value=self.amount.value, inline=False)
        embed.add_field(name="幣別", value=self.currency.value, inline=False)
        embed.add_field(name="遊戲 ID", value=self.game_id.value, inline=False)
        embed.add_field(name="陪玩", value=self.player.value, inline=False)
        
        await channel.send(f"{admin_role.mention if admin_role else ''} {interaction.user.mention} 您好！", embed=embed, view=CloseTicketView())
        
        # 使用 followup 發送完成通知
        await interaction.followup.send(f"✅ 已建立專屬頻道：{channel.mention}", ephemeral=True)

# --- 3. 開單面板 ---
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
    print("【系統提示】機器人已啟動！")

@bot.command()
@commands.has_role("老闆")
async def ticket(ctx):
    embed = discord.Embed(title="⚡ X家電競 - 遊戲陪玩服務 ⚡", description="點擊下方按鈕開始諮詢。", color=discord.Color.blue())
    await ctx.send(embed=embed, view=TicketView())

# --- 4. Web 服務 ---
app = Flask('')
@app.route('/')
def home(): return "Online"
Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()

bot.run(os.getenv('DISCORD_TOKEN'))
