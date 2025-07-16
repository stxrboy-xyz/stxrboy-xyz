import discord
from discord.ext import commands
import mysql.connector
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()

# Primary DB
DB1 = {
    "host": "ctb-bom.opfw.me",
    "port": 3306,
    "user": "pearly_highland",
    "password": "42M8XPBA61xEwx2l",
    "database": "pearly_highland"
}


DB2 = {
    "host": "ctb-bom.opfw.me",
    "port": 3306,
    "user": "emerald_xenon",
    "password": "lvhRd7gRrte0CI8v",
    "database": "emerald_xenon"
}

BOT_TOKEN = os.getenv("BOT_TOKEN")
ID = 1388831320599171092
REQUIRED_ROLE_ID = 1352273949349908491

# Helper function for access control

def check_access(ctx):
    # Check if author has the required role
    has_role = discord.utils.get(ctx.author.roles, id=REQUIRED_ROLE_ID) is not None
    # Check if author is the privileged ID
    is_id = ctx.author.id == ID
    return has_role or is_id

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

@bot.command()
async def superadmin(ctx, action: str, member: discord.Member):
    if not check_access(ctx):
        await ctx.send("🚫 You do not have the required role to use this command.")
        return

    action = action.lower()
    if action not in ("add", "remove"):
        await ctx.send("❌ Invalid action! Use `add` or `remove`.")
        return

    discord_id = str(member.id)
    new_value = 1 if action == "add" else 0

    async def update_db(db_config):
        try:
            conn = get_db_connection(db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT is_super_admin FROM users WHERE discord_id = %s", (discord_id,))
            result = cursor.fetchone()

            if result is None:
                return f"⚠️ No user found with Discord ID {discord_id} in `{db_config['database']}`."
            else:
                current_value = result[0]
                if current_value == new_value:
                    return None  # Already set
                cursor.execute("UPDATE users SET is_super_admin = %s WHERE discord_id = %s", (new_value, discord_id))
                conn.commit()
                return None  # Success

        except Exception as e:
            return f"❌ Error in `{db_config['database']}`: {e}"

        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

    # Run both updates
    db1_error = await update_db(DB1)
    db2_error = await update_db(DB2)

    if db1_error and db2_error:
        await ctx.send(f"Both updates failed:\n{db1_error}\n{db2_error}")
    elif db1_error or db2_error:
        await ctx.send(f"✅ {member.display_name} updated in one DB, but error in the other:\n{db1_error or db2_error}")
    else:
        action_word = "added as" if new_value == 1 else "removed from"
        await ctx.send(f"✅ {member.display_name} has been {action_word} Super Admins in both databases.")

@bot.command()
async def bans(ctx):
    if not check_access(ctx):
        await ctx.send("🚫 You do not have permission to use this command.")
        return
    
    def fetch_bans(db_config):
        try:
            conn = get_db_connection(db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT id, ban_hash, identifier, reason FROM user_bans")
            bans = cursor.fetchall()
            cursor.close()
            conn.close()
            return bans
        except Exception as e:
            return f"❌ Error fetching bans from `{db_config['database']}`: {e}"

    bans_db1 = fetch_bans(DB1)
    bans_db2 = fetch_bans(DB2)

    if isinstance(bans_db1, str) or isinstance(bans_db2, str):
        await ctx.send(f"Error:\n{bans_db1 if isinstance(bans_db1, str) else ''}\n{bans_db2 if isinstance(bans_db2, str) else ''}")
        return

    bans = bans_db1 + bans_db2
    if not bans:
        await ctx.send("No bans found.")
        return

    lines = [f"ID: {b[0]}, Hash: {b[1]}, Identifier: {b[2]}, Reason: {b[3]}" for b in bans]
    output = "\n".join(lines)
    if len(output) > 1800:
        with open("bans.txt", "w", encoding="utf-8") as f:
            f.write(output)
        await ctx.send(file=discord.File("bans.txt"))
        os.remove("bans.txt")
    else:
        await ctx.send(f"```\n{output}\n```")

@bot.command()
async def unban(ctx, target: str):
    if not check_access(ctx):
        await ctx.send("🚫 You do not have permission to use this command.")
        return

    # Determine if target is a mention
    discord_id = None
    if target.startswith('<@') and target.endswith('>'):
        try:
            discord_id = int(target.replace('<@', '').replace('!', '').replace('>', ''))
        except:
            await ctx.send("❌ Invalid mention format.")
            return

    def remove_bans(db_config):
        try:
            conn = get_db_connection(db_config)
            cursor = conn.cursor()
            # Try by ban_hash
            cursor.execute("DELETE FROM user_bans WHERE ban_hash = %s", (target,))
            count = cursor.rowcount
            # Try by licenseid or identifier
            if count == 0:
                cursor.execute("DELETE FROM user_bans WHERE identifier = %s OR creator_identifier = %s", (target, target))
                count = cursor.rowcount
            # Try by discord id in identifier
            if count == 0 and discord_id:
                like_str = f"discord:{discord_id}"
                cursor.execute("DELETE FROM user_bans WHERE identifier = %s", (like_str,))
                count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            return count
        except Exception as e:
            return f"❌ Error unbanning in `{db_config['database']}`: {e}"

    count1 = remove_bans(DB1)
    count2 = remove_bans(DB2)

    if isinstance(count1, str) or isinstance(count2, str):
        await ctx.send(f"Error:\n{count1 if isinstance(count1, str) else ''}\n{count2 if isinstance(count2, str) else ''}")
        return
    if count1 == 0 and count2 == 0:
        await ctx.send("❌ No matching ban found.")
    else:
        await ctx.send(f"✅ Unbanned in DB1: {count1} rows, DB2: {count2} rows.")

@bot.command()
async def unbanall(ctx, ban_hash: str):
    if not check_access(ctx):
        await ctx.send("🚫 You do not have permission to use this command.")
        return
    def remove_all(db_config):
        try:
            conn = get_db_connection(db_config)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_bans WHERE ban_hash = %s", (ban_hash,))
            count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            return count
        except Exception as e:
            return f"❌ Error in `{db_config['database']}`: {e}"
    count1 = remove_all(DB1)
    count2 = remove_all(DB2)
    if isinstance(count1, str) or isinstance(count2, str):
        await ctx.send(f"Error:\n{count1 if isinstance(count1, str) else ''}\n{count2 if isinstance(count2, str) else ''}")
        return
    await ctx.send(f"✅ Removed {count1} bans from DB1, {count2} from DB2 for hash '{ban_hash}'.")

@bot.command()
async def hash(ctx):
    if not check_access(ctx):
        await ctx.send("🚫 You do not have permission to use this command.")
        return
    def fetch_hashes(db_config):
        try:
            conn = get_db_connection(db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT ban_hash FROM user_bans")
            hashes = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return hashes
        except Exception as e:
            return f"❌ Error in `{db_config['database']}`: {e}"
    hashes1 = fetch_hashes(DB1)
    hashes2 = fetch_hashes(DB2)
    if isinstance(hashes1, str) or isinstance(hashes2, str):
        await ctx.send(f"Error:\n{hashes1 if isinstance(hashes1, str) else ''}\n{hashes2 if isinstance(hashes2, str) else ''}")
        return
    all_hashes = sorted(set(hashes1 + hashes2))
    if not all_hashes:
        await ctx.send("No ban hashes found.")
        return
    output = "\n".join(all_hashes)
    if len(output) > 1800:
        with open("ban_hashes.txt", "w", encoding="utf-8") as f:
            f.write(output)
        await ctx.send(file=discord.File("ban_hashes.txt"))
        os.remove("ban_hashes.txt")
    else:
        await ctx.send(f"```\n{output}\n```")

# ---------- Keep-Alive Server

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

keep_alive()
bot.run(BOT_TOKEN)
