import os
import shutil
from time import sleep
from datetime import datetime
from pathlib import Path
import requests
from urllib.parse import urljoin, urlparse
import subprocess
from Crypto.Cipher import AES

MAX_RETRIES = 3
success = []
# -------------------------------
# Download segment function
# -------------------------------
def download_segment(session, ts_url, seg_path, index, total, decrypt_key=None, iv=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(ts_url, stream=True, timeout=15)
            if r.status_code != 200:
                raise Exception(f"Status code {r.status_code}")
            data = r.content
            if decrypt_key:
                cipher = AES.new(decrypt_key, AES.MODE_CBC, iv)
                data = cipher.decrypt(data)
            with open(seg_path, "wb") as f:
                f.write(data)
            if os.path.getsize(seg_path) == 0:
                raise Exception("Empty file")
            print(f"[{index}/{total}] Downloaded: {ts_url}")
            return True
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"[*] Retry {attempt} for {ts_url} due to error: {e}")
                sleep(2)
            else:
                raise Exception(f"Failed to download {ts_url} after {MAX_RETRIES} attempts: {e}")

# -------------------------------
# Parse m3u8 playlist
# -------------------------------
def parse_m3u8(session, url):
    res = session.get(url, timeout=15)
    res.raise_for_status()
    text = res.text

    # Master playlist check
    if "#EXT-X-STREAM-INF" in text:
        lines = [line.strip() for line in text.split("\n") if line and not line.startswith("#")]
        url = urljoin(url, lines[-1])  # เลือก playlist คุณภาพสูงสุด
        res = session.get(url, timeout=15)
        res.raise_for_status()
        text = res.text

    # AES-128 key detection
    key = None
    iv = None
    lines = text.split("\n")
    ts_files = []
    for line in lines:
        line = line.strip()
        if line.startswith("#EXT-X-KEY"):
            if 'URI="' in line:
                uri_part = line.split('URI="')[1].split('"')[0]
                key_url = urljoin(url, uri_part)
                key_data = session.get(key_url, timeout=15).content
                key = key_data
                if "IV=" in line:
                    iv_hex = line.split("IV=0x")[1].split(",")[0]
                    iv = bytes.fromhex(iv_hex)
                else:
                    iv = key_data[:16]
        elif line and not line.startswith("#"):
            ts_files.append(line)
    return ts_files, url, key, iv

# -------------------------------
# Download m3u8 and merge
# -------------------------------
def download_m3u8(url, output_file, headers=None):
    session = requests.Session()
    
    # Auto Referer if headers not provided
    if not headers:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}{os.path.dirname(parsed.path)}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": base,
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Cookie": ""
        }
    session.headers.update(headers)

    ts_files, base_url, key, iv = parse_m3u8(session, url)
    if not ts_files:
        raise Exception("No TS segments found!")

    os.makedirs("segments", exist_ok=True)
    seg_paths = []

    print(f"[+] Downloading {len(ts_files)} segments sequentially...")
    for i, ts_name in enumerate(ts_files):
        ts_url = urljoin(base_url, ts_name)
        seg_path = f"segments/seg_{i}.ts"
        download_segment(session, ts_url, seg_path, i + 1, len(ts_files), key, iv)
        seg_paths.append(seg_path)

    list_file = "segments_list.txt"
    with open(list_file, "w") as f:
        for seg in seg_paths:
            f.write(f"file '{seg}'\n")

    print("[+] Merging video using ffmpeg...")
    subprocess.run([
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_file
    ], check=True)

    # Cleanup temporary files
    shutil.rmtree("segments", ignore_errors=True)
    if Path(list_file).exists():
        Path(list_file).unlink()
    print("[+] Temporary files cleaned up")
    print("[+] SUCCESS! Video saved as:", output_file)
    success.append(f"URL : {url}\nFile : {output_file}")
    return output_file

# -------------------------------
# Auto download from list.txt
# -------------------------------
def auto_download():
    
    # อ่าน URL แยกบรรทัด
    with open('list.txt','r') as file:
        urls = []

        with open('list.txt', 'r') as file:  # เปิดไฟล์ list.txt ในโหมดอ่าน
            for line in file:  # อ่านทีละบรรทัด
                line = line.strip()  # ลบช่องว่างหัวท้าย เช่น \n หรือ space
                if line != "":  # ตรวจสอบว่าบรรทัดไม่ว่าง
                    urls.append(line)  # เพิ่ม URL ลงใน list


    for url in urls:
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        output_file = f"Video/downloaded_video_{timestamp}.mp4"
        print(f"\n[+] Downloading URL: {url}")
        try:
            download_m3u8(url, output_file)
        except Exception as e:
            print("[ERROR]", e)

# -------------------------------
# Main menu
# -------------------------------
def main():
    os.makedirs("Video", exist_ok=True)
    print("==== M3U8 VIDEO DOWNLOADER ====")
    while True:
        print("[1] Manual Download")
        print("[2] Auto Download")
        try:
            select = int(input("SELECT : ").strip())
        except ValueError:
            print("[ERROR] Please enter a number (1 or 2).")
            continue  # ถามอีกครั้ง

        if select == 1:
            url = input("Enter M3U8 URL: ").strip()
            timestamp = datetime.now().strftime("%y%m%d%H%M%S")
            output_file = f"Video/downloaded_video_{timestamp}.mp4"
            try:
                download_m3u8(url, output_file)
            except Exception as e:
                print("[ERROR]", e)
            break
        elif select == 2:
            auto_download()
            break
        else:
            print("[ERROR] Invalid selection. Enter 1 or 2.")

    print("\n")
    print("*" * 50)
    for result in success:
        print(f"Successfully : {result}")

if __name__ == '__main__':
    main()
