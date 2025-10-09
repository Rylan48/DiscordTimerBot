import os
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands

# Load token and server ID from .env
load_dotenv()
token = os.getenv("token")
server_id = (os.getenv("server_id"))

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    # Sync slash commands to your guild (server)
    guild = discord.Object(id=server_id)
    await bot.tree.sync(guild=guild)
    print(f"🔁 Synced commands to server {server_id}")

    # Give @everyone default permission for all app commands
    commands_list = await bot.tree.fetch_commands(guild=guild)
    for cmd in commands_list:
        await cmd.edit(default_member_permissions=None)
    print("✅ Set default permissions for everyone")

# ---- Join Channel ----
@bot.tree.command(
    name="joinchannel",
    description="Bot joins the selected voice channel."
)
@app_commands.describe(channel="Select a voice channel for the bot to join")
async def joinchannel(interaction: discord.Interaction, channel: discord.VoiceChannel):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.move_to(channel)
        await interaction.response.send_message(f"🔄 Moved to **{channel.name}**")
    else:
        await channel.connect()
        await interaction.response.send_message(f"Tracking Time In **{channel.name}**")


# ---- Leave Channel ----
@bot.tree.command(
    name="leave",
    description="Bot leaves the current voice channel."
)
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect(force=False)
        await interaction.response.send_message("👋 Disconnected. Bye Bitches")
    else:
        await interaction.response.send_message("❌ I'm not in a voice channel.")


# Run the bot
bot.run(token)
