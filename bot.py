import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from flask import Flask
from threading import Thread

# 設定
STAFF_ROLE_ID = 123456789012345678  # 請替換為您的員工身分組 ID
REVIEW_CHANNEL_ID = 1523692423790727219

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_overwrites(interaction: discord.Interaction):
    """取得基礎頻道權限設定"""
    staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
    return {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

# --- 1. 評價視窗 ---
class ReviewModal(discord.ui.Modal, title='服務評價'):
    score = discord.ui.TextInput(label='請評分 (1-5星)', placeholder='請輸入 1-5', min_length=1, max_length=1)
    comment = discord.ui.TextInput(label='心得分享', style=discord.TextStyle.paragraph, placeholder='您的建議對我們很重要！')

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.score.value)
            if not (1 <= val <= 5): raise ValueError
        except ValueError:
            return await interaction.response.send_message("請輸入正確的 1-5 數字！", ephemeral=True)

        channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
        embed = discord.Embed(title="✨ 新評價到來！", color=discord.Color.gold())
        embed.add_field(name="客戶", value=interaction.user.mention, inline=False)
        embed.add_field(name="評分", value="⭐" * val, inline=False)
        embed.add_field(name="心得", value=self.comment.value, inline=False)
        if channel: await channel.send(embed=embed)
        
        await interaction.response.send_message("感謝好評！頻道將在 5 秒後刪除。", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- 2. 關單邏輯 ---
class CloseTicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🔒 關閉客服單", style=discord.ButtonStyle.danger, custom_id="unique_close_btn")
    async def close_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚧 5 秒後刪除頻道...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- 3. 開單邏輯 ---
class TicketModal(discord.ui.Modal, title="📋 下單登記表"):
    item = discord.ui.TextInput(label="欲購買項目", placeholder="例如：尋寶隊")
    amount = discord.ui.TextInput(label="購買數量")
    currency = discord.ui.TextInput(label="支付幣別")
    game_id = discord.ui.TextInput(label="遊戲 ID")
    player = discord.ui.TextInput(label="指定陪玩人員")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = await interaction.guild.create_text_channel(
            name=f"order-{interaction.user.name}", 
            overwrites=get_overwrites(interaction)
        )
        embed = discord.Embed(title="📥 收到新訂單！", color=discord.Color.green())
        embed.add_field(name="項目", value=self.item.value)
        embed.add_field(name="資訊", value=f"數量:{self.amount.value}, 幣別:{self.currency.value}\nID:{self.game_id.value}\n人員:{self.player.value}")
        await channel.send(f"{interaction.user.mention} 員工已接單。", embed=embed, view=CloseTicketView())
        await interaction.followup.send(f"✅ 已建立頻道：{channel.mention}", ephemeral=True)

# --- 4. 初始化 ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    bot.add_view(TicketView())
    bot.add_view(DirectTicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(ReviewButtonView())
    print("【系統】機器人已啟動")

# (省略重複的 View 定義，保持結構一致)
# ... 其餘程式碼結構維持您原有的即可 ...

app = Flask('')
@app.route('/')
def home(): return "Online"
Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
bot.run(os.getenv('DISCORD_TOKEN'))
