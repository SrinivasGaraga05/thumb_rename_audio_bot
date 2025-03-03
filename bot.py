import os
import asyncio
import re
import ffmpeg
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

# Initialize Pyrogram Bot (✅ No user restrictions)
bot = Client("bulk_thumbnail_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask app for web hosting (public access)
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 Bot is running for everyone!"

# Directory for storing user thumbnails
THUMB_DIR = "thumbnails"
os.makedirs(THUMB_DIR, exist_ok=True)

# Global variable to enable/disable processing
processing_enabled = True

# ✅ Set Thumbnail (Public Use)
@bot.on_message(filters.command("set_thumb") & filters.photo)
async def set_thumbnail(client, message):
    file_path = os.path.join(THUMB_DIR, f"{message.from_user.id}.jpg")
    await client.download_media(message.photo, file_name=file_path)
    await message.reply_text("✅ Thumbnail saved permanently! Use /delete_thumb to remove it.")

# ✅ Delete Thumbnail
@bot.on_message(filters.command("delete_thumb"))
async def delete_thumbnail(client, message):
    file_path = os.path.join(THUMB_DIR, f"{message.from_user.id}.jpg")
    if os.path.exists(file_path):
        os.remove(file_path)
        await message.reply_text("🗑️ Thumbnail deleted successfully!")
    else:
        await message.reply_text("⚠️ No saved thumbnail found!")

# ✅ Stop Processing
@bot.on_message(filters.command("stop"))
async def stop_processing(client, message):
    global processing_enabled
    processing_enabled = False
    await message.reply_text("⏸️ Bot has stopped processing files. Use /start to resume.")

# ✅ Resume Processing
@bot.on_message(filters.command("start"))
async def start_processing(client, message):
    global processing_enabled
    processing_enabled = True
    await message.reply_text("▶️ Bot has resumed processing files. Send a file to rename & change its thumbnail.")

# ✅ Process File for All Users
@bot.on_message(filters.document)
async def change_thumbnail(client, message):
    global processing_enabled

    if not processing_enabled:
        await message.reply_text("⏸️ Bot is currently stopped. Use /start to resume processing.")
        return

    thumb_path = os.path.join(THUMB_DIR, f"{message.from_user.id}.jpg")

    # Check if a thumbnail exists
    if not os.path.exists(thumb_path):
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

    # Extract filename & extension
    file_name, file_ext = os.path.splitext(message.document.file_name)

    # Preserve valid brackets like [720p], [e20]
    valid_brackets = re.findall(r"\[[\w\s\d]+\]", file_name)

    # Remove unwanted tags inside brackets (e.g., [xyz])
    file_name = re.sub(r"\[[^\d\s]+\]", "", file_name)

    # Remove any word starting with '@'
    file_name = re.sub(r"@\S+", "", file_name)

    # Trim extra spaces
    file_name = file_name.strip()

    # Reattach valid brackets
    file_name += " " + " ".join(valid_brackets)

    # Ensure filename starts with [@Animes2u]
    new_filename = f"{DEFAULT_KEYWORD}{file_name}{file_ext}"
    new_file_path = f"processed_{file_name}{file_ext}"

    try:
        # 🔹 Change Audio Track Name Using FFmpeg
        (
            ffmpeg
            .input(file_path)
            .output(new_file_path, map='0', metadata='title=[@Animes2u] Audio')
            .run(overwrite_output=True)
        )

        # Send processed file
        await client.send_document(
            chat_id=message.chat.id,
            document=new_file_path,
            thumb=thumb_path,
            file_name=new_filename,
            caption=f"✅ Renamed: {new_filename} (Audio Track Updated)",
        )

        await message.reply_text("✅ Done! Audio track name updated.")

        # ✅ Delete temp files
        os.remove(file_path)
        os.remove(new_file_path)

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# Run Flask for public access
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    print(f"🌍 Public Bot Running on Port {port}...")
    web_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    print("🤖 Public Bot is starting...")

    # Start Flask server
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start Telegram Bot (Open to All)
    try:
        bot.start()
        print("✅ Bot is online and accessible to everyone.")
    except Exception as e:
        print(f"❌ Bot startup failed: {e}")

    # Keep bot running
    idle()

    print("🛑 Bot stopped.")
    bot.stop()
