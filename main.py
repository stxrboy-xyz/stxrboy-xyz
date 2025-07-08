import discord
from discord.ext import commands, tasks
import mysql.connector
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import time
import asyncio

load_dotenv()

# ---------- DATABASE CONFIGS ----------
# Primary DB
DB1 = {
    "host": "ctb-bom.opfw.me",
    "port": 3306,
    "user": "pearly_highland",
    "password": "42M8XPBA61xEwx2l",
    "database": "pearly_highland"
}

# Secondary DB (to be synced)
DB2 = {
    "host": "ctb-bom.opfw.me",
    "port": 3306,
    "user": "emerald_xenon",
    "password": "lvhRd7gRrte0CI8v",
    "database": "emerald_xenon"
}

BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_ROLE_ID = 1352273949349908491

# ---------- DISCORD BOT SETUP ----------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

def get_db_connection(db_config):
    return mysql.connector.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"]
    )

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    sync_db_loop.start()  # Start the background sync loop

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
        conn = get_db_connection(DB1)
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

# ---------- DATABASE SYNC ----------
def sync_table(table_name, cursor1, cursor2, conn2):
    cursor1.execute(f"SELECT * FROM {table_name}")
    rows = cursor1.fetchall()

    cursor1.execute(f"SHOW COLUMNS FROM {table_name}")
    columns = [col[0] for col in cursor1.fetchall()]
    columns_str = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))

    cursor2.execute(f"DELETE FROM {table_name}")
    if rows:
        insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        cursor2.executemany(insert_query, rows)
        conn2.commit()

    print(f"[{time.ctime()}] ✅ Synced {table_name}: {len(rows)} rows")

def sync_databases():
    try:
        conn1 = get_db_connection(DB1)
        conn2 = get_db_connection(DB2)

        cursor1 = conn1.cursor()
        cursor2 = conn2.cursor()

        cursor1.execute("SHOW TABLES")
        tables = [table[0] for table in cursor1.fetchall()]

        for table in tables:
            try:
                sync_table(table, cursor1, cursor2, conn2)
            except Exception as e:
                print(f"[{time.ctime()}] ❌ Failed to sync table {table}: {e}")

        cursor1.close()
        cursor2.close()
        conn1.close()
        conn2.close()

    except Exception as e:
        print(f"[{time.ctime()}] ❌ DB Sync Error: {e}")

@tasks.loop(minutes=2)
async def sync_db_loop():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, sync_databases)

# ---------- KEEP-ALIVE SERVER ----------
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is alive and syncing every 2 minutes."

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    thread = Thread(target=run)
    thread.start()

keep_alive()
bot.run(BOT_TOKEN)
