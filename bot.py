import os
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

# Initialize Pyrogram Bot
bot = Client("bulk_thumbnail_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask app for web hosting (keep bot alive)
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 Bot is running!"

# Directory for storing user thumbnails
THUMB_DIR = "thumbnails"
os.makedirs(THUMB_DIR, exist_ok=True)

# ✅ Set Thumbnail Command
@bot.on_message(filters.command("set_thumb") & filters.photo)
async def set_thumbnail(client, message):
    file_path = os.path.join(THUMB_DIR, f"{message.from_user.id}.jpg")
    await client.download_media(message, file_name=file_path)
    await message.reply_text("✅ Thumbnail saved successfully!")

# Function to modify audio track names
def modify_audio_tracks(input_file, output_file):
    try:
        print(f"🔄 Modifying audio track: {input_file} ➡️ {output_file}")
        ffmpeg.input(input_file).output(output_file, codec="copy", map="0", metadata="title=[@Animes2u]").run(overwrite_output=True)
        return output_file if os.path.exists(output_file) else None
    except Exception as e:
        print(f"❌ FFmpeg Error: {e}")
        return None

# ✅ File Rename & Thumbnail Change
@bot.on_message(filters.document)
async def change_thumbnail(client, message):
    thumb_path = os.path.join(THUMB_DIR, f"{message.from_user.id}.jpg")

    # Check if thumbnail exists
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

    # Modify audio track names
    modified_file_path = os.path.join(os.path.dirname(file_path), f"modified_{os.path.basename(file_path)}")
    modified_file = modify_audio_tracks(file_path, modified_file_path)

    if not modified_file or not os.path.exists(modified_file):
        await message.reply_text("❌ Failed to modify audio tracks.")
        return

    print(f"📤 Sending file: {modified_file}")

    try:
        # Send renamed file with thumbnail
        await client.send_document(
            chat_id=message.chat.id,
            document=modified_file,
            thumb=thumb_path if os.path.exists(thumb_path) else None,
            file_name=new_filename,
            caption=f"✅ Renamed: {new_filename}
