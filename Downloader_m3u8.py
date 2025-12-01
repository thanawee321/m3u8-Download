import os
import shutil
import time
import webbrowser
import requests
import sys
import subprocess
import zipfile
import urllib.request
import platform
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
from Crypto.Cipher import AES
from colorama import Fore, Style

MAX_RETIRES = 30
TIMEOUT = 5

success_downloads = []
fail_downloads = []
total_url = 0


# CHECK FFMPEG (แก้เฉพาะส่วนที่จำเป็น)
def check_ffmpeg():

    # 1) ลองเรียก ffmpeg จาก PATH
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if result.returncode == 0:
            print(f"{Fore.GREEN}[+] ffmpeg is already installed in system.{Fore.RESET}")
            return shutil.which("ffmpeg")
    except FileNotFoundError:
        pass

    print(f"{Fore.YELLOW}[!] ffmpeg not found. Installing...{Fore.RESET}")
    os_type = platform.system()

    # ------------------ WINDOWS ------------------
    if os_type == "Windows":

        install_dir = Path(os.getenv("LOCALAPPDATA")) / "ffmpeg"
        install_dir.mkdir(exist_ok=True)

        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        zip_path = install_dir / "ffmpeg.zip"

        print(f"{Fore.BLUE}[*] Downloading ffmpeg for Windows...{Fore.RESET}")
        urllib.request.urlretrieve(ffmpeg_url, zip_path)

        # Extract
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(install_dir)
        zip_path.unlink()

        exe_candidates = list(install_dir.glob("ffmpeg-*-essentials_build/bin/ffmpeg.exe"))
        if not exe_candidates:
            print(f"{Fore.RED}[-] ffmpeg.exe not found after extraction!{Fore.RESET}")
            return None

        ffmpeg_path = exe_candidates[0]

        print(f"{Fore.GREEN}[+] ffmpeg installed at: {ffmpeg_path}{Fore.RESET}")
        print(f"{Fore.GREEN}[+] (No PATH modification needed for Nuitka EXE){Fore.RESET}")

        return str(ffmpeg_path)

    # ------------------ macOS ------------------
    elif os_type == "Darwin":

        print(f"{Fore.BLUE}[*] Installing ffmpeg via Homebrew...{Fore.RESET}")

        if shutil.which("brew") is None:
            print(f"{Fore.BLUE}[*] No Homebrew found. Installing Homebrew...{Fore.RESET}")
            os.system('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')

        os.system("brew install ffmpeg")

        if shutil.which("ffmpeg"):
            print(f"{Fore.GREEN}[+] ffmpeg installed successfully via Homebrew.{Fore.RESET}")
            return shutil.which("ffmpeg")

        print(f"{Fore.RED}[-] ffmpeg failed to install on macOS.{Fore.RESET}")
        return None

    else:
        print(f"{Fore.RED}[-] Unsupported OS: {os_type}{Fore.RESET}")
        return None


def parse_m3u8(session, url):
    res = session.get(url, timeout=TIMEOUT)
    res.raise_for_status()
    text = res.text

    if "#EXT-X-STREAM-INF" in text:
        lines = [line.strip() for line in text.split("\n") if line and not line.startswith("#")]
        url = urljoin(url, lines[-1])
        res = session.get(url, timeout=TIMEOUT)
        res.raise_for_status()
        text = res.text

    key = None
    iv = None
    ts_files = []

    for line in text.split("\n"):
        line = line.strip()

        if line.startswith("#EXT-X-KEY"):

            if 'URI="' in line:
                uri_part = line.split('URI="')[1].split('"')[0]
                key_url = urljoin(url, uri_part)
                key_data = session.get(key_url, timeout=TIMEOUT).content
                key = key_data

                if "IV=" in line:
                    iv_hex = line.split("IV=")[1].split(",")[0].replace("0x", "")
                    iv = bytes.fromhex(iv_hex)
                else:
                    iv = key_data[:16]

        elif line and not line.startswith("#"):
            ts_files.append(line)

    return ts_files, url, key, iv


def download_segment(session, ts_url, seg_path, index, total_ts, decrypt_key=None, iv=None):
    key = decrypt_key

    for attempt in range(1, MAX_RETIRES + 1):
        try:
            res = session.get(ts_url, stream=True, timeout=TIMEOUT)
            if res.status_code != 200:
                raise Exception(f"Status code not 200 {res.status_code}")

            data = res.content

            if key:
                cipher = AES.new(key, AES.MODE_CBC, iv)
                data = cipher.decrypt(data)

            with open(seg_path, "wb") as f:
                f.write(data)

            if os.path.getsize(seg_path) == 0:
                raise Exception("empty file")

            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.write(f"{Fore.GREEN}[{index}/{total_ts}] Downloading : {ts_url}{Fore.RESET}")
            sys.stdout.flush()

            return True

        except Exception as e:
            sys.stdout.write("\n")
            if attempt < MAX_RETIRES:
                print(f"{Fore.YELLOW}[*] Retry {attempt}/{MAX_RETIRES} for {ts_url}: {e}{Fore.RESET}")
                time.sleep(1)
            else:
                fail_downloads.append(ts_url)
                raise Exception(f"Failed to download after retries: {e}")


#   ⭐ แก้ไขเฉพาะส่วน ffmpeg_path ⭐
def download_m3u8(url, output_file, count_url=None, total_url=None, ffmpeg_path=None):

    session = requests.Session()

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}{os.path.dirname(parsed.path)}/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; X64)",
        "Referer": base,
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Cookie": ""
    }
    session.headers.update(headers)

    ts_files, base_url, key, iv = parse_m3u8(session, url)
    if not ts_files:
        raise Exception("NO TS found")

    os.makedirs("Segments", exist_ok=True)
    seg_paths = []

    print(f"{Fore.BLUE}[+] Total Downloading...{Fore.RESET}[{count_url}/{total_url}]")
    print(f"{Fore.BLUE}[+] Downloading {Fore.RESET}{len(ts_files)} {Fore.BLUE}segments...{Fore.RESET}")

    for i, ts_name in enumerate(ts_files):
        ts_url = urljoin(base_url, ts_name)
        seg_path = f"Segments/seg_{i}.ts"
        download_segment(session, ts_url, seg_path, i + 1, len(ts_files), key, iv)
        seg_paths.append(seg_path)

    list_file = "segment_list.txt"
    with open(list_file, "w") as f:
        for seg in seg_paths:
            f.write(f"file '{seg}'\n")

    print(f"\n{Fore.BLUE}[*] Merging video using ffmpeg...{Fore.RESET}")

    
    subprocess.run([
        ffmpeg_path,     # ← ใช้ path ตรงของ ffmpeg
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_file
    ], check=True)

    shutil.rmtree("Segments", ignore_errors=True)
    Path(list_file).unlink(missing_ok=True)

    print(f"{Fore.GREEN}[+] SUCCESS! Saved: {output_file}{Fore.RESET}")
    success_downloads.append(f"[URL : {url}] → [File : {output_file}]")

    return output_file



def manual_download(ffmpeg_path):
    url = str(input("Enter m3u8 URL : "))
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    output_file = f"Video/download_video_{timestamp}.mp4"

    try:
        download_m3u8(url, output_file, ffmpeg_path=ffmpeg_path)
    except Exception as e:
        print(f"{Fore.RED}[-] Error : {e}{Fore.RESET}")



def auto_download(ffmpeg_path):
    global total_url

    only_num_url = 0
    with open("list.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    total_url = len(lines)

    for url in lines:
        only_num_url += 1
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        output_file = f"Video/download_video_{timestamp}.mp4"

        try:
            download_m3u8(url, output_file, only_num_url, total_url, ffmpeg_path)
        except Exception as e:
            print(f"{Fore.RED}[-] Error : {e}{Fore.RESET}")



def logo():
    logo_lines = [
        " ██████╗    █████╗   ██████╗  ██╗   ██╗ ██╗  ██╗  ██████╗   ██████╗  ██╗  ██╗",
        " ██╔══██╗  ██╔══██╗  ██╔══██╗ ╚██╗ ██╔╝ ██║  ██║ ██╔═══██╗ ██╔═══██╗ ██║ ██╔╝",
        " ██████╔╝  ███████║  ██████╔╝  ╚████╔╝  ███████║ ██║   ██║ ██║   ╚═╝ █████═╝ ",
        " ██╔══██╗  ██╔══██║  ██╔══██╗   ╚██╔╝   ██╔══██║ ██║ █ ██║ ██║       ██╔ ██╗ ",
        " ██████╔╝  ██║  ██║  ██████╔╝    ██║    ██║  ██║ ██║ ████║ ██║   ██╗ ██╔══██╗",
        " ╚═════╝   ╚═╝  ╚═╝  ╚═════╝     ╚═╝    ╚═╝  ╚═╝  ╚══╝╚══╝ ╚██████╔╝ ╚═╝  ╚═╝",
        "                                                   (Tool m3u8 Downloads_V1.4)"
    ]

    return "\n".join([Fore.CYAN + line + Style.RESET_ALL for line in logo_lines]) + "\n"


def infomation():

    width = 60

    version = "1.4"
    dev_by = "BabyH@ck"
    facebook = "https://www.facebook.com/thanawee321"
    youtube = "https://www.youtube.com/@BabyHackSenior"

    result = []
    edge = "=" + Fore.WHITE

    result.append(edge * width)
    result.append(edge + " " * (width - 2) + edge)

    title_text = f"\tTool m3u8 URL Downloader".ljust(width - 8)
    v_text = f" Version       : {version}".ljust(width - 2)
    dev_text = f" DevBy         : {dev_by}".ljust(width - 2)
    fb_text = f" Facebook      : {facebook}".ljust(width - 2)
    yt_text = f" Organization  : {youtube}".ljust(width - 2)

    result.append(edge + title_text + edge)
    result.append(edge + v_text + edge)
    result.append(edge + dev_text + edge)
    result.append(edge + fb_text + edge)
    result.append(edge + yt_text + edge)
    result.append(edge + " " * (width - 2) + edge)
    result.append(edge + " " * (width - 2) + edge)

    result.append(edge * width + Fore.RESET)

    return logo() + "\n" + "\n".join(result) + "\n"


def result():

    print("=" * 100)
    print(f"Total [{len(success_downloads)}/{total_url}]")

    for r in success_downloads:
        print(f"{Fore.CYAN}{r}")

    input(f"{Fore.RESET}[*] Please Enter ...")


def main(ffmpeg_path):

    os.makedirs("Video", exist_ok=True)

    while True:
        print("\n" + infomation())
        print("\n=== Tool Download m3u8 URL ===")
        print("[1] Manual Download")
        print("[2] Auto Downloads")

        try:
            sec = int(input("Select : "))

            if sec == 1:
                manual_download(ffmpeg_path)
                result()

            if sec == 2:
                auto_download(ffmpeg_path)
                result()

            elif sec == 0:
                print(f"{Fore.RESET}[*] Exit...")
                webbrowser.open("https://www.youtube.com/watch?v=P9sQZLtsfp8")
                break

        except ValueError:
            print(f"{Fore.YELLOW}[!] Please enter a number (1,2){Fore.RESET}")


if __name__ == '__main__':
    ffmpeg_path = check_ffmpeg()
    if ffmpeg_path:
        main(ffmpeg_path)
