import discord
from discord import app_commands
from discord.ext import commands
import json
import os

TOKEN "oMTQ0NjExMjg2MTQ2MTE1MTkzNA.G6d5nI.7oQ-k9HyV4-TvrhkB3zUNUXHAE78MyY4yecrKU"
CONFIG_FILE = "config.json"

# ---------- config ----------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "category_id": None,
                "role_id": None,
                "log_channel_id": None
            }, f, indent=2)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

config = load_config()

# ---------- bot ----------
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"ログイン完了: {bot.user}")

# ---------- 共通チェック ----------
def has_manage_role(interaction: discord.Interaction):
    role_id = config["role_id"]
    if role_id is None:
        return False
    return any(r.id == role_id for r in interaction.user.roles)

# ---------- 設定コマンド ----------
@bot.tree.command(name="setcategory", description="チャンネル作成先カテゴリを設定")
@app_commands.checks.has_permissions(administrator=True)
async def setcategory(interaction: discord.Interaction, category: discord.CategoryChannel):
    config["category_id"] = category.id
    save_config(config)
    await interaction.response.send_message(
        f"✅ カテゴリを **{category.name}** に設定しました",
        ephemeral=True
    )

@bot.tree.command(name="setrole", description="操作可能ロールを設定")
@app_commands.checks.has_permissions(administrator=True)
async def setrole(interaction: discord.Interaction, role: discord.Role):
    config["role_id"] = role.id
    save_config(config)
    await interaction.response.send_message(
        f"✅ 操作ロールを **{role.name}** に設定しました",
        ephemeral=True
    )

@bot.tree.command(name="setlog", description="作成/削除ログ送信先を設定")
@app_commands.checks.has_permissions(administrator=True)
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    config["log_channel_id"] = channel.id
    save_config(config)
    await interaction.response.send_message(
        f"✅ ログチャンネルを {channel.mention} に設定しました",
        ephemeral=True
    )

# ---------- setup ----------
@bot.tree.command(name="setup", description="ユーザーID入力フォームを送信")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, channel: discord.TextChannel):

    if None in (config["category_id"], config["role_id"], config["log_channel_id"]):
        await interaction.response.send_message(
            "⚠ 先に `/setcategory` `/setrole` `/setlog` を設定してください。",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"{channel.mention} にフォームを送信しました。",
        ephemeral=True
    )

    class OpenView(discord.ui.View):
        @discord.ui.button(label="ユーザーID入力フォームを開く", style=discord.ButtonStyle.blurple)
        async def open(self, i: discord.Interaction, _):
            if not has_manage_role(i):
                await i.response.send_message("権限がありません。", ephemeral=True)
                return
            await i.response.send_modal(UserModal())

    await channel.send("👇 管理者専用フォーム", view=OpenView())

# ---------- Modal ----------
class UserModal(discord.ui.Modal, title="Discord ユーザーID入力"):
    user_id = discord.ui.TextInput(label="DiscordユーザーID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        try:
            member = await guild.fetch_member(int(self.user_id.value))
        except:
            await interaction.response.send_message("❌ サーバーに存在しません。", ephemeral=True)
            return

        await interaction.response.send_message(
            f"{member.mention} のチャンネルを作成しますか？",
            view=ConfirmView(member),
            ephemeral=True
        )

# ---------- Confirm ----------
class ConfirmView(discord.ui.View):
    def __init__(self, member):
        super().__init__()
        self.member = member

    @discord.ui.button(label="はい", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, _):
        guild = interaction.guild
        category = guild.get_channel(config["category_id"])
        log = guild.get_channel(config["log_channel_id"])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.member: discord.PermissionOverwrite(read_messages=True, send_messages=False)
        }

        channel = await guild.create_text_channel(
            f"user-{self.member.id}",
            category=category,
            overwrites=overwrites
        )

        fixed_message = (
            f"{self.member.mention}\n"
            "第１試験合格おめでとうございます！\n"
            "つきましては第２面接試験がおりますのでご予約お願いします\n"
            "https://calendar.app.google/HEPXPP8D4pgZFNH17"
        )

        class DeleteView(discord.ui.View):
            @discord.ui.button(label="即削除", style=discord.ButtonStyle.danger)
            async def delete(self, i: discord.Interaction, _):
                if not has_manage_role(i):
                    await i.response.send_message("権限がありません。", ephemeral=True)
                    return
                await channel.delete()
                await log.send(f"🗑 削除: {channel.name}（実行者: {i.user}）")

        await channel.send(fixed_message, view=DeleteView())
        await log.send(f"📁 作成: {channel.mention}（対象: {self.member}）")

        await interaction.response.send_message("✅ 作成しました", ephemeral=True)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, _):
        await interaction.response.send_message("❌ キャンセルしました", ephemeral=True)

# ---------- start ----------
bot.run(TOKEN)
