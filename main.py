import os
import json
import random
import requests
import datetime

# --- CONFIGURATION ---
VIDEO_FOLDER = "videos"
HISTORY_FILE = "history.json"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# Yahan maine image se dekh kar aapka exact Repo Name daal diya hai
GITHUB_REPO = "Automation8248/Aarushi-" 
BRANCH_NAME = "main"

# --- DATA GRID (Pre-saved Titles & Captions) ---

# List 1: Titles (Har bar inme se koi ek randomly select hoga)
TITLES_GRID = [
"Aaj kuch unexpected ho gaya…"
]


# List 2: Captions (Har bar inme se koi ek randomly select hoga)
CAPTIONS_GRID = [
"Bas share karna tha ❤️"
]


# List 3: Fixed Hashtags (Ye har video me SAME rahega)
FIXED_HASHTAGS = """
.
.
.
.
.
#viral #trending #fyp #foryou #reels #short #shorts #ytshorts #explore #explorepage #viralvideo #trend #newvideo #content #creator #dailycontent #entertainment #fun #interesting #watchtillend #mustwatch #reality #real #moment #life #daily #people #reaction #vibes #share #support"""

# Isse AFFILIATE_HASHTAGS se badal kar INSTA_HASHTAGS kar diya hai
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
    # 1. DELETE OLD FILES (15 Days Logic)
    history = load_history()
    today = datetime.date.today()
    new_history = []
    
    print("Checking for expired videos...")
    for entry in history:
        sent_date = datetime.date.fromisoformat(entry['date_sent'])
        days_diff = (today - sent_date).days
        
        file_path = os.path.join(VIDEO_FOLDER, entry['filename'])
        
        if days_diff >= 15:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"DELETED EXPIRED: {entry['filename']}")
        else:
            new_history.append(entry)
    
    save_history(new_history)
    history = new_history 

    # 2. PICK NEW VIDEO
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER)
        
    all_videos = [f for f in os.listdir(VIDEO_FOLDER) if f.lower().endswith(('.mp4', '.mov', '.mkv'))]
    sent_filenames = [entry['filename'] for entry in history]
    
    available_videos = [v for v in all_videos if v not in sent_filenames]
    
    if not available_videos:
        print("No new videos to send.")
        return

    video_to_send = random.choice(available_videos)
    video_path = os.path.join(VIDEO_FOLDER, video_to_send)
    
    print(f"Selected Video File: {video_to_send}")

    # 3. RANDOM SELECTION (Grid System)
    selected_title = random.choice(TITLES_GRID)
    selected_caption = random.choice(CAPTIONS_GRID)
    
    # Combine content
    full_telegram_caption = f"{selected_title}\n\n{selected_caption}\n{FIXED_HASHTAGS}"
    
    print(f"Generated Title: {selected_title}")
    print(f"Generated Caption: {selected_caption}")

    # 4. SEND TO TELEGRAM
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("Sending to Telegram...")
        with open(video_path, 'rb') as video_file:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
            payload = {
                'chat_id': TELEGRAM_CHAT_ID, 
                'caption': full_telegram_caption
            }
            files = {'video': video_file}
            try:
                requests.post(url, data=payload, files=files)
            except Exception as e:
                print(f"Telegram Error: {e}")

    # 5. SEND TO WEBHOOK
    if WEBHOOK_URL:
        print("Sending to Webhook...")
        # URL construction with your specific repo name
        raw_video_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{BRANCH_NAME}/{VIDEO_FOLDER}/{video_to_send}"
        # Encode spaces if any
        raw_video_url = raw_video_url.replace(" ", "%20")
        
        webhook_data = {
            "video_url": raw_video_url,
            "title": selected_title,
            "caption": selected_caption,
            "hashtags": FIXED_HASHTAGS,
            "insta_hashtags": INSTA_HASHTAGS,
            "youtube_hashtags": YOUTUBE_HASHTAGS, # Naya add kiya gaya
            "facebook_hashtags": FACEBOOK_HASHTAGS, # Naya add kiya gaya
            "source": "AffiliateBot"
        }
        try:
            requests.post(WEBHOOK_URL, json=webhook_data)
            print(f"Webhook Sent: {raw_video_url}")
        except Exception as e:
            print(f"Webhook Error: {e}")

    # 6. UPDATE HISTORY
    new_history.append({
        "filename": video_to_send,
        "date_sent": today.isoformat()
    })
    save_history(new_history)
    print("Automation Complete.")

if __name__ == "__main__":
    run_automation()
