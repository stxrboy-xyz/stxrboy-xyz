import discord
from discord.ext import commands
import mysql.connector
import os
from flask import Flask
from threading import Thread

# ===== Flask dummy server to keep Render Web Service alive =====
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# ===== Database Configuration =====
DB_HOST = "ovh-bom.opfw.me"
DB_PORT = 3306
DB_USER = "pristine_tundra"
DB_PASS = "NzMfXaj6B7AqrhqV"
DB_NAME = "pristine_tundra"

# ===== Bot Configuration =====
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ALLOWED_ROLE_ID = 1352273949349908491  # Only users with this role ID can use the command

intents = discord.Intents.default()
intents.members = True  # Required for fetching member roles
intents.guilds = True
intents.messages = True
intents.message_content = True  # Required to read message content

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== MySQL Connection =====
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

# ===== Bot Events & Commands =====
@bot.event
async def on_ready():
    print(f"✅ Bot is ready. Logged in as {bot.user}")

@bot.command()
async def superadmin(ctx, action=None, member: discord.Member = None):
    if not ctx.author.get_role(ALLOWED_ROLE_ID):
        await ctx.send("🚫 You do not have permission to use this command.")
        return

    if action not in ["add", "remove"] or member is None:
        await ctx.send("❌ Usage: `!superadmin add @user` or `!superadmin remove @user`")
        return

    discord_id = str(member.id)
    new_value = 1 if action == "add" else 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check current value
        cursor.execute("SELECT is_super_admin FROM users WHERE discord_id = %s", (discord_id,))
        result = cursor.fetchone()

        if not result:
            await ctx.send("❌ User not found in the database.")
        elif result[0] == new_value:
            await ctx.send(f"⚠️ {member.display_name} already has superadmin set to `{new_value}`.")
        else:
            cursor.execute("UPDATE users SET is_super_admin = %s WHERE discord_id = %s", (new_value, discord_id))
            conn.commit()
            await ctx.send(f"✅ {member.display_name} superadmin set to `{new_value}`.")

        cursor.close()
        conn.close()

    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

# ===== Start Everything =====
def start_bot():
    bot.run(BOT_TOKEN)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    start_bot()
