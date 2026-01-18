import os
import requests
import yt_dlp
import sys
import glob
import re

# --- CONFIGURATION ---
VIDEO_LIST_FILE = 'videos.txt'
HISTORY_FILE = 'history.txt'
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

def get_next_video():
    processed_urls = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            processed_urls = [line.strip() for line in f.readlines()]

    if not os.path.exists(VIDEO_LIST_FILE):
        print("Error: videos.txt not found!")
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
    print(f"Processing: {url}")
    # Remove previous temp files
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
            description = info.get('description', '')
            tags = info.get('tags', [])
            # Hashtags logic: Create hashtags from tags, take top 10
            hashtags = " ".join([f"#{tag.replace(' ', '')}" for tag in tags[:10]])

            # Check for subtitles
            sub_files = glob.glob("temp_video*.vtt")
            if sub_files:
                with open(sub_files[0], 'r', encoding='utf-8') as f:
                    caption_text = clean_vtt_text(f.read())
    except Exception as e:
        print(f"Download Error: {e}")
        return None

    return {
        "filename": dl_filename,
        "title": title,
        "hashtags": hashtags,
        "description": description,
        "captions": caption_text
    }

def upload_to_catbox(filepath):
    print("Uploading to Catbox.moe...")
    url = "https://catbox.moe/user/api.php"
    try:
        with open(filepath, "rb") as f:
            data = {"reqtype": "fileupload"}
            files = {"fileToUpload": f}
            response = requests.post(url, data=data, files=files)
            if response.status_code == 200:
                return response.text.strip()
            else:
                print(f"Catbox Error: {response.text}")
                return None
    except Exception as e:
        print(f"Upload Error: {e}")
        return None

def send_notifications(video_data, catbox_url):
    # Caption Setup
    caption = f"🎬 **{video_data['title']}**\n\n{video_data['hashtags']}\n\n"
    if video_data['captions'] and video_data['captions'] != "No captions.":
         caption += f"📝 **Quotes/Captions:**\n_{video_data['captions']}_\n\n"
    caption += f"🔗 Watch/Download: {catbox_url}"
    
    # --- TELEGRAM DEBUG & SEND ---
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM CONFIG MISSING: Token or Chat ID not found in environment variables.")
    else:
        print(f"Attempting to send to Telegram Chat ID: {TELEGRAM_CHAT_ID}")
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": str(TELEGRAM_CHAT_ID), 
            "text": caption[:4000], # Telegram limit safety
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(tg_url, json=payload)
            print(f"Telegram Response Code: {resp.status_code}")
            print(f"Telegram Response Body: {resp.text}") # Ye line error batayegi agar fail hua to
        except Exception as e:
            print(f"Telegram Request Failed: {e}")

    # --- WEBHOOK DEBUG & SEND ---
    if not WEBHOOK_URL:
        print("❌ WEBHOOK CONFIG MISSING: URL not found.")
    else:
        print(f"Sending to Webhook: {WEBHOOK_URL}")
        webhook_payload = {
            "title": video_data['title'],
            "video_url": catbox_url,
            "hashtags": video_data['hashtags'],
            "captions": video_data['captions']
        }
        try:
            resp = requests.post(WEBHOOK_URL, json=webhook_payload)
            print(f"Webhook Response: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"Webhook Request Failed: {e}")

def update_history(url):
    with open(HISTORY_FILE, 'a') as f:
        f.write(url + '\n')

if __name__ == "__main__":
    next_url = get_next_video()
    
    if not next_url:
        print("No new videos to process today!")
        sys.exit(0)
        
    data = download_video_data(next_url)
    
    if data and data['filename']:
        catbox_link = upload_to_catbox(data['filename'])
        
        if catbox_link:
            print(f"Catbox URL: {catbox_link}")
            send_notifications(data, catbox_link)
            update_history(next_url)
            
            # Cleanup
            if os.path.exists(data['filename']):
                os.remove(data['filename'])
                
            print("Task Completed.")
        else:
            print("Failed to upload to Catbox.")
            sys.exit(1)
    else:
        print("Failed to download video data.")
        sys.exit(1)
