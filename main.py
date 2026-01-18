import os
import requests
import yt_dlp
import sys
import json

# --- CONFIGURATION ---
VIDEO_LIST_FILE = 'videos.txt'
HISTORY_FILE = 'history.txt'
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

def get_next_video():
    # History load karo
    processed_urls = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            processed_urls = [line.strip() for line in f.readlines()]

    # Video list load karo
    if not os.path.exists(VIDEO_LIST_FILE):
        print("Error: videos.txt not found!")
        return None

    with open(VIDEO_LIST_FILE, 'r') as f:
        all_urls = [line.strip() for line in f.readlines() if line.strip()]

    # Pehla aisa URL dhundo jo processed nahi hai
    for url in all_urls:
        if url not in processed_urls:
            return url
    
    return None

def download_video_data(url):
    print(f"Processing: {url}")
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloaded_video.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        # Metadata extraction
        title = info.get('title', 'No Title')
        description = info.get('description', '')
        tags = info.get('tags', [])
        hashtags = " ".join([f"#{tag.replace(' ', '')}" for tag in tags[:10]]) # Top 10 tags
        
        return {
            "filename": filename,
            "title": title,
            "hashtags": hashtags,
            "original_url": url,
            "description": description
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
                return response.text.strip() # Returns the Catbox URL
            else:
                print(f"Catbox Error: {response.text}")
                return None
    except Exception as e:
        print(f"Upload Error: {e}")
        return None

def send_notifications(video_data, catbox_url):
    caption = f"🎬 **{video_data['title']}**\n\n{video_data['hashtags']}\n\n🔗 Watch/Download: {catbox_url}"
    
    # 1. Send to Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": caption,
            "parse_mode": "Markdown"
        }
        requests.post(tg_url, json=payload)
        print("Sent to Telegram.")

    # 2. Send to Webhook
    if WEBHOOK_URL:
        webhook_payload = {
            "title": video_data['title'],
            "video_url": catbox_url,
            "hashtags": video_data['hashtags'],
            "original_desc": video_data['description']
        }
        try:
            requests.post(WEBHOOK_URL, json=webhook_payload)
            print("Sent to Webhook.")
        except Exception as e:
            print(f"Webhook Error: {e}")

def update_history(url):
    with open(HISTORY_FILE, 'a') as f:
        f.write(url + '\n')

if __name__ == "__main__":
    next_url = get_next_video()
    
    if not next_url:
        print("No new videos to process today!")
        sys.exit(0)
        
    try:
        # 1. Download
        data = download_video_data(next_url)
        
        # 2. Upload to Catbox
        catbox_link = upload_to_catbox(data['filename'])
        
        if catbox_link:
            print(f"Catbox URL: {catbox_link}")
            
            # 3. Send Alerts
            send_notifications(data, catbox_link)
            
            # 4. Update History
            update_history(next_url)
            
            # Cleanup
            if os.path.exists(data['filename']):
                os.remove(data['filename'])
                
            print("Task Completed Successfully.")
        else:
            print("Failed to upload to Catbox.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Critical Error: {e}")
        sys.exit(1)
