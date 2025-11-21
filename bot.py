import os
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import asyncio
from discord import FFmpegPCMAudio

# Load token and server ID from .env
load_dotenv()
token = os.getenv("token")
server_id = (os.getenv("server_id"))

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ---- on start ----
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    guild = discord.Object(id=server_id)
    await bot.tree.sync(guild=guild)
    print(f"🔁 Synced commands to server {server_id}")

    commands_list = await bot.tree.fetch_commands(guild=guild)
    for cmd in commands_list:
        await cmd.edit(default_member_permissions=None)
    print("✅ Set default permissions for everyone")

    # Start the background sound loop
    bot.loop.create_task(play_random_loop())
    print("🎵 Background sound loop started")

    # start the background snitch task
    audit_log_watcher.start()
    print("🐍 Snitching Active")


# ---- Join Channel ----
@bot.tree.command(
    name="joinchannel",
    description="Bot joins the selected voice channel."
)
@app_commands.describe(channel="Select a voice channel for the bot to join")
async def joinchannel(interaction: discord.Interaction, channel: discord.VoiceChannel):
    voice_client = interaction.guild.voice_client
    try:
        if voice_client:
            await voice_client.move_to(channel)
            await interaction.response.send_message(f"🔄 Moved to **{channel.name}**")
            print(f"🔄 Moved to **{channel.name}**")
        else:
            await channel.connect(timeout=15, reconnect=True)
            await interaction.response.send_message(f"🎧 Joined **{channel.name}**")
            print(f"🎧 Joined **{channel.name}**")
    except asyncio.TimeoutError:
        await interaction.response.send_message("❌ Connection to the voice channel timed out.")
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Error: {type(e).__name__}: {e}")


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
        print("👋 Disconnected. Bye Bitches")
    else:
        await interaction.response.send_message("❌ I'm not in a voice channel.")
        print("f❌ I'm not in a voice channel.")


# ---- random sound loop ----
async def play_random_loop():
    await bot.wait_until_ready()
    sounds_folder = "sounds"

    # Human-friendly chance format: "1/10" = 1 in 10 chance
    sound_chances = {
        "nigga stfu.mp3": "10/1000",
        "scream.mp3": "50/1000",
        "nothing": "940/1000",
        "Open Chest (Minecraft)  Sound Effect.mp3": "0/1000",
        "Kaynerapeyou.m4a": "0/1000",
        "gulp.m4a": "0/1000",
    }

    while not bot.is_closed():
        try:
            for guild in bot.guilds:
                voice_client = guild.voice_client
                if voice_client and not voice_client.is_playing():
                    # Include both files and "nothing"
                    sound_files = [
                        f for f in os.listdir(sounds_folder)
                        if f.endswith((".mp3", ".wav", ".m4a"))
                    ]
                    sound_files.append("nothing")

                    # Convert "1/x" style chances into numeric weights
                    weights = []
                    for f in sound_files:
                        chance = sound_chances.get(f, "1/10")  # default chance if missing
                        num, denom = map(float, chance.split("/"))
                        weights.append(num / denom)

                    # 🎲 Choose a sound or silence based on weighted chances
                    random_sound = random.choices(sound_files, weights=weights, k=1)[0]

                    if random_sound == "nothing":
                        print("😶 Stayed silent this interval")
                        continue

                    file_path = os.path.join(sounds_folder, random_sound)

                    # Play sound
                    source = FFmpegPCMAudio(file_path)
                    voice_client.play(source)
                    print(f"🎶 Played: {random_sound} (chance={sound_chances.get(random_sound, '1/10')})")

            # Wait 10 minutes between checks
            await asyncio.sleep(600)


        except Exception as e:
            print(f"⚠️ Error in play_random_loop: {e}")
            await asyncio.sleep(10)


# ---- random reply bot ----
@bot.event
async def on_message(message):
    # Ignore its own messages
    if message.author == bot.user:
        return

    # 1 in 100 chance to reply
    if random.randint(1, 100) == 1:
        responses = [
            "fuck you",
            "🍆💦 👩‍🦰 <---- your mom",
            "and?",
            "Cool!",
            "Wtf?",
            "please elaborate",
            "..."
        ]
        await message.reply(random.choice(responses))

    # Ensures other commands still work
    await bot.process_commands(message)


# ---- snitch bot ----
AUDIT_LOG_CHANNEL_ID = 1426746016559927308
CHECK_INTERVAL = 1  # seconds between checks

# Store last known audit log entry IDs for each guild
last_audit_ids = {}

# helper to post to audit log
async def post_audit_entry(guild, entry: discord.AuditLogEntry):
    """Send a formatted embed for an audit log entry with details and location."""
    channel = guild.get_channel(AUDIT_LOG_CHANNEL_ID)
    if not channel:
        return

    action_name = str(entry.action).replace("AuditLogAction.", "").replace("_", " ").title()

    # Target (fallback to extra if target is None)
    target_name = str(entry.target) if entry.target else "Unknown"
    if target_name == "Unknown" and hasattr(entry, "extra") and entry.extra:
        target_name = str(entry.extra)

    embed = discord.Embed(
        title=f"📝 {action_name}",
        color=discord.Color.blurple(),
        timestamp=entry.created_at
    )
    embed.add_field(name="User", value=entry.user.mention if entry.user else "Unknown", inline=False)
    embed.add_field(name="Target", value=target_name, inline=False)

    if entry.reason:
        embed.add_field(name="Reason", value=entry.reason, inline=False)

    # Include location if possible
    location = None
    if entry.action in (
        discord.AuditLogAction.member_update,
        discord.AuditLogAction.member_role_update,
        discord.AuditLogAction.member_move,
        discord.AuditLogAction.member_disconnect
    ):
        # Voice channel
        if hasattr(entry.target, "voice") and entry.target.voice and entry.target.voice.channel:
            location = entry.target.voice.channel.name
    elif entry.action in (
        discord.AuditLogAction.message_delete,
        discord.AuditLogAction.message_bulk_delete
    ):
        # Text channel
        location = getattr(entry.extra, "channel", None)
        if location:
            location = location.name
    if location:
        embed.add_field(name="Location", value=location, inline=False)

    # Detailed changes for member updates
    details = []
    if entry.action in (discord.AuditLogAction.member_update, discord.AuditLogAction.member_role_update) and entry.changes:
        before = getattr(entry.changes, "before", None)
        after = getattr(entry.changes, "after", None)
        if before and after:
            # Nickname
            if getattr(before, "nick", None) != getattr(after, "nick", None):
                details.append(f"**Nickname**: `{before.nick}` → `{after.nick}`")
            # Mute / Deaf
            if getattr(before, "mute", None) != getattr(after, "mute", None):
                details.append(f"**Server Mute**: `{before.mute}` → `{after.mute}`")
            if getattr(before, "deaf", None) != getattr(after, "deaf", None):
                details.append(f"**Server Deafen**: `{before.deaf}` → `{after.deaf}`")
            # Timeout
            if getattr(before, "timed_out_until", None) != getattr(after, "timed_out_until", None):
                details.append(f"**Timeout**: `{before.timed_out_until}` → `{after.timed_out_until}`")
            # Roles
            before_roles = getattr(before, "roles", [])
            after_roles = getattr(after, "roles", [])
            added_roles = [r.name for r in after_roles if r not in before_roles]
            removed_roles = [r.name for r in before_roles if r not in after_roles]
            if added_roles:
                details.append(f"➕ Roles added: {', '.join(added_roles)}")
            if removed_roles:
                details.append(f"➖ Roles removed: {', '.join(removed_roles)}")

    if details:
        embed.add_field(name="Changes", value="\n".join(details)[:1024], inline=False)

    await channel.send(embed=embed)

# audit log watcher
@tasks.loop(seconds=CHECK_INTERVAL)
async def audit_log_watcher():
    """Periodically check for new audit log entries."""
    for guild in bot.guilds:
        try:
            async for entry in guild.audit_logs(limit=1):
                if guild.id not in last_audit_ids or entry.id != last_audit_ids[guild.id]:
                    last_audit_ids[guild.id] = entry.id
                    await post_audit_entry(guild, entry)
        except discord.Forbidden:
            print(f"❌ Missing permission to view audit log in {guild.name}")
        except Exception as e:
            print(f"⚠️ Error checking audit logs in {guild.name}: {e}")

# server mutes/deafens/timeouts
@bot.event

@bot.event
async def on_member_update(before, after):
    if before.voice is None or after.voice is None:
        return

    changes = []
    if before.voice.mute != after.voice.mute:
        changes.append(f"mute set to {after.voice.mute}")
    if before.voice.deaf != after.voice.deaf:
        changes.append(f"deafen set to {after.voice.deaf}")

    if changes:
        channel = after.guild.get_channel(AUDIT_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"🔈 {after.mention} voice update ({', '.join(changes)})")


# ---- run bot ----
bot.run(token)


#git add . && git commit -m "Committing Yippee" && git push

