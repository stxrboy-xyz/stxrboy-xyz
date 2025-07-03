import discord
from discord.ext import commands
import mysql.connector
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()

DB_HOST = "ctb-bom.opfw.me"
DB_PORT = 3306
DB_USER = "pearly_highland"
DB_PASS = "42M8XPBA61xEwx2l"
DB_NAME = "pearly_highland"

BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_ROLE_ID = 1352273949349908491

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")

@bot.command()
async def superadmin(ctx, action: str, member: discord.Member):
    role = discord.utils.get(ctx.author.roles, id=REQUIRED_ROLE_ID)
    if role is None:
        await ctx.send("🚫 You do not have the required role to use this command.")
        return

    action = action.lower()
    if action not in ("add", "remove"):
        await ctx.send("❌ Invalid action! Use `add` or `remove`.")
        return

    discord_id = str(member.id)
    new_value = 1 if action == "add" else 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_super_admin FROM users WHERE discord_id = %s", (discord_id,))
        result = cursor.fetchone()

        if result is None:
            await ctx.send(f"⚠️ No user found with Discord ID {discord_id}.")
        else:
            current_value = result[0]
            if current_value == new_value:
                state = "already a Super Admin" if new_value == 1 else "already not a Super Admin"
                await ctx.send(f"{member.display_name} is {state}.")
            else:
                cursor.execute("UPDATE users SET is_super_admin = %s WHERE discord_id = %s", (new_value, discord_id))
                conn.commit()
                action_word = "added as" if new_value == 1 else "removed from"
                await ctx.send(f"✅ {member.display_name} has been {action_word} Super Admins.")

        cursor.close()
        conn.close()

    except Exception as e:
        await ctx.send(f"⚠️ Error updating database: {e}")

# ---------- Keep-Alive Server for Render + UptimeRobot ----------

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is alive and running!, updated"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    thread = Thread(target=run)
    thread.start()

# Start the Flask server before starting the bot
keep_alive()

# Start the bot
bot.run(BOT_TOKEN)
