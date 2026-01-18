import os
import subprocess
import requests
import sys

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Basic safety check
if not BOT_TOKEN or not CHAT_ID:
    print("❌ Telegram secrets missing")
    sys.exit(1)

# Load links
with open("links.txt", "r") as f:
    links = [l.strip() for l in f if l.strip()]

# Load used links
if not os.path.exists("used.txt"):
    open("used.txt", "w").close()

with open("used.txt", "r") as f:
    used = set(l.strip() for l in f if l.strip())

# Pick next unused link (NO REPEAT)
next_link = None
for link in links:
    if link not in used:
        next_link = link
        break

if not next_link:
    print("✅ All videos already posted")
    sys.exit(0)

print("▶ Downloading:", next_link)

# Download video + caption
subprocess.run(
    [
        "yt-dlp",
        next_link,
        "-o", "video.%(ext)s",
        "--merge-output-format", "mp4",
        "--write-description"
    ],
    check=True
)

# Read caption
caption = ""
if os.path.exists("video.description"):
    with open("video.description", "r", encoding="utf-8") as f:
        caption = f.read().strip()

# Send to Telegram
with open("video.mp4", "rb") as video:
    tg = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo",
        data={
            "chat_id": CHAT_ID,
            "caption": caption[:1024]
        },
        files={"video": video},
        timeout=30
    )
    print("Telegram status:", tg.status_code)

# Send to Webhook (SAFE)
if WEBHOOK_URL and WEBHOOK_URL.startswith("http"):
    wh = requests.post(
        WEBHOOK_URL,
        json={
            "source": next_link,
            "caption": caption
        },
        timeout=30
    )
    print("Webhook status:", wh.status_code)
else:
    print("⚠️ Webhook skipped (not set)")

# Mark as used (PREVENT REPEAT)
with open("used.txt", "a") as f:
    f.write(next_link + "\n")

print("✅ Done successfully")
