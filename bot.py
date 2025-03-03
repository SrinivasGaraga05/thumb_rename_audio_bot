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

# Initialize Pyrogram Bot
bot = Client("bulk_thumbnail_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask app for web hosting (keep the bot alive)
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🤖 Bot is running!"

# Directory for storing user thumbnails
THUMB_DIR = "thumbnails"
os.makedirs(THUMB_DIR, exist_ok=True)

# Global variable to enable/disable processing
processing_enabled = True

# ✅ Set Thumbnail Command (Thumbnail remains permanent)
@bot.on_message(filters.command("set_thumb") & filters.photo)
async def set_thumbnail(client, message):
    file_path = os.path.join(THUMB_DIR, f"{message.from_user.id}.jpg")
    await client.download_media(message.photo, file_name=file_path)
    await message.reply_text("✅ Thumbnail saved permanently! Use /delete_thumb to remove it.")

# ✅ Delete Thumbnail Command
@bot.on_message(filters.command("delete_thumb"))
async def delete_thumbnail(client, message):
    file_path = os.path.join(THUMB_DIR, f"{message.from_user.id}.jpg")
    if os.path.exists(file_path):
        os.remove(file_path)
        await message.reply_text("🗑️ Thumbnail deleted successfully!")
    else:
        await message.reply_text("⚠️ No saved thumbnail found!")

# ✅ Stop Processing Command (Bot stays online but ignores file processing)
@bot.on_message(filters.command("stop"))
async def stop_processing(client, message):
    global processing_enabled
    processing_enabled = False
    await message.reply_text("⏸️ Bot has stopped processing files. Use /start to resume.")

# ✅ Start Processing Command
@bot.on_message(filters.command("start"))
async def start_processing(client, message):
    global processing_enabled
    processing_enabled = True
    awa
