import os, requests, feedparser
from telegram import Bot
import yt_dlp

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEBHOOK = os.getenv("WEBHOOK_URL")

bot = Bot(BOT_TOKEN)

rss = feedparser.parse(open("rss_url.txt").read().strip())
entries = list(reversed(rss.entries))  # oldest → newest

last = 0
if os.path.exists("last_sent.txt"):
    last = int(open("last_sent.txt").read())

if last >= len(entries):
    print("No new posts")
    exit()

post = entries[last]
video_url = post.link
title = post.title
caption = post.get("summary", "")

# download video
ydl_opts = {"outtmpl": "video.mp4", "quiet": True}
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

# telegram
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

open("last_sent.txt", "w").write(str(last + 1))
print("DONE")
