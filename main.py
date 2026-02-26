import os
import json
import random
import requests
import datetime
import cloudinary
import cloudinary.api
import cloudinary.uploader # Delete karne ke liye iski zaroorat padegi

# --- CONFIGURATION ---
HISTORY_FILE = "history.json"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# Cloudinary Configuration
cloudinary.config( 
  cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.environ.get("CLOUDINARY_API_KEY"), 
  api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
  secure = True
)

CLOUDINARY_FOLDER = "videos" 

# --- DATA GRID (Pre-saved Titles & Captions) ---

TITLES_GRID = [
"Aaj kuch unexpected ho gaya…"
]

CAPTIONS_GRID = [
"Bas share karna tha ❤️"
]

FIXED_HASHTAGS = """
.
.
.
.
.
#viral #trending #fyp #foryou #reels #short #shorts #ytshorts #explore #explorepage #viralvideo #trend #newvideo #content #creator #dailycontent #entertainment #fun #interesting #watchtillend #mustwatch #reality #real #moment #life #daily #people #reaction #vibes #share #support"""

INSTA_HASHTAGS = """
.
.
.
.
"#viral #fyp #trending #explorepage #ytshorts"
"""
YOUTUBE_HASHTAGS = """
.
.
.
"#youtubeshorts #youtube #shorts #subscribe #viralshorts"
"""

FACEBOOK_HASHTAGS = """
.
.
.
"#facebookreels #fb #reelsvideo #viralreels #fbreels"
"""

# --- HELPER FUNCTIONS ---

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, 'r') as f:
        return json.load(f)

def save_history(data):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- MAIN LOGIC ---

def run_automation():
    # 1. DELETE EXPIRED VIDEOS FROM CLOUDINARY (15 Days Logic)
    history = load_history()
    today = datetime.date.today()
    new_history = []
    
    print("Checking for 15-day expired videos...")
    for entry in history:
        sent_date = datetime.date.fromisoformat(entry['date_sent'])
        days_diff = (today - sent_date).days
        
        # Agar 15 din ya usse zyada ho gaye hain, toh Cloudinary se Delete kar do
        if days_diff >= 15:
            try:
                public_id_to_delete = entry['filename']
                # Cloudinary se permanent delete karne ki API call
                result = cloudinary.uploader.destroy(public_id_to_delete, resource_type="video")
                print(f"DELETED EXPIRED FROM CLOUDINARY: {public_id_to_delete} - Status: {result.get('result')}")
            except Exception as e:
                print(f"Error deleting video {entry['filename']} from Cloudinary: {e}")
        else:
            new_history.append(entry)
    
    save_history(new_history)
    history = new_history 

    # 2. FETCH VIDEOS FROM CLOUDINARY
    print("Fetching available videos from Cloudinary...")
    try:
        response = cloudinary.api.resources(
            type="upload",
            resource_type="video",
            prefix=f"{CLOUDINARY_FOLDER}/",
            max_results=500 
        )
        all_videos = response.get('resources', [])
    except Exception as e:
        print(f"Cloudinary Fetch Error: {e}")
        return

    sent_filenames = [entry['filename'] for entry in history]
    
    available_videos = [v for v in all_videos if v['public_id'] not in sent_filenames]
    
    if not available_videos:
        print("No new videos to send from Cloudinary.")
        return

    selected_video_data = random.choice(available_videos)
    video_to_send_id = selected_video_data['public_id']
    video_url = selected_video_data['secure_url'] 
    
    print(f"Selected Video ID: {video_to_send_id}")
    print(f"Video URL: {video_url}")

    # 3. RANDOM SELECTION (Grid System)
    selected_title = random.choice(TITLES_GRID)
    selected_caption = random.choice(CAPTIONS_GRID)
    
    print(f"Generated Title: {selected_title}")
    print(f"Generated Caption: {selected_caption}")

    # 4. SEND TO TELEGRAM
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("Sending to Telegram...")
        ist_now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
        time_string = ist_now.strftime("%d %b %I:%M:%S %p %Y").upper()
        telegram_caption = f"<b>{time_string}</b>"

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        
        payload = {
            'chat_id': TELEGRAM_CHAT_ID, 
            'caption': telegram_caption,
            'parse_mode': 'HTML',
            'video': video_url 
        }
        
        try:
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                print("Successfully sent to Telegram.")
            else:
                print(f"Telegram API Response Error: {response.text}")
        except Exception as e:
            print(f"Telegram Request Error: {e}")

    # 5. SEND TO WEBHOOK
    if WEBHOOK_URL:
        print("Sending to Webhook...")
        
        webhook_data = {
            "video_url": video_url,
            "title": selected_title,
            "caption": selected_caption,
            "hashtags": FIXED_HASHTAGS,
            "insta_hashtags": INSTA_HASHTAGS,
            "youtube_hashtags": YOUTUBE_HASHTAGS, 
            "facebook_hashtags": FACEBOOK_HASHTAGS, 
            "source": "AffiliateBot"
        }
        try:
            response = requests.post(WEBHOOK_URL, json=webhook_data)
            print(f"Webhook Sent. Status: {response.status_code}")
        except Exception as e:
            print(f"Webhook Error: {e}")

    # 6. UPDATE HISTORY
    new_history.append({
        "filename": video_to_send_id,
        "date_sent": today.isoformat()
    })
    save_history(new_history)
    print("Automation Complete.")

if __name__ == "__main__":
    run_automation()
