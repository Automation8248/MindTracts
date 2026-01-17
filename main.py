import instaloader
import requests
import os
from telegram import Bot

# ===== CONFIG =====
INSTAGRAM_USERNAME = "virtualaarvi"
TELEGRAM_CHAT_ID = "@your_channel"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
LAST_FILE = "last_video.txt"

bot = Bot(token=TELEGRAM_TOKEN)
L = instaloader.Instaloader()

profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)

# Load last posted video
last_shortcode = ""
if os.path.exists(LAST_FILE):
    last_shortcode = open(LAST_FILE).read().strip()

for post in profile.get_posts():

    if not post.is_video:
        continue

    if post.shortcode == last_shortcode:
        break

    # 🔗 Instagram Video Link (Copy Link)
    video_link = f"https://www.instagram.com/reel/{post.shortcode}/"

    # 🎥 Direct Video URL
    video_url = post.video_url

    # 📝 Caption + Hashtags
    caption = post.caption if post.caption else ""
    final_caption = f"""{caption}

🔗 {video_link}
🎥 Credit: @{INSTAGRAM_USERNAME}
"""

    # Download video
    video_data = requests.get(video_url).content
    with open("video.mp4", "wb") as f:
        f.write(video_data)

    # Upload to Telegram
    bot.send_video(
        chat_id=TELEGRAM_CHAT_ID,
        video=open("video.mp4", "rb"),
        caption=final_caption[:1024]  # Telegram limit
    )

    # Webhook send
    requests.post(WEBHOOK_URL, json={
        "username": INSTAGRAM_USERNAME,
        "video_link": video_link,
        "caption": caption,
        "status": "posted"
    })

    # Save last video
    open(LAST_FILE, "w").write(post.shortcode)

    break
