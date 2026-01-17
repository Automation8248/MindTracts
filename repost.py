import instaloader
import requests

USERNAME = "virtualaarvi"
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"
WEBHOOK_URL = "YOUR_WEBHOOK_URL"

L = instaloader.Instaloader(download_videos=True, download_pictures=False)

profile = instaloader.Profile.from_username(L.context, USERNAME)

# read last video
with open("last_video.txt", "r") as f:
    last_video = f.read().strip()

videos = [p for p in profile.get_posts() if p.is_video]
videos.reverse()  # OLDEST → NEWEST

for post in videos:
    if post.shortcode == last_video:
        continue

    # download video
    L.download_post(post, target="video")

    video_file = [f for f in os.listdir("video") if f.endswith(".mp4")][0]

    # upload to catbox
    r = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"file": open("video/" + video_file, "rb")}
    )

    catbox_url = r.text
    caption = post.caption or ""

    # send to telegram
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(telegram_url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"{caption}\n\n🎥 {catbox_url}"
    })

    # send to webhook
    requests.post(WEBHOOK_URL, json={
        "video": catbox_url,
        "caption": caption
    })

    # save progress
    with open("last_video.txt", "w") as f:
        f.write(post.shortcode)

    break  # ONLY ONE VIDEO PER DAY
