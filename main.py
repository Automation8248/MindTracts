import instaloader
import requests
from telegram import Bot
import os
import sys
import time

# --- CONFIG (GitHub Secrets se lega) ---
TARGET_USERNAME = "virtualaarvi"     # Jiska video download karna hai
BOT_USERNAME = os.getenv("BOT_USERNAME") # Fake Account User
BOT_PASSWORD = os.getenv("BOT_PASSWORD") # Fake Account Pass
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# --- CHECK SECRETS ---
if not BOT_USERNAME or not BOT_PASSWORD:
    print("Error: GitHub Secrets mein BOT_USERNAME aur BOT_PASSWORD add karo!")
    sys.exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

# --- SETUP & LOGIN ---
L = instaloader.Instaloader(
    download_videos=True, 
    save_metadata=False, 
    download_pictures=False,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

try:
    print(f"Logging in as {BOT_USERNAME}...")
    L.login(BOT_USERNAME, BOT_PASSWORD)
    print("✅ Login Successful!")
except Exception as e:
    print(f"❌ Login Failed: {e}")
    print("Agar 'Checkpoint' error hai, to fake account par login karke approve karo.")
    # Login fail hone par bhi try karega, shayad public access mil jaye
    pass 

# --- MAIN WORK ---
try:
    print(f"Checking posts for: {TARGET_USERNAME}")
    profile = instaloader.Profile.from_username(L.context, TARGET_USERNAME)
    
    # Last video check
    try:
        with open("last_video.txt", "r") as f:
            last_video = f.read().strip()
    except:
        last_video = ""

    posts = profile.get_posts()
    
    # Sirf top 5 posts check karenge
    count = 0
    for post in posts:
        count += 1
        if count > 5: break

        if post.shortcode == last_video:
            print("⏳ No new videos.")
            break
        
        if post.is_video:
            print(f"🚀 New Video Found: {post.shortcode}")
            
            # Caption Logic
            caption_text = post.caption if post.caption else ""
            final_caption = f"{caption_text}\n\n🎥 Credit: @{TARGET_USERNAME}"

            try:
                # Telegram
                bot.send_video(chat_id=TELEGRAM_CHAT_ID, video=post.video_url, caption=final_caption)
                print("✅ Telegram Sent")

                # Webhook
                if WEBHOOK_URL:
                    requests.post(WEBHOOK_URL, json={
                        "username": TARGET_USERNAME,
                        "video_id": post.shortcode,
                        "caption": caption_text,
                        "status": "posted"
                    })
                    print("✅ Webhook Sent")

                # Save ID
                with open("last_video.txt", "w") as f:
                    f.write(post.shortcode)
                
                break # Done
            except Exception as e:
                print(f"❌ Sending Error: {e}")

except Exception as e:
    print(f"❌ Script Error: {e}")
    sys.exit(1)
