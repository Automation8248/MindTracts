import os
import requests
import yt_dlp
import sys
import glob
import re
from deep_translator import GoogleTranslator

# --- CONFIGURATION ---
VIDEO_LIST_FILE = 'videos.txt'
HISTORY_FILE = 'history.txt'

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Filler tags agar video ke tags kam pad jayein (Total 5 karne ke liye)
SEO_TAGS = ["#reels", "#trending", "#viral", "#explore", "#love", "#shayari"]

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

def get_hindi_title(text):
    try:
        # Translate full title to Hindi
        translated = GoogleTranslator(source='auto', target='hi').translate(text)
        # Split into words and take first 4
        words = translated.split()
        short_title = " ".join(words[:4])
        return short_title
    except Exception as e:
        print(f"Translation Error: {e}")
        # Fallback: First 4 words of original text if translation fails
        return " ".join(text.split()[:4])

def generate_hashtags(original_tags):
    final_tags = []
    
    # 1. First Tag is ALWAYS #aarvi
    final_tags.append("#aarvi")
    
    # 2. Add video's original tags (excluding forbidden ones)
    forbidden = ["virtualaarvi", "aarvi"] # aarvi already added manually
    
    for tag in original_tags:
        clean_tag = tag.replace(" ", "").lower()
        if clean_tag not in forbidden and f"#{clean_tag}" not in final_tags:
            final_tags.append(f"#{clean_tag}")
            
    # 3. Fill up to exactly 5 tags
    for seo in SEO_TAGS:
        if len(final_tags) < 5:
            if seo not in final_tags:
                final_tags.append(seo)
        else:
            break
            
    # Limit to exactly 5 tags
    return " ".join(final_tags[:5])

def download_video_data(url):
    print(f"⬇️ Downloading: {url}")
    for f in glob.glob("temp_video*"):
        try: os.remove(f)
        except: pass

    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': 'temp_video.%(ext)s',
        'quiet': True,
    }
    
    dl_filename = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            dl_filename = ydl.prepare_filename(info)
            title = info.get('title', 'No Title')
            
            # --- Generate Hindi Title (First 4 words) ---
            hindi_4_words = get_hindi_title(title)
            
            # --- Generate Hashtags (Total 5) ---
            tags_list = info.get('tags', [])
            hashtags = generate_hashtags(tags_list)

    except Exception as e:
        print(f"❌ Download Error: {e}")
        return None

    return {
        "filename": dl_filename,
        "title": title,          # Original Title (for Webhook)
        "hindi_text": hindi_4_words, # Processed Hindi Text (for Telegram)
        "hashtags": hashtags,
        "original_url": url
    }

def upload_to_catbox(filepath):
    print("🚀 Uploading to Catbox (for Webhook)...")
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
    
    # --- Format Caption for Telegram ---
    # 1. Hindi 4 words
    # 2. 5 Dots spacing
    # 3. 5 Hashtags
    tg_caption = f"{video_data['hindi_text']}\n.\n.\n.\n.\n.\n{video_data['hashtags']}"
    
    # --- 1. TELEGRAM (Send Video File) ---
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("📤 Sending Video File to Telegram...")
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        
        try:
            with open(video_data['filename'], 'rb') as video_file:
                payload = {
                    "chat_id": str(TELEGRAM_CHAT_ID),
                    "caption": tg_caption,
                    "parse_mode": "Markdown"
                }
                files = {'video': video_file}
                resp = requests.post(tg_url, data=payload, files=files)
                
                if resp.status_code == 200:
                    print("✅ Telegram Video Sent!")
                else:
                    print(f"❌ Telegram Fail: {resp.text}")
        except Exception as e:
            print(f"❌ Telegram Error: {e}")

    # --- 2. WEBHOOK (Send Link + Caption) ---
    if WEBHOOK_URL:
        print(f"Sending to Webhook...")
        webhook_payload = {
            "content": tg_caption,  # Same caption for consistency
            "video_url": catbox_url,
            "title_original": video_data['title'],
            "hashtags": video_data['hashtags']
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
        # Catbox upload is needed for Webhook link
        catbox_link = upload_to_catbox(data['filename'])
        if not catbox_link: catbox_link = "Upload Failed"

        send_notifications(data, catbox_link)
        update_history(next_url)
        
        if os.path.exists(data['filename']):
            os.remove(data['filename'])
        print("✅ Task Done.")
    else:
        sys.exit(1)
