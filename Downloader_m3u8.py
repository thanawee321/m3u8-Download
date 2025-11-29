import os
import shutil
import time
import webbrowser
import requests
import sys
import subprocess
import zipfile
import urllib.request
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin,urlparse
from Crypto.Cipher import AES
from colorama import Fore,Style



MAX_RETIRES = 30
TIMEOUT = 5
success= []

def parse_m3u8(session,url):
    res = session.get(url,timeout=TIMEOUT)
    res.raise_for_status()
    text = res.text

    if "#EXT-X-STREAM-INF" in text:
        lines = [line.strip() for line in text.split("\n") if line and not line.startswith("#")]
        url = urljoin(url,lines[-1])
        res = session.get(url,timeout=TIMEOUT)
        res.raise_for_status()
        text = res.text

    key = None
    iv = None
    lines = text.split("\n")
    ts_files = []
    for line in lines:
        line = line.strip()
        if line.startswith("#EXT-X-KEY"):
            if 'URI="' in line:
                uri_part = line.split('URI="')[1].split('"')[0]
                key_url = urljoin(url,uri_part)
                key_data = session.get(key_url,timeout=TIMEOUT).content
                key = key_data

                if "IV=" in line:
                    iv_hex = line.split("IV=")[1].split(",")[0]
                    iv_hex = iv_hex.replace("0x","")  # ลบ prefix
                    iv = bytes.fromhex(iv_hex)

                else:
                    iv = key_data[:16]
        elif line and not line.startswith("#"):
            ts_files.append(line)
    return ts_files,url,key,iv


def download_segment(session, ts_url, seg_path, index, total_ts, decrypt_key=None, iv=None):
    key = decrypt_key
    for attempt in range(1, MAX_RETIRES + 1):
        try:
            res = session.get(ts_url, stream=True, timeout=TIMEOUT)
            if res.status_code != 200:
                raise Exception(f"{Fore.YELLOW}Status code not 200 {res.status_code}")

            data = res.content

            if key:
                cipher = AES.new(key, AES.MODE_CBC, iv)
                data = cipher.decrypt(data)

            with open(seg_path, "wb") as file:
                file.write(data)

            if os.path.getsize(seg_path) == 0:
                raise Exception(f"{Fore.RED}[-] Empty file{Fore.RESET}")

            # --- Progress bar (เขียนทับบรรทัดเดิม) ---
            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.write(f"{Fore.GREEN}[{index}/{total_ts}] Downloading : {ts_url}{Fore.RESET}")
            sys.stdout.flush()

            return True

        except Exception as e:

            # --- ขึ้นบรรทัดใหม่ก่อนแสดง error ---
            sys.stdout.write("\n")
            sys.stdout.flush()

            if attempt < MAX_RETIRES:
                print(
                    f"{Fore.YELLOW}[*] Retry {attempt}/{MAX_RETIRES} "
                    f"for {ts_url} due to error: {Fore.RESET}{e}"
                )
                time.sleep(1)
            else:
                raise Exception(
                    f"{Fore.RED}[-] Failed to download {ts_url} after {MAX_RETIRES} attempts. "
                    f"Error: {e}{Fore.RESET}"
                )




def download_m3u8(url,output_file):
    header = None
    session = requests.Session()

    if not header:

        parsed = urlparse(url) # แยก URL เป็นส่วนๆ
        base = f"{parsed.scheme}://{parsed.netloc}{os.path.dirname(parsed.path)}/"
        headers = {
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0;Win64; X64)",
            "Referer" : base,
            "Accept" : "*/*",
            "Connection" : "keep-alive",
            "Cookie": ""
        }

    session.headers.update(headers)
    ts_files,base_url,key,iv = parse_m3u8(session,url)
    if not ts_files:
        raise Exception(f"{Fore.RED}[-] NO TS Segment found!!{Fore.RESET}")
    
    os.makedirs("Segments",exist_ok=True)
    seg_paths = []
    print(f"{Fore.BLUE}[+] Downloading {len(ts_files)} segments sequentially...")
    for i,ts_name in enumerate(ts_files):
        ts_url = urljoin(base_url,ts_name)
        seg_path = f"Segments/seg_{i}.ts"
        download_segment(session,ts_url,seg_path,i + 1,len(ts_files),key,iv)
        seg_paths.append(seg_path)

    list_file = "segment_list.txt"
    with open(list_file,'w') as file:
        for seg in seg_paths:
            file.write(f"file '{seg}'\n")

    print(f"\n{Fore.BLUE}[*] Merging video using ffmpeg...{Fore.RESET}")
    subprocess.run([
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",list_file,
        "-c",
        "copy",
        output_file
    ],check=True)

    shutil.rmtree("Segments",ignore_errors=True)
    if Path(list_file).exists():
        Path(list_file).unlink()
    print(f"{Fore.GREEN}[+] Temporary files cleaned up{Fore.RESET}")
    print(f"{Fore.GREEN}[+] SUCCESS! Video save as : {output_file}")
    success.append(f"[URL : {url}] --> [File : {output_file}]")
    return output_file



def manual_download():
    url = str(input("Enter m3u8 URL : "))
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    output_file = f"Video/download_video_{timestamp}.mp4"
    try:
        download_m3u8(url,output_file)
    except Exception as e:
        print(f"{Fore.RED}[-] Error : {Fore.RESET}{e}")
    return None
def auto_download():

    with open("list.txt",'r') as file:
        urls = []

        with open("list.txt",'r') as file:
            for line in file:
                line = line.strip()
                if line != "":
                    urls.append(line)

    
    for url in urls:
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        output_file = f"Video/download_video_{timestamp}.mp4"
        try:
            download_m3u8(url,output_file)
        except Exception as e:
            print(f"{Fore.RED}[-] Error : {Fore.RESET}{e}")
    return None


def check_ffmpeg():
    try:
        # เช็ค ffmpeg ใน PATH
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"{Fore.GREEN}[+] ffmpeg is already installed.{Fore.RESET}")
        return True
    except Exception:
        print(f"{Fore.BLUE}[*] ffmpeg not found, installing...{Fore.RESET}")

        # สร้างโฟลเดอร์สำหรับ ffmpeg ใน project
        ffmpeg_dir = Path("ffmpeg_bin")
        ffmpeg_dir.mkdir(exist_ok=True)

        # URL สำหรับ ffmpeg Windows static build (64-bit)
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        zip_path = ffmpeg_dir / "ffmpeg.zip"

        # ดาวน์โหลด
        print(f"{Fore.BLUE}[*] Downloading ffmpeg...{Fore.RESET}")
        urllib.request.urlretrieve(ffmpeg_url, zip_path)

        # แตก zip
        print(f"{Fore.BLUE}[*] Extracting ffmpeg...{Fore.RESET}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        zip_path.unlink()  # ลบ zip หลัง extract

        # หา path ของ ffmpeg.exe ที่ extract มา
        ffmpeg_exe = list(ffmpeg_dir.glob("ffmpeg-*-essentials_build/bin/ffmpeg.exe"))
        if not ffmpeg_exe:
            print(f"{Fore.RED}[-] ffmpeg executable not found after extraction!{Fore.RESET}")
            return False

        ffmpeg_path = ffmpeg_exe[0]
        print(f"{Fore.GREEN}[+] ffmpeg installed at {Fore.RESET}{ffmpeg_path}")
        return ffmpeg_path


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
    
    return "\n".join([Fore.CYAN + line + Style.RESET_ALL for line in logo_lines])+"\n"
        
        
def infomation():
    
    width = 60
    
    version = "1.4"
    dev_by = "BabyH@ck"
    facebook = "https://www.facebook.com/thanawee321"
    youtube = "https://www.youtube.com/@BabyHackSenior"
    

    # สร้างกรอบและเก็บในตัวแปร
    result = []
    
    edge = "=" + Fore.WHITE
    
    # ขอบบน
    result.append(edge * width)
    result.append(edge + " " * (width - 2) + edge)  # บรรทัดว่าง
    
    
    # ข้อความชิดซ้าย
    title_text = f"\tTool m3u8 URL Downloader".ljust(width - 8)
    version_text = f" Version       : {version}".ljust(width - 2)
    dev_by_text = f" DevBy         : {dev_by}".ljust(width - 2)
    aboutme = f" Facebook      : {facebook}".ljust(width - 2)
    youtube = f" Organization  : {youtube}".ljust(width - 2)
    
    result.append(edge + title_text + edge)
    result.append(edge + version_text + edge)
    result.append(edge + dev_by_text + edge)
    result.append(edge + aboutme + edge)
    result.append(edge + youtube + edge)
    result.append(edge + " " * (width - 2) + edge)  # บรรทัดว่าง
    result.append(edge + " " * (width - 2) + edge)  # บรรทัดว่าง
    result.append(edge * width + Fore.RESET)  # ขอบล่าง

    # รวมข้อความทั้งหมดเป็นสตริงเดียว
    border_content = "\n".join(result)

    # ผลลัพธ์ที่ประกอบกันเป็น ASCII Art และกรอบ
    return logo() + "\n" + border_content + "\n"


def result():
    print("=" * 100)
    print(f"Total [{len(success)}]")
    for result in success:
        print(f"{Fore.CYAN}{result}")


def main():
    os.makedirs("Video",exist_ok=True)
    while True:
        Fore.RESET
        print("\n")
        print(infomation())
        print("\n=== Tool Download m3u8 URL ===")
        print("[1] Manual Download")
        print("[2] Auto Downloads")

        try:
            sec = int(input("Select : "))
            if sec == 1:
                manual_download()
                result()
            if sec == 2:
                auto_download()
                result()
            elif sec == 0:
                print(f"{Fore.RESET}[*] Exit...")
                #subprocess.run(["powershell", "-Command", "Start-Process https://www.youtube.com/watch?v=P9sQZLtsfp8&list=RDP9sQZLtsfp8&start_radio=1"], check=True)
                webbrowser.open("https://www.youtube.com/watch?v=P9sQZLtsfp8&list=RDP9sQZLtsfp8&start_radio=1")
                break

        except ValueError:
            print(f"{Fore.YELLOW}[!] Please enter a number (1,2){Fore.RESET}")

    


    return None


if __name__ == '__main__':
    ffmpeg_path = check_ffmpeg()
    if ffmpeg_path :
        main()