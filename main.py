import os
import requests
import yt_dlp
from playwright.sync_api import sync_playwright

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def get_user_ids(file_path="users.txt"):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def get_latest_video_url(profile_id):
    """Playwright ka use karke profile se latest video link nikalna"""
    profile_url = f"https://www.kuaishou.com/profile/{profile_id}"
    print(f"Scraping profile: {profile_url}")
    
    with sync_playwright() as p:
        # Browser background me run hoga (headless=True)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(profile_url, timeout=60000)
            # Wait for video elements to load on the page
            page.wait_for_selector('a[href*="/short-video/"]', timeout=15000)
            
            # Get the first video link (which is usually the newest)
            element = page.query_selector('a[href*="/short-video/"]')
            if element:
                href = element.get_attribute('href')
                # Complete the URL if it's a relative path
                if not href.startswith('http'):
                    href = f"https://www.kuaishou.com{href}"
                print(f"Found latest video link: {href}")
                return href
        except Exception as e:
            print(f"Failed to scrape profile {profile_id}: {e}")
        finally:
            browser.close()
    return None

def send_to_telegram(video_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, "rb") as video_file:
            res = requests.post(
                url, 
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption[:1024]}, 
                files={"video": video_file}, 
                timeout=120
            )
            print("Telegram response:", res.status_code)
    except Exception as e:
        print(f"Telegram error: {e}")

def send_to_webhook(metadata):
    if not WEBHOOK_URL:
        return
    try:
        requests.post(WEBHOOK_URL, json=metadata, timeout=30)
        print("Webhook sent successfully.")
    except Exception as e:
        print(f"Webhook error: {e}")

def process_user(user_id):
    # Step 1: Scrape the direct video URL
    video_url = get_latest_video_url(user_id)
    if not video_url:
        print(f"Skipping {user_id} - No video link found.")
        return

    # Step 2: Download the video using yt-dlp
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': False,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_id = info.get("id")
            ext = info.get("ext", "mp4")
            local_filename = f"downloads/{video_id}.{ext}"

            metadata = {
                "id": video_id,
                "title": info.get("title", "Kuaishou Video"),
                "uploader": info.get("uploader", user_id),
                "webpage_url": video_url,
                "view_count": info.get("view_count"),
            }

            caption = f"🎬 {metadata['title']}\n👤 Uploader ID: {user_id}\n🔗 {video_url}"

            # Step 3: Send files and clean up
            if os.path.exists(local_filename):
                file_size_mb = os.path.getsize(local_filename) / (1024 * 1024)
                if file_size_mb <= 50:
                    send_to_telegram(local_filename, caption)
                else:
                    print("Video exceeds Telegram 50MB limit.")
                
                send_to_webhook(metadata)
                os.remove(local_filename) # Storage save karne ke liye delete
                
    except Exception as e:
        print(f"Download error for {video_url}: {e}")

def main():
    os.makedirs("downloads", exist_ok=True)
    users = get_user_ids("users.txt")
    for user_id in users:
        # Example user_id in users.txt should just be: 1695373323
        process_user(user_id)

if __name__ == "__main__":
    main()
