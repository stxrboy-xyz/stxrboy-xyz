import discord
from discord.ext import commands
import mysql.connector

# Your database credentials
DB_HOST = "ovh-bom.opfw.me"
DB_PORT = 3306
DB_USER = "pristine_tundra"
DB_PASS = "NzMfXaj6B7AqrhqV"
DB_NAME = "pristine_tundra"

# Your Discord bot token
BOT_TOKEN = ""

REQUIRED_ROLE_ID = 1352273949349908491  # The role ID allowed to run the command

intents = discord.Intents.default()


bot = commands.Bot(command_prefix="!", intents=intents)

# Connect to MySQL database
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
    print(f"Bot logged in as {bot.user}")

@bot.command()
async def superadmin(ctx, action: str, member: discord.Member):
    # Check if author has the required role
    role = discord.utils.get(ctx.author.roles, id=REQUIRED_ROLE_ID)
    if role is None:
        await ctx.send("You do not have the required role to use this command.")
        return

    action = action.lower()
    if action not in ("add", "remove"):
        await ctx.send("Invalid action! Use `add` or `remove`.")
        return

    discord_id = str(member.id)
    new_value = 1 if action == "add" else 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check current superadmin status
        cursor.execute("SELECT is_super_admin FROM users WHERE discord_id = %s", (discord_id,))
        result = cursor.fetchone()

        if result is None:
            await ctx.send(f"No user found with Discord ID {discord_id}.")
        else:
            current_value = result[0]
            if current_value == new_value:
                state = "already a Super Admin" if new_value == 1 else "already not a Super Admin"
                await ctx.send(f"{member.display_name} is {state}.")
            else:
                cursor.execute("UPDATE users SET is_super_admin = %s WHERE discord_id = %s", (new_value, discord_id))
                conn.commit()
                action_word = "added as" if new_value == 1 else "removed from"
                await ctx.send(f"{member.display_name} has been {action_word} Super Admins.")

        cursor.close()
        conn.close()

    except Exception as e:
        await ctx.send(f"Error updating database: {e}")

bot.run(BOT_TOKEN)

