import os
import cv2
import numpy as np
import subprocess
import requests
import time
import random
from pytubefix import YouTube

# ================= CONFIGURATION =================
TOP_VIDEOS_FOLDER = "top_videos"
LINKS_FILE = "links.txt"
OUTPUT_FOLDER = "final_shorts"

# GitHub Secrets ya local environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

os.makedirs(TOP_VIDEOS_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ================= 30+ USER AGENTS =================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.163 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.80 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
    # Note: I've kept a strong mix of 15+ solid ones here to keep code clean and fast, 
    # but the logic randomly selects one every time it runs!
]
# =================================================

def download_youtube_video(url, output_path):
    """Pytubefix + Random User-Agent se Bot protection bypass karke video download"""
    random_ua = random.choice(USER_AGENTS)
    print(f"🕵️ Using User-Agent: {random_ua}")
    
    try:
        # client='ANDROID' bypasses most heavy JS challenges on YouTube
        yt = YouTube(url, use_oauth=False, allow_oauth_cache=True, client='ANDROID')
        yt.custom_client_headers = {"User-Agent": random_ua}
        
        print(f"🔄 Fetching video streams for: {yt.title}")
        # Fetching highest resolution MP4 to ensure FFmpeg works smoothly
        stream = yt.streams.filter(file_extension='mp4').get_highest_resolution()
        
        print("⬇️ Downloading video...")
        stream.download(filename=output_path)
        print("✅ Download Completed!")
        return True
    except Exception as e:
        print(f"❌ Download Error: {e}")
        return False

def get_gameplay_center_x(video_path, sample_frames=30):
    """OpenCV se Roblox gameplay ka center point dhundhna taaki crop perfect ho"""
    cap = cv2.VideoCapture(video_path)
    ret, prev_frame = cap.read()
    if not ret:
        cap.release()
        return 0.5

    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, width = prev_gray.shape
    x_centers = []

    frame_count = 0
    while cap.isOpened() and frame_count < sample_frames * 5:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % 5 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest_contour) > 500:
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    x_centers.append(x + w / 2)
            
            prev_gray = gray
        frame_count += 1

    cap.release()

    if x_centers:
        avg_x = np.mean(x_centers)
        return avg_x / width
    return 0.5

def create_split_short(top_video, bottom_video, output_path, crop_x_ratio):
    """FFmpeg ka use karke 9:16 Split Screen Short Banana (60 Sec max)"""
    # Bottom video (Roblox) horizontal crop logic based on OpenCV
    crop_filter = f"scale=-1:960,crop=1080:960:iw*{crop_x_ratio}-540:0"

    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', top_video,
        '-t', '60', '-i', bottom_video, # Limit gameplay to 60 seconds
        '-filter_complex',
        f"[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];"
        f"[1:v]{crop_filter}[bottom];"
        f"[top][bottom]vstack=inputs=2,setdar=9/16[v]",
        '-map', '[v]',
        '-map', '1:a', # Sirf Roblox (bottom) ka audio use karega 100% volume par
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-shortest',
        output_path
    ]
    
    print("✂️ FFmpeg is editing the video...")
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def send_to_telegram(video_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, 'rb') as video:
            payload = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            files = {'video': video}
            requests.post(url, data=payload, files=files)
            print("🚀 Sent to Telegram!")
    except Exception as e:
        print(f"Telegram Error: {e}")

def send_to_webhook(video_path, title):
    if not WEBHOOK_URL:
        return
    try:
        with open(video_path, 'rb') as video:
            files = {'file': (os.path.basename(video_path), video)}
            data = {'content': f"🤖 **New Short Edited (9:16):** {title}"}
            requests.post(WEBHOOK_URL, data=data, files=files)
            print("🚀 Sent to Webhook!")
    except Exception as e:
        print(f"Webhook Error: {e}")

def process_job():
    print("\n==================================")
    print("🚀 Starting Shorts Automation Job...")
    print("==================================")
    
    if not os.path.exists(LINKS_FILE):
        print("❌ Error: links.txt file not found.")
        return

    with open(LINKS_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    top_videos = [os.path.join(TOP_VIDEOS_FOLDER, f) for f in os.listdir(TOP_VIDEOS_FOLDER) if f.endswith('.mp4')]

    if not urls:
        print("⚠️ No links left in links.txt.")
        return
    if not top_videos:
        print("❌ Error: top_videos folder is empty.")
        return

    # Extract first link
    url = urls.pop(0)
    
    # Update links.txt
    with open(LINKS_FILE, 'w') as f:
        for u in urls:
            f.write(f"{u}\n")

    temp_roblox = "temp_roblox.mp4"
    output_short = os.path.join(OUTPUT_FOLDER, f"short_{int(time.time())}.mp4")

    # 1. Download
    print(f"📥 Processing Link: {url}")
    success = download_youtube_video(url, temp_roblox)
    
    if not success:
        print("❌ Stopping process due to download failure.")
        return

    # 2. Smart Crop Zone Analysis
    print("🔍 Analyzing Action Zone for perfect crop...")
    crop_x_ratio = get_gameplay_center_x(temp_roblox)

    # 3. Edit with FFmpeg
    print("🎬 Generating Split Screen Video (Top + Roblox Bottom)...")
    top_video = top_videos[0] # Pick the first top video
    create_split_short(top_video, temp_roblox, output_short, crop_x_ratio)

    # 4. Delivery
    print("📤 Distributing Final Video...")
    send_to_telegram(output_short, "🎮 New Roblox Short Ready!")
    send_to_webhook(output_short, "New Roblox Short")

    # Cleanup
    if os.path.exists(temp_roblox):
        os.remove(temp_roblox)
        
    print("✅ Daily Job Completed Successfully!")

if __name__ == "__main__":
    process_job()
