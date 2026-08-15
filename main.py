import os
import time
import tempfile
import requests
import yt_dlp

# ==========================================
# CONFIG
# ==========================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
YOUTUBE_COOKIES = os.environ.get("YOUTUBE_COOKIES")

LINK_FILE = "link.txt"
FAILED_FILE = "failed.txt"
DOWNLOAD_DIR = "downloads"

MAX_RETRIES = 3

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ==========================================
# CHECK CONFIG
# ==========================================

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing.")

if not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID is missing.")


# ==========================================
# CREATE TEMP COOKIE FILE
# ==========================================

def create_cookie_file():
    if not YOUTUBE_COOKIES:
        return None

    cookie_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8"
    )

    try:
        cookie_file.write(YOUTUBE_COOKIES)
        cookie_file.close()

        os.chmod(cookie_file.name, 0o600)

        return cookie_file.name

    except Exception:
        cookie_file.close()

        try:
            os.remove(cookie_file.name)
        except Exception:
            pass

        raise


# ==========================================
# READ LINKS
# ==========================================

def read_links():

    if not os.path.exists(LINK_FILE):
        print("❌ link.txt not found.")
        return []

    with open(
        LINK_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return [
            line.strip()
            for line in file
            if line.strip()
        ]


# ==========================================
# REMOVE SUCCESSFUL LINK
# ==========================================

def remove_successful_link(url):

    links = read_links()

    remaining = [
        link
        for link in links
        if link != url
    ]

    with open(
        LINK_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        for link in remaining:
            file.write(link + "\n")


# ==========================================
# SAVE FAILED LINK
# ==========================================

def save_failed_link(url):

    with open(
        FAILED_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(url + "\n")


# ==========================================
# DOWNLOAD VIDEO
# ==========================================

def download_video(url, cookie_file=None):

    print()
    print("==========================================")
    print("Downloading:")
    print(url)
    print("==========================================")

    output_template = os.path.join(
        DOWNLOAD_DIR,
        "%(id)s.%(ext)s"
    )

    options = {
        "format": "bv*+ba/b",

        "merge_output_format": "mp4",

        "outtmpl": output_template,

        "noplaylist": True,

        "retries": 3,

        "fragment_retries": 3,

        "socket_timeout": 30,

        "restrictfilenames": True,

        "quiet": False,

        "no_warnings": False,
    }

    # Use supplied cookies only for authorized access.
    if cookie_file:
        options["cookiefile"] = cookie_file

    try:

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            video_id = info.get("id")

            title = info.get(
                "title",
                "YouTube Video"
            )

            if not video_id:
                print("❌ Video ID not found.")
                return None, None

            possible_files = [
                os.path.join(
                    DOWNLOAD_DIR,
                    f"{video_id}.mp4"
                ),
                os.path.join(
                    DOWNLOAD_DIR,
                    f"{video_id}.mkv"
                ),
                os.path.join(
                    DOWNLOAD_DIR,
                    f"{video_id}.webm"
                ),
                os.path.join(
                    DOWNLOAD_DIR,
                    f"{video_id}.m4v"
                ),
            ]

            for file_path in possible_files:

                if os.path.isfile(file_path):

                    if os.path.getsize(file_path) > 0:

                        print(
                            f"✅ Download complete: {file_path}"
                        )

                        return file_path, title

            filename = ydl.prepare_filename(info)

            if os.path.isfile(filename):

                return filename, title

            print("❌ Downloaded file not found.")

            return None, None

    except Exception as error:

        print(
            f"❌ Download error: {error}"
        )

        return None, None


# ==========================================
# SEND TO TELEGRAM
# ==========================================

def send_to_telegram(video_path, title):

    print()
    print("Sending video to Telegram...")

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    )

    try:

        with open(
            video_path,
            "rb"
        ) as video:

            response = requests.post(

                telegram_url,

                data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "caption": title[:900]
                },

                files={
                    "video": (
                        os.path.basename(video_path),
                        video,
                        "video/mp4"
                    )
                },

                timeout=900
            )

        result = response.json()

        if result.get("ok"):

            print("✅ Sent to Telegram.")

            return True

        print(
            "❌ Telegram error:",
            result
        )

        return False

    except Exception as error:

        print(
            f"❌ Telegram error: {error}"
        )

        return False


# ==========================================
# DELETE LOCAL FILE
# ==========================================

def delete_video(video_path):

    try:

        if os.path.exists(video_path):

            os.remove(video_path)

            print("🗑️ Local file deleted.")

    except Exception as error:

        print(
            f"⚠️ Delete error: {error}"
        )


# ==========================================
# PROCESS URL
# ==========================================

def process_url(url, cookie_file):

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        print(
            f"\nAttempt {attempt}/{MAX_RETRIES}"
        )

        video_path, title = download_video(
            url,
            cookie_file
        )

        if not video_path:

            if attempt < MAX_RETRIES:
                time.sleep(5)

            continue

        telegram_ok = send_to_telegram(
            video_path,
            title
        )

        if telegram_ok:

            remove_successful_link(url)

            delete_video(video_path)

            return True

        delete_video(video_path)

        if attempt < MAX_RETRIES:
            time.sleep(10)

    save_failed_link(url)

    return False


# ==========================================
# MAIN
# ==========================================

def main():

    print()
    print("==========================================")
    print(" YouTube → Telegram Automation")
    print("==========================================")

    links = read_links()

    if not links:
        print("No URLs in link.txt.")
        return

    cookie_file = None

    try:

        cookie_file = create_cookie_file()

        print(
            f"📋 URLs found: {len(links)}"
        )

        successful = 0
        failed = 0

        for index, url in enumerate(
            links,
            start=1
        ):

            print()
            print(
                f"========== {index}/{len(links)} =========="
            )

            if process_url(
                url,
                cookie_file
            ):
                successful += 1
            else:
                failed += 1

            time.sleep(3)

        print()
        print("==========================================")
        print("FINAL RESULT")
        print("==========================================")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print("==========================================")

    finally:

        if cookie_file:

            try:
                os.remove(cookie_file)
                print("🔒 Temporary cookie file removed.")

            except Exception:
                pass


if __name__ == "__main__":
    main()
