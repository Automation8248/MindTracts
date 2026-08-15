import os
import cv2
import numpy as np
import subprocess
import requests
import time
import yt_dlp
from pytubefix import YouTube
from urllib.parse import urlparse, parse_qs

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
# 1. FALLBACK DOWNLOADER ENGINE (The Real APIs)
# =================================================

def extract_video_id(url):
    """URL se YouTube Video ID nikalna APIs ke liye"""
    parsed = urlparse(url)
    if parsed.hostname in ['youtu.be']: return parsed.path[1:]
    if parsed.hostname in ['www.youtube.com', 'youtube.com']:
        return parse_qs(parsed.query).get('v', [None])[0]
    return None

def download_source_1_cobalt(url, output_path):
    """Priority 1: Cobalt API (Direct Server Request)"""
    print("▶️ Attempting Cobalt API...")
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    # Cobalt requires identifying your tool to avoid blocks
    headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AutomationBot/1.0' 
    data = {'url': url, 'videoQuality': '1080', 'filenamePattern': 'classic'}
    
    res = requests.post('https://api.cobalt.tools/api/json', headers=headers, json=data, timeout=15)
    res.raise_for_status()
    download_url = res.json().get('url')
    
    if download_url:
        video_data = requests.get(download_url, stream=True)
        with open(output_path, 'wb') as f:
            for chunk in video_data.iter_content(chunk_size=1024):
                if chunk: f.write(chunk)
        return True
    raise Exception("Cobalt returned invalid response")

def download_source_2_piped(url, output_path):
    """Priority 2: Piped API (Alternative Frontend)"""
    print("▶️ Attempting Piped API...")
    video_id = extract_video_id(url)
    if not video_id: raise Exception("Invalid YouTube URL")
    
    res = requests.get(f'https://pipedapi.kavin.rocks/streams/{video_id}', timeout=15)
    res.raise_for_status()
    streams = res.json().get('videoStreams', [])
    
    # 1080p ya highest available mp4 nikalna
    mp4_streams = [s for s in streams if s.get('format') == 'MPEG_4']
    if not mp4_streams: raise Exception("No MP4 stream found on Piped")
    
    best_stream = sorted(mp4_streams, key=lambda x: x.get('bitrate', 0), reverse=True)[0]
    video_data = requests.get(best_stream['url'], stream=True)
    with open(output_path, 'wb') as f:
        for chunk in video_data.iter_content(chunk_size=1024):
            if chunk: f.write(chunk)
    return True

def download_source_3_pytubefix(url, output_path):
    """Priority 3: Pytubefix with PO Token"""
    print("▶️ Attempting Pytubefix...")
    yt = YouTube(url, client='WEB', use_po_token=True)
    stream = yt.streams.filter(file_extension='mp4').get_highest_resolution()
    stream.download(filename=output_path)
    return True

def download_source_4_ytdlp(url, output_path):
    """Priority 4: yt-dlp (The Ultimate Fallback)"""
    print("▶️ Attempting yt-dlp...")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'nocheckcertificate': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return True

def robust_download(url, output_path):
    """Cycles through downloader APIs one by one until success."""
    
    download_sources = [
        ("Cobalt API", download_source_1_cobalt),
        ("Piped API", download_source_2_piped),
        ("Pytubefix", download_source_3_pytubefix),
        ("yt-dlp", download_source_4_ytdlp)
    ]
    
    for source_name, download_func in download_sources:
        try:
            download_func(url, output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                print(f"✅ Success! Downloaded via {source_name}")
                return True
            else:
                raise ValueError("File is empty or corrupted.")
        except Exception as e:
            print(f"❌ {source_name} failed: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            print("🔄 Switching to next source...")
            time.sleep(2)
            
    print("❌ All API sources failed to download the video.")
    return False


# =================================================
# 2. VIDEO EDITING & DELIVERY ENGINE
# =================================================

def get_gameplay_center_x(video_path, sample_frames=30):
    cap = cv2.VideoCapture(video_path)
    ret, prev_frame = cap.read()
    if not ret:
        cap.release()
        return 0.5
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    width = prev_gray.shape[1]
    x_centers = []
    frame_count = 0
    while cap.isOpened() and frame_count < sample_frames * 5:
        ret, frame = cap.read()
        if not ret: break
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
    return np.mean(x_centers) / width if x_centers else 0.5

def create_split_short(top_video, bottom_video, output_path, crop_x_ratio):
    crop_filter = f"scale=-1:960,crop=1080:960:iw*{crop_x_ratio}-540:0"
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', top_video, '-t', '60', '-i', bottom_video,
        '-filter_complex',
        f"[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];"
        f"[1:v]{crop_filter}[bottom];"
        f"[top][bottom]vstack=inputs=2,setdar=9/16[v]",
        '-map', '[v]', '-map', '1:a',
        '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
        output_path
    ]
    print("✂️ Editing split-screen video with FFmpeg...")
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def send_to_telegram(video_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, 'rb') as video:
            requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}, files={'video': video})
            print("🚀 Sent to Telegram!")
    except Exception as e:
        print(f"Telegram Error: {e}")

def send_to_webhook(video_path, title):
    if not WEBHOOK_URL: return
    try:
        with open(video_path, 'rb') as video:
            requests.post(WEBHOOK_URL, data={'content': f"🤖 **New Short Edited (9:16):** {title}"}, files={'file': (os.path.basename(video_path), video)})
            print("🚀 Sent to Webhook!")
    except Exception as e:
        print(f"Webhook Error: {e}")

def process_job():
    print("\n==================================")
    print("🚀 Starting Multi-API Automation Job...")
    print("==================================")
    
    if not os.path.exists(LINKS_FILE):
        print("❌ Error: links.txt file not found.")
        return

    with open(LINKS_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    top_videos = [os.path.join(TOP_VIDEOS_FOLDER, f) for f in os.listdir(TOP_VIDEOS_FOLDER) if f.endswith('.mp4')]

    if not urls or not top_videos:
        print("⚠️ No links left or top_videos folder is empty.")
        return

    url = urls.pop(0)
    with open(LINKS_FILE, 'w') as f:
        for u in urls: f.write(f"{u}\n")

    temp_roblox = "temp_roblox.mp4"
    output_short = os.path.join(OUTPUT_FOLDER, f"short_{int(time.time())}.mp4")

    # Step 1: Robust Download
    print(f"📥 Processing Link: {url}")
    success = robust_download(url, temp_roblox)
    
    if not success:
        print("❌ Stopping process due to total download failure.")
        return

    # Step 2: Edit
    crop_x_ratio = get_gameplay_center_x(temp_roblox)
    create_split_short(top_videos[0], temp_roblox, output_short, crop_x_ratio)

    # Step 3: Delivery
    send_to_telegram(output_short, "🎮 New Roblox Short Ready!")
    send_to_webhook(output_short, "New Roblox Short")

    # Cleanup
    if os.path.exists(temp_roblox): os.remove(temp_roblox)
    print("✅ Daily Job Completed Successfully!")

if __name__ == "__main__":
    process_job()
