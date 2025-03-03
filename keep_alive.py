from flask import Flask
from threading import Thread

# Create a Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot is running and alive!"

# Function to run Flask in a separate thread
def run():
    port = 8080  # Default port for web hosting
    app.run(host="0.0.0.0", port=port)

# Start Flask in a separate thread
def keep_alive():
    server = Thread(target=run)
    server.daemon = True
    server.start()
