import os
import json
import re
import asyncio
from pyrogram import Client, filters, idle
from flask import Flask
from threading import Thread

# Load environment variables
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_KEYWORD = "[@Animes2u] "

# Ensure required environment variables are set
if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("❌ Missing API_ID, API_HASH, or BOT_TOKEN.")

# Initialize Pyrogram Bot
bot = Client("file_rename_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask app for web hosting (keep the bot alive)
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 Bot is running!"

# Directory for storing user thumbnails
THUMB_DIR = "thumbnails"
THUMB_DB = "thumb_db.json"
os.makedirs(THUMB_DIR, exist_ok=True)

# Load thumbnail database
def load_thumb_db():
    if os.path.exists(THUMB_DB):
        with open(THUMB_DB, "r") as f:
            return json.load(f)
    return {}

# Save thumbnail database
def save_thumb_db(db):
    with open(THUMB_DB, "w") as f:
        json.dump(db, f, indent=4)

# ✅ Set Thumbnail Command (Permanent)
@bot.on_message(filters.command("set_thumb") & filters.photo)
async def set_thumbnail(client, message):
    file_path = os.path.join(THUMB_DIR, f"{message.from_user.id}.jpg")
    
    # Download the thumbnail
    await client.download_media(message, file_name=file_path)
    
    # Save to database
    thumb_db = load_thumb_db()
    thumb_db[str(message.from_user.id)] = file_path
    save_thumb_db(thumb_db)

    await message.reply_text("✅ Thumbnail saved **permanently**! Use `/del_thumb` to remove it.")

# ✅ Delete Thumbnail Command
@bot.on_message(filters.command("del_thumb"))
async def delete_thumbnail(client, message):
    thumb_db = load_thumb_db()
    user_id = str(message.from_user.id)

    if user_id in thumb_db:
        os.remove(thumb_db[user_id])  # Delete file
        del thumb_db[user_id]  # Remove from database
        save_thumb_db(thumb_db)
        await message.reply_text("✅ Your thumbnail has been **deleted**.")
    else:
        await message.reply_text("⚠️ No thumbnail found to delete!")

# ✅ Pause & Resume Bot
bot_paused = False

@bot.on_message(filters.command("pause"))
async def pause_bot(client, message):
    global bot_paused
    bot_paused = True
    await message.reply_text("⏸ Bot is **paused**. It will not process files until resumed.")

@bot.on_message(filters.command("resume"))
async def resume_bot(client, message):
    global bot_paused
    bot_paused = False
    await message.reply_text("▶ Bot is **resumed**. Now processing files again.")

# ✅ File Rename with Permanent Thumbnail
@bot.on_message(filters.document)
async def rename_file(client, message):
    global bot_paused
    if bot_paused:
        await message.reply_text("⏸ Bot is **paused**. Use `/resume` to enable it.")
        return

    thumb_db = load_thumb_db()
    thumb_path = thumb_db.get(str(message.from_user.id))  # Get user's saved thumbnail

    # Check if user has a saved thumbnail
    if not thumb_path or not os.path.exists(thumb_path):
        await message.reply_text("⚠️ No thumbnail found! Use /set_thumb to set one.")
        return

    # Check file size (max 2GB)
    file_size = message.document.file_size
    max_size = 2 * 1024 * 1024 * 1024  # 2GB
    if file_size > max_size:
        await message.reply_text("❌ File is too large (Max: 2GB).")
        return

    await message.reply_text("🔄 Processing file...")

    # Download the document
    file_path = await client.download_media(message)
    if not file_path:
        await message.reply_text("❌ Failed to download file.")
        return

    print(f"📥 Downloaded file: {file_path}")

    # Extract filename & clean it
    file_name, file_ext = os.path.splitext(message.document.file_name)

    # Keep [E10], [720p], etc., but remove other brackets
    file_name = re.sub(r"\[(?!\d+p|E\d+).*?\]", "", file_name)

    # Remove any word starting with '@'
    file_name = re.sub(r"@\S+", "", file_name)

    # Trim extra spaces
    file_name = file_name.strip()

    # Ensure the filename starts with [Animes2u]
    new_filename = f"{DEFAULT_KEYWORD}{file_name}{file_ext}"

    print(f"📤 Sending renamed file: {new_filename}")

    try:
        # Send renamed file with permanent thumbnail
        await client.send_document(
            chat_id=message.chat.id,
            document=file_path,
            thumb=thumb_path,
            file_name=new_filename,
            caption=f"✅ Renamed: {new_filename}",
            mime_type=message.document.mime_type,
        )
        await message.reply_text("✅ Done! Here is your updated file.")

        # ✅ Delete temp files to free space
        os.remove(file_path)

    except Exception as e:
        await message.reply_text(f"❌ Error sending file: {e}")
        print(f"❌ Error sending file: {e}")

# ✅ Start Command
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "👋 Hello! This bot renames your files and applies a **permanent thumbnail**.\n\n"
        "✅ Use `/set_thumb` to **set a permanent thumbnail**.\n"
        "❌ Use `/del_thumb` to **delete your thumbnail**.\n"
        "⏸ Use `/pause` to **pause the bot**.\n"
        "▶ Use `/resume` to **resume the bot**.\n"
        "📂 Send a file, and it will be renamed and sent back with your thumbnail!"
    )

# Run Flask in a separate thread
def run_flask():
    try:
        port = int(os.environ.get("PORT", 8080))
        print(f"🌍 Starting Flask on port {port}...")
        web_app.run(host="0.0.0.0", port=port)
    except Exception as e:
        print(f"⚠️ Flask server error: {e}")

if __name__ == "__main__":
    print("🤖 Bot is starting...")

    # Start Flask server
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start Telegram Bot
    try:
        bot.start()
        print("✅ Bot is online.")
    except Exception as e:
        print(f"❌ Bot startup failed: {e}")

    # Keep bot running
    idle()

    print("🛑 Bot stopped.")
    bot.stop()
