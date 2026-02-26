import os
import json
import random
import requests
import datetime
import cloudinary
import cloudinary.api
import cloudinary.uploader

# --- CONFIGURATION ---
HISTORY_FILE = "history.json"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# Aapka fixed cloud name jo backup ki tarah kaam karega
DEFAULT_CLOUD_NAME = "dwrjs3cgz"

# Cloudinary Configuration
cloud_name_env = os.environ.get("CLOUDINARY_CLOUD_NAME")
final_cloud_name = cloud_name_env if cloud_name_env and "***" not in cloud_name_env else DEFAULT_CLOUD_NAME

cloudinary.config( 
  cloud_name = final_cloud_name, 
  api_key = os.environ.get("CLOUDINARY_API_KEY"), 
  api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
  secure = True
)

CLOUDINARY_FOLDER = "videos" 

# --- DATA GRID ---
TITLES_GRID = ["Aaj kuch unexpected ho gaya…"]
CAPTIONS_GRID = ["Bas share karna tha ❤️"]

FIXED_HASHTAGS = """
.
.
.
.
.
#viral #trending #fyp #foryou #reels #short #shorts #ytshorts #explore #explorepage #viralvideo #trend #newvideo #content #creator #dailycontent #entertainment #fun #interesting #watchtillend #mustwatch #reality #real #moment #life #daily #people #reaction #vibes #share #support"""

INSTA_HASHTAGS = """\n.\n.\n.\n.\n"#viral #fyp #trending #explorepage #ytshorts"\n"""
YOUTUBE_HASHTAGS = """\n.\n.\n.\n"#youtubeshorts #youtube #shorts #subscribe #viralshorts"\n"""
FACEBOOK_HASHTAGS = """\n.\n.\n.\n"#facebookreels #fb #reelsvideo #viralreels #fbreels"\n"""

# --- HELPER FUNCTIONS ---
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_history(data):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- MAIN LOGIC ---
def run_automation():
    history = load_history()
    today = datetime.date.today()
    new_history = []
    
    # 1. DELETE EXPIRED (15 Days Logic)
    for entry in history:
        if 'date_sent' not in entry: continue
        sent_date = datetime.date.fromisoformat(entry['date_sent'])
        if (today - sent_date).days >= 15:
            try:
                cloudinary.uploader.destroy(entry['filename'], resource_type="video")
            except: pass
        else:
            new_history.append(entry)
    
    save_history(new_history)

    # 2. FETCH FROM FOLDER (SMART FETCH WAPAS ADD KIYA HAI)
    try:
        response = cloudinary.api.resources(type="upload", resource_type="video", max_results=500)
        raw_videos = response.get('resources', [])
        
        all_videos = []
        for v in raw_videos:
            # Ye logic videos ko 100% dhoondh lega
            if v.get('folder') == CLOUDINARY_FOLDER or v.get('asset_folder') == CLOUDINARY_FOLDER or v['public_id'].startswith(f"{CLOUDINARY_FOLDER}/"):
                all_videos.append(v)
                
    except Exception as e:
        print(f"Cloudinary Fetch Error: {e}")
        return

    sent_filenames = [entry['filename'] for entry in new_history]
    available_videos = [v for v in all_videos if v['public_id'] not in sent_filenames]
    
    if not available_videos:
        print("No new videos available in folder.")
        return

    selected = random.choice(available_videos)
    video_id = selected['public_id']
    
    # 3. LINK GENERATION & AUTO-FIX
    # Cloudinary ka original secure URL lenge taaki link ekdum perfect ho
    direct_download_url = selected['secure_url']
    
    # Agar link mein '***' hai, toh usko 'dwrjs3cgz' se theek kar dega
    if "***" in direct_download_url:
        direct_download_url = direct_download_url.replace("***", DEFAULT_CLOUD_NAME)

    print(f"Selected Video ID: {video_id}")
    print(f"Final Working Link: {direct_download_url}")

    # 4. SEND TO TELEGRAM
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
        time_string = ist_now.strftime("%d %b %I:%M:%S %p %Y").upper()
        payload = {
            'chat_id': TELEGRAM_CHAT_ID, 
            'caption': f"<b>{time_string}</b>",
            'parse_mode': 'HTML',
            'video': direct_download_url
        }
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo", data=payload)
        except Exception as e:
            print(f"Telegram Error: {e}")

    # 5. SEND TO WEBHOOK
    if WEBHOOK_URL:
        webhook_payload = {
            "video_url": direct_download_url,
            "title": random.choice(TITLES_GRID),
            "caption": random.choice(CAPTIONS_GRID),
            "hashtags": FIXED_HASHTAGS,
            "insta_hashtags": INSTA_HASHTAGS,
            "youtube_hashtags": YOUTUBE_HASHTAGS,
            "facebook_hashtags": FACEBOOK_HASHTAGS,
            "source": "AffiliateBot"
        }
        try:
            requests.post(WEBHOOK_URL, json=webhook_payload)
        except Exception as e:
            print(f"Webhook Error: {e}")

    # 6. UPDATE HISTORY
    new_history.append({"filename": video_id, "date_sent": today.isoformat()})
    save_history(new_history)
    print("Automation Done Successfully!")

if __name__ == "__main__":
    run_automation()
