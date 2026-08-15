import os
import cv2
import numpy as np
import subprocess
import requests
import time
import yt_dlp
import random
import string
from pytubefix import YouTube
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= CONFIGURATION =================
TOP_VIDEOS_FOLDER = "top_videos"
LINKS_FILE = "links.txt"
OUTPUT_FOLDER = "final_shorts"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

os.makedirs(TOP_VIDEOS_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# All Hosts in Priority Order[cite: 1]
UPLOAD_HOSTS = [
    "gofile", "pixeldrain", "litterbox", "uguu", "pomf", "fileio", "0x0_st",
    "transfer_sh", "tmpfiles", "krakenfiles", "buzzheavier", "send_cm",
    "anontransfer", "filebin", "postimages", "imgbb"
]

# =================================================
# 1. JABARDASTI (AGGRESSIVE) DOWNLOADER ENGINE
# =================================================

def extract_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname in ['youtu.be']: return parsed.path[1:]
    if parsed.hostname in ['www.youtube.com', 'youtube.com']:
        return parse_qs(parsed.query).get('v', [None])[0]
    return None

def download_source_1_ytdlp_aggressive(url, output_path):
    """JABARDASTI METHOD 1: Bypasses JS challenge using Node.js & Multiple Clients"""
    print("▶️ Attempting yt-dlp (Ultimate JS Bypass with Node.js)...")
    ydl_opts = {
        'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b', # Best merged format
        'outtmpl': output_path,
        'quiet': False, # Ab humein logs dikhenge agar fail hua toh
        'nocheckcertificate': True,
        'cookiefile': 'cookies.txt',
        # Multiple clients pass kar rahe hain, YouTube ek ko block karega toh dusra chalega
        'extractor_args': {'youtube': ['player_client=web,tv,ios']} 
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return True

def download_source_2_pytubefix_android(url, output_path):
    """JABARDASTI METHOD 2: Pytubefix without PO token blocking prompt"""
    print("▶️ Attempting Pytubefix (Silent Android Mode)...")
    # use_po_token hatakar client='ANDROID' kiya taaki EOF error na aaye
    link = YouTube(url, client='ANDROID') 
    video = link.streams.get_highest_resolution()
    video.download(filename=output_path)
    return True

def download_source_3_piped_api(url, output_path):
    """JABARDASTI METHOD 3: Third-party YouTube Frontend API"""
    print("▶️ Attempting Piped API (Alternative Server)...")
    video_id = extract_video_id(url)
    if not video_id: raise Exception("Invalid ID")
    res = requests.get(f'https://pipedapi.kavin.rocks/streams/{video_id}', timeout=15)
    res.raise_for_status()
    streams = res.json().get('videoStreams', [])
    best_stream = sorted([s for s in streams if s.get('format') == 'MPEG_4'], key=lambda x: x.get('bitrate', 0), reverse=True)[0]
    video_data = requests.get(best_stream['url'], stream=True)
    with open(output_path, 'wb') as f:
        for chunk in video_data.iter_content(chunk_size=1024):
            if chunk: f.write(chunk)
    return True

def robust_download(url, output_path):
    download_sources = [
        ("yt-dlp Aggressive", download_source_1_ytdlp_aggressive),
        ("Pytubefix Android", download_source_2_pytubefix_android),
        ("Piped API", download_source_3_piped_api)
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
            print("🔄 Switching to next aggressive source...")
            time.sleep(2)
            
    print("❌ All jabardasti API sources failed to download the video.")
    return False

# =================================================
# 2. VIDEO EDITING ENGINE (FFmpeg)
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

# =================================================
# 3. PARALLEL UPLOAD AND DELIVERY ENGINE[cite: 1]
# =================================================

def send_to_telegram(video_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, 'rb') as video:
            requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}, files={'video': video})
            print("🚀 Sent to Telegram!")
    except Exception as e:
        print(f"Telegram Error: {e}")

# (Upload functions collapsed for readability, but kept exactly as you requested)
def upload_to_gofile(file_path):
    try:
        r = requests.get("https://api.gofile.io/getServer", timeout=10)
        server = r.json()['data']['server']
        url = f"https://{server}.gofile.io/uploadFile"
        with open(file_path, 'rb') as f:
            res = requests.post(url, files={'file': f}, timeout=300)
            if res.json().get('status') == 'ok': return f"https://gofile.io/d/{res.json()['data']['code']}"
    except: pass
    return None

def upload_to_pixeldrain(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://pixeldrain.com/api/file", files={'file': f}, timeout=300)
            if r.status_code == 200: return f"https://pixeldrain.com/u/{r.json()['id']}"
    except: pass
    return None

def upload_to_litterbox(file_path):
    try:
        with open(file_path, 'rb') as f:
            files = {'reqtype': (None, 'fileupload'), 'time': (None, '72h'), 'file': f}
            r = requests.post("https://litterbox.catbox.moe/resources/upload.php", files=files, timeout=300)
            if r.status_code == 200 and r.text.startswith("http"): return r.text.strip()
    except: pass
    return None

def upload_to_uguu(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://uguu.se/upload", files={'files[]': f}, timeout=180)
            if r.status_code == 200: return r.json()[0]['url']
    except: pass
    return None

def upload_to_pomf(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://pomf.cat/upload.php", files={'files[]': f}, timeout=180)
            if r.status_code == 200: return "https://a.pomf.cat/" + r.json()['files'][0]['url']
    except: pass
    return None

def upload_to_fileio(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://file.io", files={'file': f}, timeout=180)
            if r.json().get('success'): return r.json()['link']
    except: pass
    return None

def upload_to_0x0_st(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://0x0.st", files={'file': f}, timeout=180)
            if r.status_code == 200: return r.text.strip()
    except: pass
    return None

def upload_to_transfer_sh(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.put(f"https://transfer.sh/{os.path.basename(file_path)}", data=f, timeout=180)
            if r.status_code == 200: return r.text.strip()
    except: pass
    return None

def upload_to_tmpfiles(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://tmpfiles.org/api/v1/upload", files={'file': f}, timeout=180)
            if r.status_code == 200: return "https://tmpfiles.org/" + r.json()['data']['url'].split('/')[-1]
    except: pass
    return None

def upload_to_krakenfiles(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://krakenfiles.com/api/upload", files={'file': f}, timeout=300)
            if r.status_code == 200: return r.json().get('data', {}).get('url')
    except: pass
    return None

def upload_to_buzzheavier(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://buzzheavier.com/upload", files={'file': f}, timeout=300)
            if r.status_code == 200: return r.text.strip()
    except: pass
    return None

def upload_to_send_cm(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://send.cm/api/upload", files={'file': f}, timeout=180)
            if r.status_code == 200: return r.json().get('url')
    except: pass
    return None

def upload_to_anontransfer(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://anontransfer.com/api/upload", files={'file': f}, timeout=180)
            if r.status_code == 200: return r.json().get('url')
    except: pass
    return None

def upload_to_filebin(file_path):
    try:
        bin_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        with open(file_path, 'rb') as f:
            r = requests.post(f"https://filebin.net/{bin_name}/{os.path.basename(file_path)}", data=f, timeout=180)
            if r.status_code in (200, 201): return f"https://filebin.net/{bin_name}"
    except: pass
    return None

def upload_to_postimages(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://postimages.org/json/rr", files={'file': f}, data={'num': '1'}, timeout=180)
            if r.status_code == 200: return r.json().get('url')
    except: pass
    return None

def upload_to_imgbb(file_path):
    try:
        with open(file_path, 'rb') as f:
            r = requests.post("https://api.imgbb.com/1/upload", files={'image': f}, timeout=180)
            if r.status_code == 200: return r.json()['data']['url']
    except: pass
    return None

def upload_and_send_webhook(host, file_path, original_url):
    """Host check and individual Webhook trigger[cite: 1]"""
    link = None
    if host == "gofile": link = upload_to_gofile(file_path)
    elif host == "pixeldrain": link = upload_to_pixeldrain(file_path)
    elif host == "litterbox": link = upload_to_litterbox(file_path)
    elif host == "uguu": link = upload_to_uguu(file_path)
    elif host == "pomf": link = upload_to_pomf(file_path)
    elif host == "fileio": link = upload_to_fileio(file_path)
    elif host == "0x0_st": link = upload_to_0x0_st(file_path)
    elif host == "transfer_sh": link = upload_to_transfer_sh(file_path)
    elif host == "tmpfiles": link = upload_to_tmpfiles(file_path)
    elif host == "krakenfiles": link = upload_to_krakenfiles(file_path)
    elif host == "buzzheavier": link = upload_to_buzzheavier(file_path)
    elif host == "send_cm": link = upload_to_send_cm(file_path)
    elif host == "anontransfer": link = upload_to_anontransfer(file_path)
    elif host == "filebin": link = upload_to_filebin(file_path)
    elif host == "postimages": link = upload_to_postimages(file_path)
    elif host == "imgbb": link = upload_to_imgbb(file_path)

    if link and link.startswith("http"):
        print(f"✅ SUCCESS → {host.upper()}: {link}")
        if WEBHOOK_URL:
            try:
                payload = {
                    "url": link,
                    "host": host,
                    "original_url": original_url,
                    "title": f"Roblox Short {int(time.time())}",
                    "size_mb": round(os.path.getsize(file_path) / (1024 * 1024), 2),
                    "status": "success"
                }
                requests.post(WEBHOOK_URL, json=payload, timeout=10)
            except Exception as e:
                print(f"⚠️ Webhook error for {host}: {e}")
        return (host, link)
    else:
        print(f"❌ Failed → {host.upper()}")
        return None

# =================================================
# 4. MAIN JOB PROCESSOR
# =================================================

def process_job():
    print("\n==================================")
    print("🚀 Starting Aggressive Automation Job...")
    print("==================================")
    
    if not os.path.exists(LINKS_FILE):
        print(f"❌ Error: {LINKS_FILE} file not found.")
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

    # Step 3: Telegram Delivery
    send_to_telegram(output_short, "🎮 New Roblox Short Ready!")
    
    # Step 4: Parallel Uploads to All Hosts + Webhooks[cite: 1]
    print("\n🚀 Starting parallel uploads to file hosts...\n")
    successful_uploads = []
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_host = {executor.submit(upload_and_send_webhook, host, output_short, url): host 
                         for host in UPLOAD_HOSTS}
        
        for future in as_completed(future_to_host):
            result = future.result()
            if result:
                successful_uploads.append(result)

    print(f"\n🎉 Total Successful Uploads: {len(successful_uploads)}")

    # Cleanup
    if os.path.exists(temp_roblox): os.remove(temp_roblox)
    if os.path.exists(output_short): os.remove(output_short)
    print("✅ Daily Job Completed Successfully!")

if __name__ == "__main__":
    process_job()
