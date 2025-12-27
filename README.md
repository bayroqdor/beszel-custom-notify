# Beszel Telegram Monitoring Bot

A custom Telegram bot middleware for [Beszel](https://github.com/henrygd/beszel) monitoring system. 
This bot acts as a bridge between Beszel webhooks and Telegram, providing formatted alerts with OS icons, IP addresses, and real-time system status checks.

## Features

-   **🔔 Enhanced Alerts:** Converts plain text Beszel alerts into beautiful, formatted Telegram messages with status icons (🚨, ⚠️, ✅).
-   **🖥 System Status:** `/status` command fetches real-time server list from Beszel API, showing Up/Down status and OS type (🪟 Windows, 🐧 Linux, 🍎 MacOS).
-   **🧠 Auto-Discovery:** Automatically learns server IP addresses from Beszel API and appends them to alert messages.
-   **🛡 Robust:** Handles connection timeouts and recovers automatically.

## Prerequisites

-   Python 3.8+
-   A running [Beszel](https://github.com/henrygd/beszel) instance.
-   Telegram Bot Token (from [@BotFather](https://t.me/BotFather)).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/bayroqdor/beszel-telegram-bot.git](https://github.com/bayroqdor/beszel-telegram-bot.git)
    cd beszel-telegram-bot
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration:**
    Open `monitor_bot.py` and update the following variables at the top of the file:
    ```python
    TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    CHAT_ID = "YOUR_CHAT_ID_HERE"

    BESZEL_URL = "http://YOUR_BESZEL_IP:8090"
    BESZEL_USER = "admin@example.com"
    BESZEL_PASS = "YOUR_PASSWORD"
    ```

5.  **Run the bot:**
    ```bash
    python3 monitor_bot.py
    ```

## Connecting to Beszel

1.  Log in to your **Beszel Dashboard**.
2.  Go to **Settings** -> **Notifications**.
3.  Add a new notification using the **Generic Webhook** type.
4.  Enter the URL of your bot (ensure the port `5555` is open on your firewall):
    
    ```text
    generic+http://YOUR_BOT_SERVER_IP:5555/webhook
    ```
    *Note: The `generic+http` prefix is important to bypass SSL requirements if you are running locally without HTTPS.*

5.  Click **Test** to verify the connection. You should receive a formatted message in Telegram.

## Running as a Service (Linux Systemd)

To keep the bot running in the background:

1.  Create a service file:
    ```bash
    sudo nano /etc/systemd/system/beszel-bot.service
    ```

2.  Paste the following (adjust paths and user):
    ```ini
    [Unit]
    Description=Beszel Telegram Bot
    After=network.target

    [Service]
    User=your_user
    WorkingDirectory=/path/to/beszel-telegram-bot
    ExecStart=/path/to/beszel-telegram-bot/venv/bin/python3 -u monitor_bot.py
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

3.  Enable and start:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable beszel-bot
    sudo systemctl start beszel-bot
    ```

## Screenshots

*(You can add screenshots of your bot messages here)*