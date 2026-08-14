import os
import cv2
import numpy as np
import subprocess
import yt_dlp
import requests
import time

# ================= CONFIGURATION =================
TOP_VIDEOS_FOLDER = "top_videos"
LINKS_FILE = "links.txt"
OUTPUT_FOLDER = "final_shorts"

# GitHub Secrets se Tokens fetch karega
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

os.makedirs(TOP_VIDEOS_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
# =================================================

def get_gameplay_center_x(video_path, sample_frames=30):
    """
    OpenCV ka use karke gameplay mein motion/action ka center point (X-coordinate) find karta hai
    taaki 9:16 vertical crop action ke center mein rahe.
    """
    cap = cv2.VideoCapture(video_path)
    ret, prev_frame = cap.read()
    if not ret:
        cap.release()
        return 0.5  # Default center (50%)

    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    height, width = prev_gray.shape
    x_centers = []

    frame_count = 0
    while cap.isOpened() and frame_count < sample_frames * 5:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % 5 == 0:  # Sample every 5th frame for performance
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            
            # Find motion contours
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
        return avg_x / width  # Returns percentage offset from left (0.0 to 1.0)
    return 0.5

def download_youtube_video(url, output_path):
    """yt-dlp se best quality video download karna"""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': output_path,
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def create_split_short(top_video, bottom_video, output_path, crop_x_ratio):
    """
    FFmpeg se video crop karke, split screen merge karega STRICTLY in 9:16 format (1080x1920)
    """
    # 9:16 Resolution = 1080x1920 total.
    # Split in half vertically = 1080x960 per video.
    
    # Bottom video (gameplay) ke liye dynamic motion-based horizontal crop
    crop_filter = f"scale=-1:960,crop=1080:960:iw*{crop_x_ratio}-540:0"

    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', top_video,
        '-t', '60', '-i', bottom_video, # Limit bottom video to 60 seconds
        '-filter_complex',
        # Top video ko strictly 1080x960 banayega
        f"[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];"
        # Bottom video ko gameplay action ke hisaab se 1080x960 banayega
        f"[1:v]{crop_filter}[bottom];"
        # Dono ko upar-niche jodkar exactly 9:16 Aspect Ratio set karega
        f"[top][bottom]vstack=inputs=2,setdar=9/16[v]",
        '-map', '[v]',
        '-map', '1:a',  # Sirf Roblox Gameplay Audio 100% volume par
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-shortest',
        output_path
    ]
    
    # Command run karna
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def send_to_telegram(video_path, caption):
    """Telegram par final short send karna"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram Credentials missing, skipping Telegram upload.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, 'rb') as video:
            payload = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            files = {'video': video}
            res = requests.post(url, data=payload, files=files)
            if res.status_code == 200:
                print("✅ Successfully sent to Telegram!")
            else:
                print(f"❌ Telegram Error: {res.text}")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

def send_to_webhook(video_path, title):
    """Discord/N8n Webhook par final short send karna"""
    if not WEBHOOK_URL:
        print("⚠️ Webhook URL missing, skipping Webhook upload.")
        return
        
    try:
        with open(video_path, 'rb') as video:
            files = {'file': (os.path.basename(video_path), video)}
            data = {'content': f"🤖 **New Short Generated (9:16):** {title}"}
            res = requests.post(WEBHOOK_URL, data=data, files=files)
            if res.status_code in [200, 204]:
                print("✅ Successfully sent to Webhook!")
            else:
                print(f"❌ Webhook Error: {res.text}")
    except Exception as e:
        print(f"❌ Failed to send Webhook: {e}")

def process_job():
    print("\n🚀 Starting GitHub Actions Automation Job...")
    
    if not os.path.exists(LINKS_FILE):
        print("❌ Error: links.txt file nahi mili.")
        return

    with open(LINKS_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    top_videos = [os.path.join(TOP_VIDEOS_FOLDER, f) for f in os.listdir(TOP_VIDEOS_FOLDER) if f.endswith('.mp4')]

    if not urls:
        print("⚠️ Empty links.txt file. No new videos to process.")
        return
    if not top_videos:
        print("❌ Error: top_videos folder khali hai. Kam se kam ek video zaroori hai.")
        return

    # Pehla URL nikalna
    url = urls.pop(0)
    
    # links.txt ko update karna (taaki next time same link use na ho)
    with open(LINKS_FILE, 'w') as f:
        for u in urls:
            f.write(f"{u}\n")

    temp_roblox = "temp_roblox.mp4"
    output_short = os.path.join(OUTPUT_FOLDER, f"short_{int(time.time())}.mp4")

    print(f"📥 Downloading Roblox Video: {url}")
    download_youtube_video(url, temp_roblox)

    print("🔍 Analyzing gameplay action zone (OpenCV)...")
    crop_x_ratio = get_gameplay_center_x(temp_roblox)
    print(f"🎯 Gameplay Pinpoint Center Ratio: {crop_x_ratio:.2f}")

    print("🎬 Generating 9:16 Split Screen Short Video...")
    top_video = top_videos[0]  # Folder ka pehla top video use karega
    create_split_short(top_video, temp_roblox, output_short, crop_x_ratio)

    print("📤 Sending Output File to platforms...")
    send_to_telegram(output_short, "🎮 New Roblox Short Ready! (9:16 Aspect Ratio)")
    send_to_webhook(output_short, "New Roblox Short")

    # Cleanup temp video to save space
    if os.path.exists(temp_roblox):
        os.remove(temp_roblox)

    print("✅ Daily Job Completed Successfully!")

if __name__ == "__main__":
    process_job()
