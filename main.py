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

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

os.makedirs(TOP_VIDEOS_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
# =================================================

def get_gameplay_center_x(video_path, sample_frames=30):
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

def download_youtube_video(url, output_path):
    """Flexible format downloader to prevent 'format not available' error"""
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best', # Ab yeh kisi bhi format me best quality download karega (webm/mp4)
        'merge_output_format': 'mp4',         # Download hone ke baad automatically mp4 me merge karega
        'outtmpl': output_path,
        'quiet': False,                       # Logs ko on rakha hai taki future me trace karna asan ho
        'cookiefile': 'cookies.txt',
        'nocheckcertificate': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def create_split_short(top_video, bottom_video, output_path, crop_x_ratio):
    crop_filter = f"scale=-1:960,crop=1080:960:iw*{crop_x_ratio}-540:0"

    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', top_video,
        '-t', '60', '-i', bottom_video,
        '-filter_complex',
        f"[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];"
        f"[1:v]{crop_filter}[bottom];"
        f"[top][bottom]vstack=inputs=2,setdar=9/16[v]",
        '-map', '[v]',
        '-map', '1:a',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-shortest',
        output_path
    ]
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
    except Exception as e:
        print(f"Telegram Error: {e}")

def send_to_webhook(video_path, title):
    if not WEBHOOK_URL:
        return
        
    try:
        with open(video_path, 'rb') as video:
            files = {'file': (os.path.basename(video_path), video)}
            data = {'content': f"🤖 **New Short (9:16):** {title}"}
            requests.post(WEBHOOK_URL, data=data, files=files)
    except Exception as e:
        print(f"Webhook Error: {e}")

def process_job():
    print("\n🚀 Starting Automation Job...")
    
    if not os.path.exists(LINKS_FILE):
        print("❌ Error: links.txt missing.")
        return

    with open(LINKS_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    top_videos = [os.path.join(TOP_VIDEOS_FOLDER, f) for f in os.listdir(TOP_VIDEOS_FOLDER) if f.endswith('.mp4')]

    if not urls:
        print("⚠️ No new links found in links.txt.")
        return
    if not top_videos:
        print("❌ Error: top_videos folder is empty.")
        return

    url = urls.pop(0)
    
    with open(LINKS_FILE, 'w') as f:
        for u in urls:
            f.write(f"{u}\n")

    temp_roblox = "temp_roblox.mp4"
    output_short = os.path.join(OUTPUT_FOLDER, f"short_{int(time.time())}.mp4")

    print(f"📥 Downloading: {url}")
    download_youtube_video(url, temp_roblox)

    print("🔍 Analyzing Action Zone...")
    crop_x_ratio = get_gameplay_center_x(temp_roblox)

    print("🎬 Editing Split Screen Video...")
    top_video = top_videos[0]
    create_split_short(top_video, temp_roblox, output_short, crop_x_ratio)

    print("📤 Sending to Platforms...")
    send_to_telegram(output_short, "🎮 New Roblox Short Ready!")
    send_to_webhook(output_short, "New Roblox Short")

    if os.path.exists(temp_roblox):
        os.remove(temp_roblox)
    print("✅ Completed Successfully!")

if __name__ == "__main__":
    process_job()
