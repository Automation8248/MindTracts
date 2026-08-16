import os
import requests
import yt_dlp

# Environment variables se credentials lena
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def get_user_ids(file_path="users.txt"):
    """Reads user IDs or profile URLs from a text file."""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} file nahi mili.")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def send_to_telegram(video_path, caption):
    """Sends the downloaded video and caption to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram bot token ya chat ID missing hai.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, "rb") as video_file:
            files = {"video": video_file}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption[:1024]}
            res = requests.post(url, data=data, files=files, timeout=120)
            if res.status_code == 200:
                print("Telegram par video successfully send ho gayi.")
            else:
                print(f"Telegram error: {res.text}")
    except Exception as e:
        print(f"Telegram send failure: {e}")

def send_to_webhook(metadata):
    """Sends video metadata to your webhook."""
    if not WEBHOOK_URL:
        print("Webhook URL set nahi hai.")
        return

    try:
        res = requests.post(WEBHOOK_URL, json=metadata, timeout=30)
        print(f"Webhook status: {res.status_code}")
    except Exception as e:
        print(f"Webhook send failure: {e}")

def process_user(user_input):
    """Downloads the latest video for a profile and sends it out."""
    # Agar direct URL nahi hai toh URL format karein
    if user_input.startswith("http://") or user_input.startswith("https://"):
        target_url = user_input
    else:
        target_url = f"https://www.kuaishou.com/profile/{user_input}"

    print(f"\nProcessing: {target_url}")

    # yt-dlp configuration: Sirf latest 1 video download karega
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'playlist_items': '1',
        'quiet': False,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=True)
            
            # Agar profile ek playlist/channel ki tarah behave kare
            if 'entries' in info and len(info['entries']) > 0:
                video_data = info['entries'][0]
            else:
                video_data = info

            if not video_data:
                print(f"Koi video nahi mila for {user_input}")
                return

            video_id = video_data.get("id")
            title = video_data.get("title", "Kuaishou Video")
            uploader = video_data.get("uploader", user_input)
            ext = video_data.get("ext", "mp4")
            local_filename = f"downloads/{video_id}.{ext}"

            metadata = {
                "id": video_id,
                "title": title,
                "uploader": uploader,
                "webpage_url": video_data.get("webpage_url", target_url),
                "view_count": video_data.get("view_count"),
                "like_count": video_data.get("like_count"),
            }

            caption = f"🎬 {title}\n👤 Uploader: {uploader}\n🔗 {metadata['webpage_url']}"

            # 1. Telegram par bhejna
            if os.path.exists(local_filename):
                # Telegram bot API limit: 50MB per video
                file_size_mb = os.path.getsize(local_filename) / (1024 * 1024)
                if file_size_mb <= 50:
                    send_to_telegram(local_filename, caption)
                else:
                    print(f"Video ka size 50MB se bada hai ({file_size_mb:.2f} MB), Telegram par send nahi ho sakta.")
                
                # 2. Webhook par metadata bhejna
                send_to_webhook(metadata)

                # Local video delete karein (storage bachane ke liye)
                os.remove(local_filename)

    except Exception as e:
        print(f"Error processing {user_input}: {e}")

def main():
    os.makedirs("downloads", exist_ok=True)
    users = get_user_ids("users.txt")
    if not users:
        print("users.txt me koi ID nahi mili.")
        return

    for user in users:
        process_user(user)

if __name__ == "__main__":
    main()
