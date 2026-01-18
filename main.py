import os
import requests
import yt_dlp
import sys
import glob
import re
import json

# --- CONFIGURATION ---
VIDEO_LIST_FILE = 'videos.txt'
HISTORY_FILE = 'history.txt'

# Secrets load karte waqt check karenge ki wo exist karte hain ya nahi
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

def get_next_video():
    processed_urls = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            processed_urls = [line.strip() for line in f.readlines()]

    if not os.path.exists(VIDEO_LIST_FILE):
        print("❌ Error: videos.txt file nahi mili!")
        return None

    with open(VIDEO_LIST_FILE, 'r') as f:
        all_urls = [line.strip() for line in f.readlines() if line.strip()]

    for url in all_urls:
        if url not in processed_urls:
            return url
    return None

def clean_vtt_text(vtt_content):
    lines = vtt_content.splitlines()
    clean_lines = []
    for line in lines:
        if '-->' in line or line.strip() == '' or line.startswith('WEBVTT') or line.strip().isdigit():
            continue
        clean_line = re.sub(r'<[^>]+>', '', line).strip()
        if clean_line and clean_line not in clean_lines:
            clean_lines.append(clean_line)
    return "\n".join(clean_lines[:50])

def download_video_data(url):
    print(f"⬇️ Downloading: {url}")
    # Temp files cleanup
    for f in glob.glob("temp_video*"):
        try: os.remove(f)
        except: pass

    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': 'temp_video.%(ext)s',
        'quiet': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en', 'hi', 'auto'],
    }
    
    caption_text = "No captions."
    dl_filename = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            dl_filename = ydl.prepare_filename(info)
            title = info.get('title', 'No Title')
            tags = info.get('tags', [])
            hashtags = " ".join([f"#{tag.replace(' ', '')}" for tag in tags[:10]])

            sub_files = glob.glob("temp_video*.vtt")
            if sub_files:
                with open(sub_files[0], 'r', encoding='utf-8') as f:
                    caption_text = clean_vtt_text(f.read())
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return None

    return {
        "filename": dl_filename,
        "title": title,
        "hashtags": hashtags,
        "captions": caption_text
    }

def upload_to_catbox(filepath):
    print("🚀 Uploading to Catbox.moe...")
    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                "https://catbox.moe/user/api.php", 
                data={"reqtype": "fileupload"}, 
                files={"fileToUpload": f}
            )
            if response.status_code == 200:
                return response.text.strip()
            else:
                print(f"❌ Catbox Error: {response.text}")
                return None
    except Exception as e:
        print(f"❌ Upload Error: {e}")
        return None

def send_notifications(video_data, catbox_url):
    print("\n--- Sending Notifications ---")
    
    # 1. TELEGRAM
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram Token ya Chat ID settings me nahi mila. Skip kar raha hu.")
    else:
        caption = f"🎬 **{video_data['title']}**\n\n{video_data['hashtags']}\n\n🔗 {catbox_url}"
        if video_data['captions'] != "No captions.":
             caption += f"\n\n📝 **Captions:**\n_{video_data['captions'][:500]}_"

        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": str(TELEGRAM_CHAT_ID), 
            "text": caption,
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(tg_url, json=payload)
            if resp.status_code == 200:
                print("✅ Telegram Sent Successfully!")
            else:
                print(f"❌ Telegram Fail ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"❌ Telegram Connection Error: {e}")

    # 2. WEBHOOK (Video URL specifically)
    if not WEBHOOK_URL:
        print("⚠️ Webhook URL settings me nahi mila. Skip kar raha hu.")
    else:
        print(f"Attempting to send to Webhook: {WEBHOOK_URL}")
        # Aapki requirement ke hisab se Video URL bhej rahe hain
        webhook_payload = {
            "content": f"New Video: {video_data['title']}", # Discord/General format
            "video_url": catbox_url,
            "title": video_data['title'],
            "hashtags": video_data['hashtags'],
            "captions": video_data['captions']
        }
        
        try:
            # Headers add kiye taaki server reject na kare
            headers = {'Content-Type': 'application/json'}
            resp = requests.post(WEBHOOK_URL, json=webhook_payload, headers=headers)
            
            if resp.status_code in [200, 201, 204]:
                print(f"✅ Webhook Sent Successfully! (Status: {resp.status_code})")
            else:
                print(f"❌ Webhook Fail ({resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"❌ Webhook Connection Error: {e}")

def update_history(url):
    with open(HISTORY_FILE, 'a') as f:
        f.write(url + '\n')

if __name__ == "__main__":
    # Check Environment Variables first
    if not TELEGRAM_BOT_TOKEN: print("⚠️ Warning: TELEGRAM_BOT_TOKEN is missing")
    if not WEBHOOK_URL: print("⚠️ Warning: WEBHOOK_URL is missing")

    next_url = get_next_video()
    
    if not next_url:
        print("💤 No new videos to process.")
        sys.exit(0)
        
    data = download_video_data(next_url)
    
    if data and data['filename']:
        catbox_link = upload_to_catbox(data['filename'])
        
        if catbox_link:
            print(f"🎉 Generated Link: {catbox_link}")
            send_notifications(data, catbox_link)
            update_history(next_url)
            
            if os.path.exists(data['filename']):
                os.remove(data['filename'])
            print("✅ Task Done.")
        else:
            sys.exit(1)
    else:
        sys.exit(1)
