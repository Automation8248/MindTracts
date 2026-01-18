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

# SEO / Filler Tags (agar original tags kam pad jayein)
SEO_TAGS = ["#viral", "#trending", "#reels", "#explore", "#shorts", "#fyp"]

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

def generate_hashtags(original_tags):
    # 1. Start clean list
    final_tags = []
    
    # 2. Add Mandatory Tag First
    final_tags.append("#aarvi")
    
    # 3. Process Original Tags
    forbidden = ["virtualaarvi"] # Lowercase mein likhein
    
    for tag in original_tags:
        clean_tag = tag.replace(" ", "").lower()
        # Filter forbidden tags
        if clean_tag not in forbidden and f"#{clean_tag}" != "#aarvi":
            final_tags.append(f"#{clean_tag}")
            
    # 4. Ensure Minimum 4 Tags (Add SEO tags if needed)
    for seo in SEO_TAGS:
        if len(final_tags) < 4:
            if seo not in final_tags:
                final_tags.append(seo)
        else:
            break
            
    return " ".join(final_tags)

def download_video_data(url):
    print(f"⬇️ Downloading: {url}")
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
            
            # --- HASHTAG LOGIC CALL ---
            tags_list = info.get('tags', [])
            hashtags = generate_hashtags(tags_list)

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
        "captions": caption_text,
        "original_url": url
    }

def upload_to_catbox(filepath):
    print("🚀 Uploading to Catbox (for Webhook backup)...")
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
                return None
    except:
        return None

def send_notifications(video_data, catbox_url):
    print("\n--- Sending Notifications ---")
    
    # --- 1. TELEGRAM VIDEO UPLOAD ---
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("📤 Sending Video File to Telegram...")
        
        # Caption Format
        caption = f"{video_data['title']}\n\n{video_data['hashtags']}\n\n"
        if video_data['captions'] != "No captions.":
             caption += f"📝 **Quotes:**\n_{video_data['captions'][:400]}_\n"
        
        # API Endpoint for Video
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        
        try:
            with open(video_data['filename'], 'rb') as video_file:
                payload = {
                    "chat_id": str(TELEGRAM_CHAT_ID),
                    "caption": caption[:1024], # Telegram caption limit
                    "parse_mode": "Markdown"
                }
                files = {'video': video_file}
                
                resp = requests.post(tg_url, data=payload, files=files)
                
                if resp.status_code == 200:
                    print("✅ Telegram Video Sent!")
                else:
                    print(f"❌ Telegram Video Fail: {resp.text}")
        except Exception as e:
            print(f"❌ Telegram Error: {e}")

    # --- 2. WEBHOOK (Still sends URL) ---
    if WEBHOOK_URL:
        print(f"Sending to Webhook...")
        webhook_payload = {
            "content": f"New Post: {video_data['title']}",
            "video_url": catbox_url,
            "title": video_data['title'],
            "hashtags": video_data['hashtags'],
            "captions": video_data['captions']
        }
        try:
            requests.post(WEBHOOK_URL, json=webhook_payload)
            print("✅ Webhook Sent!")
        except:
            print("❌ Webhook Failed")

def update_history(url):
    with open(HISTORY_FILE, 'a') as f:
        f.write(url + '\n')

if __name__ == "__main__":
    next_url = get_next_video()
    
    if not next_url:
        print("💤 No new videos.")
        sys.exit(0)
        
    data = download_video_data(next_url)
    
    if data and data['filename']:
        # Webhook ke liye Catbox zaroori hai
        catbox_link = upload_to_catbox(data['filename'])
        if not catbox_link: catbox_link = "Upload Failed"

        send_notifications(data, catbox_link)
        update_history(next_url)
        
        if os.path.exists(data['filename']):
            os.remove(data['filename'])
        print("✅ Task Done.")
    else:
        sys.exit(1)
