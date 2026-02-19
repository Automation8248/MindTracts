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
GITHUB_REPO = "Automation8248/MindTracts" 
BRANCH_NAME = "main"

# --- DATA GRID (Pre-saved Titles & Captions) ---

# List 1: Titles (Har bar inme se koi ek randomly select hoga)
TITLES_GRID = [
    "Psychology Says You’re Not Imagining This",
    "This Is Why People Suddenly Change",
    "Your Brain Does This Without You Knowing",
    "If Someone Does This, Pay Attention",
    "You Notice This Only When You Like Someone",
    "Your Mind Is Testing You Right Now",
    "People Reveal Themselves With This Habit",
    "The Brain Interprets This As Danger",
    "You Feel Drained For This Hidden Reason",
    "This Behavior Always Means Something",
    "You’ve Seen This But Never Understood It",
    "Your Brain Reacts Faster Than You Think",
    "Why Silence Makes People Uncomfortable",
    "This Small Action Changes How People See You",
    "Your Mind Is Protecting You From This",
    "People Respect You When You Stop Doing This",
    "The Real Reason People Pull Away",
    "You Trust People Who Do This",
    "This Is How The Brain Detects Lies",
    "You Feel Awkward Because Of This Instinct",
    "Your Brain Remembers Emotion, Not Words",
    "People Notice This Before You Speak",
    "This Habit Reveals Confidence Instantly",
    "Why Overthinking Never Stops At Night",
    "Your Brain Predicts People’s Intentions",
    "This Reaction Is Completely Automatic",
    "You Feel Attached Because Of This Trigger",
    "People Mirror You Without Realizing",
    "This Makes Someone Secretly Respect You",
    "The Mind Hates Uncertainty For This Reason",
    "You Feel Ignored Because Of This Signal",
    "Your Brain Treats Rejection Like Pain",
    "This Is Why First Impressions Never Change",
    "People Test You Before Trusting You",
    "You Remember Embarrassing Moments More",
    "Your Brain Searches For Patterns Always",
    "This Expression Reveals True Feelings",
    "Why Quiet People Notice Everything",
    "Your Mind Is Avoiding A Hard Truth",
    "This Is How People Judge You Instantly",
    "You Feel Safe Around People Who Do This",
    "Your Brain Rewards Familiar Behavior",
    "People Distance Themselves For This Reason",
    "This Is A Sign Of Hidden Attraction",
    "Your Brain Hates Being Ignored",
    "You React Emotionally Before Thinking",
    "This Makes Someone Feel Comfortable With You",
    "The Brain Interprets Eye Contact Like This",
    "You Miss Red Flags Because Of This Bias",
    "People Value What Feels Rare",
    "Your Mind Replays Moments To Learn",
    "This Habit Creates Instant Authority",
    "You Feel Anxious When The Brain Predicts Risk",
    "People Like You More When You Do Less",
    "Your Brain Saves Energy With Shortcuts",
    "This Behavior Builds Trust Quickly",
    "You Feel Jealous Because Of Comparison Instinct",
    "The Brain Notices Changes Immediately",
    "People Remember Feelings Over Facts",
    "This Small Pause Changes Conversations",
    "You Connect Faster Through Shared Emotion",
    "Your Mind Prefers Familiar Pain",
    "People Reveal Intentions Under Pressure",
    "This Makes You Seem More Confident",
    "Your Brain Detects Social Hierarchy Fast",
    "You Think About Them For This Reason",
    "The Brain Protects Your Self Image",
    "People Follow Calm Individuals Naturally"
]



# List 2: Captions (Har bar inme se koi ek randomly select hoga)
CAPTIONS_GRID = [
    "Watch till the end.",
    "You needed to hear this today.",
    "Most people never realize this.",
    "Save this for later.",
    "This changes how you see people.",
    "Your brain already noticed it.",
    "Now it makes sense.",
    "Read that again.",
    "You’ve experienced this before.",
    "Nobody talks about this.",
    "Think about it carefully.",
    "This explains a lot.",
    "You’ll notice it everywhere now.",
    "It was always there.",
    "Your mind remembers this.",
    "This is not random.",
    "People do this unconsciously.",
    "You feel it but ignore it.",
    "Your instincts were right.",
    "Pay attention next time.",
    "You can’t unsee this now.",
    "Your brain connects patterns.",
    "This reveals true intentions.",
    "You’ve felt this before.",
    "Your reactions have meaning.",
    "It happens more than you think.",
    "Observe quietly.",
    "There’s always a reason.",
    "Human behavior repeats.",
    "This explains their actions.",
    "Notice the small details.",
    "The mind protects itself.",
    "Emotions leave clues.",
    "Your brain reacts instantly.",
    "The silence says enough.",
    "Patterns never lie.",
    "Trust observation over words.",
    "The brain avoids discomfort.",
    "You sensed it immediately.",
    "Nothing here is accidental.",
    "Behavior shows truth.",
    "You already knew this.",
    "This affects relationships.",
    "Watch people carefully.",
    "The answer is subtle.",
    "Psychology is everywhere.",
    "Your perception shifts now.",
    "Understanding changes reactions.",
    "People reveal themselves slowly.",
    "This changes conversations.",
    "Rewatch and notice more.",
    "You’ll remember this later.",
    "The brain prefers familiarity.",
    "Awareness changes everything.",
    "Think deeper.",
    "Small signs matter.",
    "Your intuition picked it up.",
    "Now you understand why.",
    "Observe before reacting.",
    "Human nature is predictable.",
    "It’s always in the details.",
    "Perception shapes reality.",
    "You saw the sign.",
    "This explains the feeling.",
    "Now watch people again.",
    "Silence reveals intention.",
    "Understanding people is power."
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
"#psychologyfacts #humanbehavior #mindset #selfimprovement #psychologytricks"
"""
YOUTUBE_HASHTAGS = """
.
.
.
" #psychologyfacts #humanbehavior #mindset #selfimprovement #brainfacts #psychologytricks #socialskills #shorts #youtubeshorts #youtubeshorts #youtube #shorts #subscribe #viralshorts"
"""

FACEBOOK_HASHTAGS = """
.
.
.
"#psychologyfacts #humanbehavior #mindset #selfimprovement #learnsomethingnew #factsdaily #socialskills #personality #brainfacts"
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
