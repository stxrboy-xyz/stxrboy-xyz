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

# Secondary DB (new one you added)
DB2 = {
    "host": "ctb-bom.opfw.me",
    "port": 3306,
    "user": "emerald_xenon",
    "password": "lvhRd7gRrte0CI8v",
    "database": "emerald_xenon"
}

BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_ROLE_ID = 1352273949349908491

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

# ---------- Keep-Alive Server ----------

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
