import telebot
from flask import Flask, request
import requests
import threading
import re
import time

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# Replace these values with your actual data
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"  # Can be integer or string

# Beszel API Settings
BESZEL_URL = "http://127.0.0.1:8090" # Your Beszel instance URL (e.g., http://192.168.1.100:8090)
BESZEL_USER = "admin@example.com"    # Your Beszel admin email
BESZEL_PASS = "YOUR_PASSWORD"        # Your Beszel admin password

# Initialize Bot and Flask
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# Cache for server names and IPs
SERVER_MAP = {}

# ==========================================
# 1️⃣ API & SERVER DISCOVERY
# ==========================================
def update_server_map():
    """Fetches all server names and IPs from Beszel API to update the local cache."""
    global SERVER_MAP
    try:
        # 1. Login to get the token
        auth_resp = requests.post(
            f"{BESZEL_URL}/api/collections/users/auth-with-password", 
            json={"identity": BESZEL_USER, "password": BESZEL_PASS}, 
            timeout=20
        )
        
        if auth_resp.status_code != 200:
            print(f"❌ Login failed: {auth_resp.status_code}")
            return []

        token = auth_resp.json().get('token')
        
        # 2. Fetch system records
        headers = {"Authorization": token}
        resp = requests.get(
            f"{BESZEL_URL}/api/collections/systems/records?perPage=500", 
            headers=headers, 
            timeout=20
        )
        
        if resp.status_code == 200:
            items = resp.json().get('items', [])
            # Map names to hosts (IPs)
            SERVER_MAP = {s.get('name'): s.get('host') for s in items}
            print(f"🧠 Bot learned {len(SERVER_MAP)} servers.", flush=True)
            return items
        else:
            print(f"❌ API Error: {resp.status_code}")
            return []
            
    except Exception as e:
        print(f"⚠️ Error updating server map: {e}")
        return []

def get_status_report():
    """Generates a formatted status report for Telegram."""
    items = update_server_map() # Refresh data on every request
    if not items: return "❌ Could not fetch data from Beszel."

    # Sort by status (Offline servers first)
    items.sort(key=lambda x: x.get('status'), reverse=True)
    text = f"📊 <b>System Status ({len(items)} servers)</b>\n\n"
    
    for s in items:
        name = s.get('name', 'Unknown')
        ip = s.get('host', '')
        status = s.get('status')
        info = s.get('info', {}) if isinstance(s.get('info'), dict) else {}
        
        # Determine OS Icon
        kernel = info.get('k', '').lower()
        if 'windows' in kernel: icon = "🪟"
        elif 'linux' in kernel or 'generic' in kernel: icon = "🐧"
        elif 'darwin' in kernel or 'apple' in kernel: icon = "🍎"
        else: icon = "🖥"
        
        st_icon = "🟢" if status == 'up' else "🔴"
        text += f"{st_icon} {icon} <b>{name}</b> <code>[{ip}]</code>\n"
        
    return text

# ==========================================
# 2️⃣ ALERT PARSING LOGIC
# ==========================================
def parse_universal_alert(raw_text):
    """Parses raw text from Beszel webhook into a structured dictionary."""
    data = {
        "status": "info", "emoji": "ℹ️", "title": "Notification",
        "server": "Unknown", "ip": "", "metric": "System", "value": "", "link": ""
    }

    # 1. Extract Link
    link_match = re.search(r'(https?://[^\s]+)', raw_text)
    if link_match: data['link'] = link_match.group(1)

    # 2. Identify Server Name
    found_server = False
    for name, ip in SERVER_MAP.items():
        if name in raw_text:
            data['server'] = name
            data['ip'] = ip
            found_server = True
            break
    
    # Fallback if server not in cache
    if not found_server:
        clean_text = raw_text.replace("Connection to ", "")
        extracted_name = clean_text.split(' ')[0]
        data['server'] = extracted_name
        data['ip'] = SERVER_MAP.get(extracted_name, "")

    # 3. Determine Status and Metric
    # Remove server name to isolate the metric message
    clean_line = raw_text.split('\n')[0].replace(data['server'], "").strip()
    
    if "is down" in raw_text or "Connection failed" in raw_text:
        data.update({"status": "critical", "emoji": "🔴", "title": "SERVER DOWN", "metric": "Connection", "value": "OFFLINE"})
        
    elif "is up" in raw_text or "Connection restored" in raw_text:
        data.update({"status": "recovery", "emoji": "🟢", "title": "Connection Restored", "metric": "Connection", "value": "ONLINE"})
        
    elif "above threshold" in raw_text:
        metric_name = clean_line.replace("above threshold", "").strip()
        data.update({"status": "warning", "emoji": "⚠️", "title": "High Usage", "metric": metric_name})
        
    elif "below threshold" in raw_text:
        metric_name = clean_line.replace("below threshold", "").strip()
        data.update({"status": "recovery", "emoji": "✅", "title": "Recovered", "metric": metric_name})
        
    elif "Test Alert" in raw_text:
        data.update({"title": "Test Alert", "metric": "Test", "value": "OK"})

    # 4. Extract Value (Percentage, MB/s, etc.)
    val_match = re.search(r'(\d+(\.\d+)?\s?([%a-zA-Z/]+))', raw_text)
    if val_match and "LINE" not in data['value']:
        data['value'] = val_match.group(0)

    if not data['metric'] or len(data['metric']) < 2:
        data['metric'] = "System Service"

    return data

# ==========================================
# 3️⃣ HANDLERS
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try: bot.send_message(message.chat.id, "👋 Beszel Monitoring Bot is running.")
    except: pass

@bot.message_handler(commands=['status'])
def send_status(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        report = get_status_report()
        if len(report) > 4000: bot.send_message(message.chat.id, report[:4000], parse_mode="HTML")
        else: bot.send_message(message.chat.id, report, parse_mode="HTML")
    except Exception as e:
        print(f"Status Error: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    raw_text = request.get_data(as_text=True)
    print(f"📥 Signal: {raw_text}", flush=True)

    info = parse_universal_alert(raw_text)
    
    # Determine visual style based on status
    if info['status'] == 'critical':
        header_icon = "🚨"
        status_desc = "Critical Error"
    elif info['status'] == 'warning':
        header_icon = "⚠️"
        status_desc = "Warning"
    elif info['status'] == 'recovery':
        header_icon = "✅"
        status_desc = "Resolved"
    else:
        header_icon = "ℹ️"
        status_desc = "Info"

    ip_text = f"<code>[{info['ip']}]</code>" if info['ip'] else ""

    # Message Template
    msg = (
        f"{header_icon} <b>{info['title'].upper()}</b>\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
        f"🖥 <b>Server:</b> <code>{info['server']}</code> {ip_text}\n"
        f"🛠 <b>Metric:</b> {info['metric'].title()}\n"
        f"📝 <b>Status:</b> {status_desc}\n"
    )
    
    if info['value'] and "OK" not in info['value']:
         if "LINE" in info['value']: # ONLINE/OFFLINE
             msg += f"\n👉 <b>Status: {info['value']}</b>\n"
         else: # Numeric value
             msg += f"\n📊 <b>Value:</b>\n👉 <code>{info['value']}</code>\n"

    if info['link']: 
        msg += f"\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        msg += f"🔗 <a href='{info['link']}'>Open in Beszel</a>"

    try:
        bot.send_message(CHAT_ID, msg, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        print(f"Telegram Error: {e}")

    return "OK", 200

# ==========================================
# 4️⃣ RUN
# ==========================================
def run_flask():
    # Running on port 5555
    app.run(host='0.0.0.0', port=5555, debug=False, use_reloader=False)

if __name__ == '__main__':
    print("🚀 Bot started...")
    
    # Initial fetch of server map
    update_server_map()

    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    try:
        # Start Telegram polling
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Bot Error: {e}")