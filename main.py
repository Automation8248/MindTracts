import os, requests, feedparser
from telegram import Bot
import yt_dlp

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEBHOOK = os.getenv("WEBHOOK_URL")

bot = Bot(BOT_TOKEN)

rss_url = open("rss_url.txt").read().strip()
feed = feedparser.parse(rss_url)

entries = list(reversed(feed.entries))  # oldest → newest

last = int(open("last_sent.txt").read()) if os.path.exists("last_sent.txt") else 0

video_post = None
index = last

while index < len(entries):
    link = entries[index].link.lower()
    if "/reel/" in link or "/p/" in link:
        video_post = entries[index]
        break
    index += 1

if not video_post:
    print("No video post found")
    exit()

video_url = video_post.link
title = video_post.title
caption = video_post.get("summary", "")

# download video
ydl_opts = {
    "outtmpl": "video.mp4",
    "format": "mp4",
    "quiet": True
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(video_url, download=True)
    tags = " ".join(info.get("tags", [])[:10])

final_caption = f"{title}\n\n{caption}\n\n{tags}"

# upload to catbox
res = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": open("video.mp4", "rb")}
)
catbox_url = res.text.strip()

# send telegram
bot.send_video(
    chat_id=CHAT_ID,
    video=catbox_url,
    caption=final_caption[:1024]
)

# webhook
if WEBHOOK:
    requests.post(WEBHOOK, json={
        "video": catbox_url,
        "caption": final_caption
    })

open("last_sent.txt", "w").write(str(index + 1))
print("DONE")
