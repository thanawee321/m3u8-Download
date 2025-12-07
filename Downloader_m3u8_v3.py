from http.client import TOO_EARLY
import os 
import shutil
import requests
import webbrowser
import sys
import subprocess
import zipfile
import platform
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse,urljoin
from Crypto.Cipher import AES
from tqdm import tqdm   
from colorama import Fore, Style, init
from http.client import TOO_EARLY

init(autoreset=True)
ffmpeg_path = None
class banner:

    @staticmethod
    def logo():
        
        logo_lines = [

        " ██████╗    █████╗   ██████╗  ██╗   ██╗ ██╗  ██╗  ██████╗   ██████╗  ██╗  ██╗",
        " ██╔══██╗  ██╔══██╗  ██╔══██╗ ╚██╗ ██╔╝ ██║  ██║ ██╔═══██╗ ██╔═══██╗ ██║ ██╔╝",
        " ██████╔╝  ███████║  ██████╔╝  ╚████╔╝  ███████║ ██║   ██║ ██║   ╚═╝ █████═╝ ",
        " ██╔══██╗  ██╔══██║  ██╔══██╗   ╚██╔╝   ██╔══██║ ██║ █ ██║ ██║       ██╔ ██╗ ",
        " ██████╔╝  ██║  ██║  ██████╔╝    ██║    ██║  ██║ ██║ ████║ ██║   ██╗ ██╔══██╗",
        " ╚═════╝   ╚═╝  ╚═╝  ╚═════╝     ╚═╝    ╚═╝  ╚═╝  ╚══╝╚══╝ ╚██████╔╝ ╚═╝  ╚═╝",
        "                                                   (Tool m3u8 Downloads_V3.1)"
        ]

        return "\n".join([Fore.GREEN + line + Style.RESET_ALL for line in logo_lines]) + "\n"
    

    @staticmethod
    def infomation():
        width = 60

        version = "3.1"
        dev_by = "BabyH@ck"
        facebook = "https://www.facebook.com/thanawee321"
        youtube = "https://www.youtube.com/@BabyHackSenior" 

        results = []
        edge = "+" + Fore.WHITE

        results.append(edge * width)
        results.append(edge + " " * (width - 2) + edge)

        title_text = f"\tTool m3u8 URL Downloader".ljust(width - 8)
        v_text = f" Version       : {version}".ljust(width - 2)
        dev_text = f" DevBy         : {dev_by}".ljust(width - 2)
        fb_text = f" Facebook      : {facebook}".ljust(width - 2)
        yt_text = f" Organization  : {youtube}".ljust(width - 2)

        results.append(edge + title_text + edge)
        results.append(edge + v_text + edge)
        results.append(edge + dev_text + edge)
        results.append(edge + fb_text + edge)
        results.append(edge + yt_text + edge)
        results.append(edge + " " * (width - 2) + edge)
        results.append(edge + " " * (width - 2) + edge)

        results.append(edge * width + Fore.RESET)

        return banner.logo() + "\n" + "\n".join(results) + "\n"

class env_check:
    def __init__(self):
        self.folders = ["Segments","Videos"]


    def env_create(self):
        try:
            for folder in self.folders:
                if os.path.exists(folder):
                    pass
                else:
                    os.makedirs(folder)
                    print(f"{Fore.GREEN}[+] Created folder {Fore.RESET}'{folder}'")

            return True
                
        except Exception as e:
            print(f"{Fore.RED}[-] Failed to create directories : {Fore.RESET}{e}")
            return False
            
class check_ffmpeg:

    def __init__(self):
        self.ffmpeg_path = None
        self.os_type = platform.system()
        
        
    def download_file_with_procress(self, url, dest_zip_path, chunk_size=8192):
        dest_zip_path = Path(dest_zip_path)
        try:
            use_tqdm = True
        except Exception:
            use_tqdm = False

        with requests.get(url, stream=True, timeout=30) as req:
            req.raise_for_status()
            total = int(req.headers.get("content-length") or 0)
            start = time.time()
            downloaded = 0
        
            with open(dest_zip_path, "wb") as file:
                if use_tqdm:
                    total_for_tqdm = total if total > 0 else None
                    with tqdm(total=total_for_tqdm, unit='B', desc="Downloading...", unit_scale=True, unit_divisor=1024) as prograssbar:
                        for chunk in req.iter_content(chunk_size=chunk_size):
                            if chunk:
                                file.write(chunk)
                                prograssbar.update(len(chunk))
                else:
                    if total == 0:
                        for chunk in req.iter_content(chunk_size=chunk_size):
                            if chunk:
                                file.write(chunk)
                                sys.stdout.write(".")
                                sys.stdout.flush()
                        sys.stdout.write('\n')
                    else:
                        bar_len = 30
                        for chunk in req.iter_content(chunk_size=chunk_size):
                            if chunk:
                                file.write(chunk)
                                downloaded += len(chunk)
                                percent = downloaded / total
                                filled = int(bar_len * percent)
                                bar = "#" * filled + "-" * (bar_len - filled)
                                elapsed = time.time() - start
                                speed = downloaded / 1024 / elapsed if elapsed > 0 else 0
                                sys.stdout.write(f"\r[{bar}] {percent:3.0%} {downloaded/1024/1024:0.2f}Mb {total/1024/1024:0.2f}Mb {speed:0.1f}KB/s")
                                sys.stdout.flush()
                        sys.stdout.write('\n')

        return use_tqdm
    

    def ffmpeg_installed(self):

        dots = [".  ", ".. ", "...","....","....."]
        for i in range(len(dots)):
            sys.stdout.write(f"\r{Fore.YELLOW}[*] Checking ffmpeg installation {dots[i]}{Fore.RESET}")
            sys.stdout.flush()
            time.sleep(0.3)


        
        if self.os_type == "Windows":
            install_dir = Path(os.getenv("LOCALAPPDATA")) / "ffmpeg"
            if install_dir.exists():
                exe_candidates = list(install_dir.glob("ffmpeg-*-essentials_build/bin/ffmpeg.exe"))
                if exe_candidates:
                    self.ffmpeg_path = exe_candidates[0]
                    try:
                        result = subprocess.run(
                            [str(self.ffmpeg_path), "-version"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout = 5
                        )
                        if result.returncode == 0:
                            print(f"\n{Fore.GREEN}[+] ffmpeg is already installed at : {Fore.RESET} {self.ffmpeg_path}")
                            return str(self.ffmpeg_path)
                    except:
                        pass

            print(f"{Fore.YELLOW}\n[!] ffmpeg not found. Downloading and installing{Fore.RESET}")
            print(f"{Fore.CYAN}[!] Operating System {Fore.RESET}[Windows]{Fore.CYAN}!!{Fore.RESET}")
            install_dir.mkdir(exist_ok=True) 
            ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"    
            zip_path = install_dir / "ffmpeg.zip"
            print(f"{Fore.CYAN}[*] Downloading ffmpeg for Windows...{Fore.RESET}")
            try:
                self.download_file_with_procress(ffmpeg_url, zip_path)
                # Extract after successful download
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(install_dir)
                zip_path.unlink()

                exe_candidates = list(install_dir.glob("ffmpeg-*-essentials_build/bin/ffmpeg.exe"))
                if not exe_candidates:
                    print(f"{Fore.RED}[-] ffmpeg.exe not found after extraction!{Fore.RESET}")
                    return None

                ffmpeg_path = exe_candidates[0]
                print(f"{Fore.GREEN}[+] ffmpeg installed at: {Fore.RESET}{ffmpeg_path}")
                return str(ffmpeg_path)
            except Exception as e:
                print(f"{Fore.RED}[-] Failed to download ffmpeg: {e}{Fore.RESET}")
                return None
                    
        elif self.os_type == "Linux" or self.os_type == "Darwin":
            if shutil.which("ffmpeg"):
                try:
                    subprocess.run(
                        ["ffmpeg", "-version"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5
                    )
                    print(f"{Fore.GREEN}[+] ffmpeg is already installed via Homebrew.{Fore.RESET}")
                    return shutil.which("ffmpeg")
                except:
                    pass

            else:

                print(f"{Fore.BLUE}[*] Installing ffmpeg via Homebrew...{Fore.RESET}")
                print(f"{Fore.CYAN}[!] Operating System {Fore.RESET}[macOS]{Fore.CYAN}!!{Fore.RESET}")

                if shutil.which("brew") is None:
                    print(f"{Fore.BLUE}[*] No Homebrew found. Installing Homebrew...{Fore.RESET}")
                    os.system('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')

                os.system("brew install ffmpeg")

                if shutil.which("ffmpeg"):
                    print(f"{Fore.GREEN}[+] ffmpeg installed successfully via Homebrew.{Fore.RESET}")
                    return shutil.which("ffmpeg")
                
                print(f"{Fore.RED}[-] ffmpeg failed to install on macOS.{Fore.RESET}")
                return False
            
        else:
            print(f"{Fore.RED}[-] Unsupported OS: {Fore.RESET}{self.os_type}")
            return None

class m3u8:
    def __init__(self,url_m3u8,output_file,):
        self.ffmpeg_path = ffmpeg_path
        self.url_m3u8 = url_m3u8
        self.output_file = output_file
        self.max_retries = 10
        self.success_downloads = []
        self.failed_downloads = []

    def parse_m3u8(self,session):
        response = session.get(self.url_m3u8)
        response.raise_for_status()
        content = response.text

        if "#EXT-X-STREAM-INF" in content:
            lines = [line.strip() for line in content.split("\n") if line and not line.startswith("#")]
            url = urljoin(self.url_m3u8,lines[-1])

            response = session.get(url,timeout=10)
            response.raise_for_status()
            content = response.text
            self.url_m3u8 = url #NEW UPDATE อัปเดต base URL ไปยัง Variant Playlist เพื่อใช้สำหรับ urljoin ใน Segment


        key = None
        iv = None
        ts_file = []
        start_sequence = 0

        for line in content.split("\n"):
            line = line.strip()

            #ดึง Encryption Key และ Explicit IV
            if line.startswith("#EXT-X-KEY"):
                
                if 'URI="' in line:
                    uri_part = line.split('URI="')[1].split('"')[0]
                    key_url = urljoin(self.url_m3u8, uri_part)
                    key_response = session.get(key_url,timeout=10).content
                    key = key_response
                    # กรณีมี Explicit IV กำหนด
                    if "IV=" in line:
                        iv_hex = line.split("IV=")[1].split(",")[0].replace("0x", "")
                        iv = bytes.fromhex(iv_hex)
                    else:
                        iv = key_response[:16] or iv == None

            elif line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
                try:
                    # ดึงค่า N จาก #EXT-X-MEDIA-SEQUENCE:N
                    start_sequence = int(line.split(":")[1].split(",")[0].strip())
                except ValueError:
                    start_sequence = 0

                    #ดึงรายการ Segment
            elif line and not line.startswith("#"):
                ts_file.append(line)

        return ts_file, self.url_m3u8, key, iv,start_sequence
    

    
    def download_segment(self,session,ts_url,seg_path,index,total_ts,key=None,iv=None):

        for attempt in range(1,self.max_retries +1):
            try:
                response = session.get(ts_url,stream=True,timeout=10)
                if response.status_code != 200:
                    raise Exception(f"Failed to download segment: HTTP {response.status_code}") 

                data = response.content

                if key:
                    cihper = AES.new(key, AES.MODE_CBC, iv)
                    data = cihper.decrypt(data)   

                with open(seg_path,"wb") as file:
                    file.write(data)

                if os.path.getsize(seg_path) == 0:
                    raise Exception("Downloaded segment is empty.")
                
                sys.stdout.write("\r" + " " * 100 + "\r")
                sys.stdout.write(f"{Fore.GREEN}[{index}/{total_ts}] Downloading : {Fore.RESET}{os.path.basename(ts_url)}")
                sys.stdout.flush()
                
                return True
                
            except Exception as e:
                
                if attempt < self.max_retries:
                    # เคลียร์บรรทัดและแสดงข้อความ retry ในบรรทัดเดียวกัน
                    sys.stdout.write("\r" + " " * 100 + "\r")
                    sys.stdout.write(f"{Fore.YELLOW}[*] Retry {attempt}/{self.max_retries} for {os.path.basename(ts_url)}: {e}{Fore.RESET}")
                    sys.stdout.flush()
                    time.sleep(1)
                else:
                    self.failed_downloads.append(ts_url)
                    raise Exception(f"Failed to download after retries: {e}")
                
        return self.failed_downloads



    def download_m3u8(self,count_url=None,total_url=None):
        session = requests.Session()
        parsed = urlparse(self.url_m3u8)
        
        base = f"{parsed.scheme}://{parsed.netloc}{os.path.dirname(parsed.path)}/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; X64)",
            "Referer": base,
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Cookie": ""
        }
        session.headers.update(headers)

        obj_m3u8_for_parse = m3u8(self.url_m3u8,self.output_file) 
        ts_files , base_url ,key , iv , start_sequence = obj_m3u8_for_parse.parse_m3u8(session)
        if not ts_files:
            print(f"{Fore.RED}[-] No segments found in the m3u8 playlist.{Fore.RESET}")
            return False

        check_env = env_check().env_create()
        if not check_env:
            print(f"{Fore.RED}[-] Environment setup failed.{Fore.RESET}Please Wait...")
            pass

        segment_files = []
        print(f"{Fore.CYAN}[+] Total Downloading...{Fore.RESET}[{count_url}/{total_url}]")
        print(f"{Fore.CYAN}[+] Target URL : {Fore.RESET}{self.url_m3u8}")
        print(f"{Fore.CYAN}[+] Segment Downloading {Fore.RESET}{len(ts_files)} {Fore.CYAN}segments...{Fore.RESET}")

        for i, ts_name in enumerate(ts_files):
            current_iv = iv
            if key is not None and current_iv is None:
                sequence_number = start_sequence + i # Segment index (0, 1, 2, ...)
                #sequence_bytes = sequence_number.to_bytes(8, byteorder='big')
                #current_iv = b'\x00' * 8 + sequence_bytes //ค่าเดิม 8-byte padded
                current_iv = sequence_number.to_bytes(16, byteorder='big') #//ค่ามาตารฐาน 16-byte padded

            seg_path = f"Segments/segment_{i}.ts"
            ts_url = urljoin(base_url, ts_name)
            obj_m3u8_for_segment = m3u8(self.url_m3u8,self.output_file)
            obj_m3u8_for_segment.download_segment(session,ts_url,seg_path,i+1,len(ts_files),key,current_iv)

            segment_files.append(seg_path)

        list_file = "Segment_list.txt"
        with open(list_file,"w",encoding='utf-8') as file:
            for segment in segment_files:
                file.write(f"file '{segment}'\n")
        print(f"\n{Fore.BLUE}[*] Merging video using ffmpeg...{Fore.RESET}")
        
        for seg in segment_files:
            if not os.path.exists(seg) or os.path.getsize(seg) == 0:
                print(f"{Fore.RED}[!] Missing or empty segment detected: {seg}{Fore.RESET}")
                print(f"{Fore.YELLOW}[!] Merge cancelled to prevent corrupted output.{Fore.RESET}")
                return False

        # Small delay to ensure OS flushes file buffers
        time.sleep(1)

        result = subprocess.run([
            self.ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            self.output_file
        ])

        if result.returncode == 0:
            print(f"{Fore.GREEN}[+] SUCCESS! Saved : {Fore.RESET}{self.output_file}")
            shutil.rmtree("Segments", ignore_errors=True)
            Path(list_file).unlink(missing_ok=True)
        else:
            print(f"{Fore.RED}[-] FFmpeg merge failed. Keeping Segments folder for debugging.{Fore.RESET}")
            return False

        # =============== END FIXED SECTION ===============

        self.success_downloads.append(f"{Fore.GREEN}[URL : {Fore.RESET}{self.url_m3u8}{Fore.GREEN}] → [File : {Fore.RESET}{self.output_file}{Fore.GREEN}]")

        return self.success_downloads
    
class menu_downloader:


    def manual_download(self):
        try:
            timestamp = datetime.now().strftime("%y%m%d%H%M%S")
            output_file = f"Videos/download_video_{timestamp}.mp4"
            while True:
                url = input("Enter m3u8 URL : ").strip()
                if not url:
                    print(f"{Fore.YELLOW}[!] URL cannot be empty. Please try again.{Fore.RESET}")
                    continue
                parsed = urlparse(url)
                if parsed.scheme and parsed.netloc and parsed.scheme.lower() in ("http","https"):
                    if parsed.path.endswith('m3u8'):
                        print(f"{Fore.GREEN}[+] Vaild m3u8 URL detected.{Fore.RESET}")

                        download_m3u8 = m3u8(url.strip(), output_file)
                        result_downloads = download_m3u8.download_m3u8(count_url=1)
                        if result_downloads:
                            print(f"{Fore.GREEN}[+] Download completed successfully.{Fore.RESET}")
                            break
                    else:
                        print(f"{Fore.YELLOW}[!] URL doesn't look like an m3u8 playlist.{Fore.RESET}")
                        choice = input(f"[*] Continue with this URL anyway? (y/N) : ").strip().lower()
                        if choice == 'y':
                            download_m3u8 = m3u8(url.strip(),output_file)
                            result_downloads = download_m3u8.download_m3u8(count_url=1, total_url=1)
                        else:
                            continue

                else:
                    print(f"{Fore.RED}[-] Invalid URL. Please enter a full http/https URL.{Fore.RESET}")
                    continue

        except Exception as e:
            print(f"{Fore.RED}[-] Error processing URL: {e}{Fore.RESET}")
            return None


    def auto_download(self):
        
        success_results = []
        failed_results = []
        count_url = 0
        
        with open('m3u8_urls.txt', 'r',encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        total_url = len(lines)

        for url in lines:
            count_url+=1
            try:
                timestamp = datetime.now().strftime("%y%m%d%H%M%S")
                output_file = f"Videos/download_video_{timestamp}.mp4"
                download_m3u8 = m3u8(url.strip(), output_file)
                download_m3u8.download_m3u8(count_url,total_url)

                if download_m3u8.success_downloads:
                    success_results.extend(download_m3u8.success_downloads)
                if download_m3u8.failed_downloads:
                    failed_results.extend(download_m3u8.failed_downloads)

            except Exception as e:
                print(f"{Fore.RED}[-] Error : {e}{Fore.RESET}")
                failed_results.append(f"{Fore.RED}[URL : {Fore.RESET}{url}{Fore.RED}] → [Error : {e}]{Fore.RESET}")

        print("\n" + "="*20 + " Download Summary " + "="*20)
        print(f"\n{Fore.GREEN}Successful Downloads : [{Fore.RESET}{len(success_results)}/{len(lines)}{Fore.CYAN}]{Fore.RESET}{Fore.RESET}")
        for result in success_results:

            print(result)
        
        
        if failed_results:
            print(f"\n{Fore.RED}Failed Downloads:{Fore.RESET}")
            for result in failed_results:
                print(result)

        
def main():
    global ffmpeg_path

    # ====== CHECK FFMPEG INSTALL ======
    obj_check_ffmpeg = check_ffmpeg()
    ffmpeginstall = obj_check_ffmpeg.ffmpeg_installed()
    ffmpeg_path = ffmpeginstall

    if not ffmpeg_path:
        print(f"{Fore.RED}[-] ffmpeg is required to run this tool. Exiting...{Fore.RESET}")
        sys.exit(1)

    # ====== CREATE ENV FOLDERS ======
    obj_env_check = env_check()
    obj_env_check.env_create()

    # ====== PRINT BANNER ======
    print("\n" + banner().infomation())

    # ====== MAIN MENU LOOP ======
    while True:
        print("\n=== Tool Download m3u8 URL ===")
        print("[1] Manual Download")
        print("[2] Auto Downloads")
        print("[0] Exit")

        try:
            sec = int(input("Select : "))

            # ----------------------
            # MANUAL DOWNLOAD
            # ----------------------
            if sec == 1:

               menu_downloader().manual_download()


            # ----------------------
            # AUTO DOWNLOAD (ไฟล์ .txt)
            # ----------------------
            elif sec == 2:
                menu_downloader().auto_download()

            # ----------------------
            # EXIT
            # ----------------------
            elif sec == 0:
                print(f"{Fore.RESET}[*] Exit...")
                webbrowser.open("https://www.youtube.com/watch?v=P9sQZLtsfp8")
                break

            else:
                print(f"{Fore.YELLOW}[!] Please enter 1, 2, or 0.{Fore.RESET}")

        except ValueError:
            print(f"{Fore.YELLOW}[!] Invalid input. Please enter a number.{Fore.RESET}")


if __name__ == "__main__":
    main()