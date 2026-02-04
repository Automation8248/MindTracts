import os
import requests

# GitHub Secrets
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

VIDEO_DIR = "videos"

def upload_to_catbox(file_path):
    """वीडियो को Catbox.moe पर अपलोड करके डायरेक्ट लिंक देता है"""
    url = "https://catbox.moe/user/api.php"
    data = {"reqtype": "fileupload"}
    try:
        with open(file_path, "rb") as f:
            files = {"fileToUpload": f}
            response = requests.post(url, data=data, files=files, timeout=40)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Catbox Upload Failed: {e}")
        return None

def main():
    # 1. फोल्डर चेक करना
    if not os.path.exists(VIDEO_DIR):
        print(f"Error: '{VIDEO_DIR}' folder nahi mila.")
        return

    # 2. केवल वीडियो फाइल्स को ही चुनना (Filter logic)
    video_files = sorted([f for f in os.listdir(VIDEO_DIR) if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))])
    
    if not video_files:
        print("Folder mein koi video file (.mp4, .mkv etc) nahi mili.")
        return

    # पहली वीडियो फाइल को प्रोसेस के लिए उठाना
    video_to_process = video_files[0]
    file_path = os.path.join(VIDEO_DIR, video_to_process)
    
    # फाइल के नाम से टाइटल बनाना (एक्सटेंशन हटाकर)
    clean_title = os.path.splitext(video_to_process)[0]

    # 3. Catbox पर अपलोड करना
    catbox_url = upload_to_catbox(file_path)

    if catbox_url:
        seo_hashtags = "#DidYouKnow #Fact #Facts #AmazingFacts #InterestingFacts #TrueFacts #MindBlowingFacts #DailyFacts #RandomFacts #FunFacts #Knowledge #KnowledgeIsPower #LearnSomethingNew #Educational #Education #Info #Information #GeneralKnowledge #GK #ScienceFacts #TechFacts #PsychologyFacts #HistoryFacts #BusinessFacts #MoneyFacts #HealthFacts #LifeFacts #MotivationFacts #Truth #Reality #ReelsIndia #InstaReels #ViralReels #TrendingReels #ExplorePage #YoutubeShorts #ShortsVideo #ViralVideo"


        # --- टेलीग्राम फॉर्मेट (Direct Video, No Hash) ---
        tg_caption = (
            f"New video post\n"
            f".\n"
            f".\n"
            f".\n"
            f".\n"
            f".\n"
            f"{seo_hashtags}"
        )

        # --- वेबहुक फॉर्मेट (Caption + Hashtags) ---
        webhook_caption = f"New video post\n{seo_hashtags}"

        # 4. टेलीग्राम पर भेजना (Direct Video File)
        if BOT_TOKEN and CHAT_ID:
            try:
                tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
                with open(file_path, "rb") as video:
                    requests.post(tg_url, files={"video": video}, data={"chat_id": CHAT_ID, "caption": tg_caption}, timeout=40)
                print("Telegram: Video file successfully sent.")
            except Exception as tg_err:
                print(f"Telegram Error: {tg_err}")

        # 5. वेबहुक पर भेजना (Make.com Logic)
        if WEBHOOK_URL:
            try:
                # url = Catbox Link, caption = Text + Hashtags
                payload = {
                    "url": catbox_url, 
                    "title": clean_title, 
                    "caption": webhook_caption
                }
                requests.post(WEBHOOK_URL, json=payload, timeout=15)
                print("Webhook: Success.")
            except Exception as web_err:
                print(f"Webhook Failed: {web_err}")
        else:
            print("Warning: Webhook URL missing in Secrets.")

        # 6. केवल इस्तेमाल हुई फाइल को डिलीट करना
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleanup: {video_to_process} deleted.")

        print(f"Workflow Complete! Processed: {catbox_url}")
    else:
        print("Catbox Upload Failed. Skipping post.")

if __name__ == "__main__":
    main()
