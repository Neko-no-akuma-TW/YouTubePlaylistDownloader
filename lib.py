import os
import re
import json
import shutil
import sys
import subprocess
import yt_dlp
import concurrent
import glob
import time


def update_yt_dlp():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], stderr=subprocess.DEVNULL)
        print("yt-dlp 已成功更新到最新版本。")
    except subprocess.CalledProcessError as e:
        print(f"更新 yt-dlp 時發生錯誤: {e}")
        print("請檢查您的網路連線或權限設定，然後重新執行程式。")


def download_with_error_handling(video_url, ydl_opts, retry_count=3):
    for i in range(retry_count):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])
                return  # 下載成功，跳出迴圈
            except yt_dlp.utils.DownloadError as e:
                if "signature" in str(e).lower() or "nsig" in str(e).lower():
                    print(f"下載時遇到簽名相關錯誤: {e}")
                    print(f"嘗試更新 yt-dlp... (嘗試次數: {i+1}/{retry_count})")
                    update_yt_dlp()
                else:
                    print(f"下載時發生錯誤: {e}")
        if i < retry_count - 1:
            print("等待 5 秒後重新嘗試下載...")
            time.sleep(5)
    print(f"下載 {video_url} 失敗，已達到最大重試次數。")


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def set_thumbnail(video_path, thumbnail_path):
    temp_file = f'{video_path}.temp.mp4'
    jpg_thumbnail = f'{thumbnail_path}.jpg'

    try:
        if not thumbnail_path.lower().endswith(".jpg"):
            # 轉換 webp 到 jpg
            subprocess.run(['ffmpeg', '-i', thumbnail_path, jpg_thumbnail], check=True, stderr=subprocess.DEVNULL)
        else:
            jpg_thumbnail = thumbnail_path  # 如果縮圖已經是 JPG，則直接使用

        # 嵌入 jpg 縮圖
        subprocess.run(['ffmpeg', '-i', video_path, '-i', jpg_thumbnail,
                        '-map', '0', '-map', '1', '-c', 'copy',
                        '-disposition:v:1', 'attached_pic', '-metadata:s:v:1', 'title="Thumbnail"',
                        temp_file],
                       check=True, stderr=subprocess.DEVNULL)

        # 驗證縮圖是否成功嵌入
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:1',
                                 '-count_packets', '-show_entries', 'stream=nb_read_packets',
                                 '-of', 'csv=p=0', temp_file],
                                capture_output=True, text=True, stderr=subprocess.DEVNULL)

        if int(result.stdout.strip()) > 0:
            shutil.move(temp_file, video_path)
            print(f"成功設置縮圖: {video_path}")
        else:
            print(f"縮圖嵌入失敗: {video_path}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    except subprocess.CalledProcessError as e:
        print(f"設置縮圖失敗: {video_path}. 錯誤: {str(e)}")
    finally:
        # 清理臨時文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(jpg_thumbnail) and jpg_thumbnail != thumbnail_path:
            os.remove(jpg_thumbnail)



def embed_chapters(video_path, chapters):
    if not chapters:
        print(f"沒有章節信息可嵌入: {video_path}")
        return

    temp_file = f'{video_path}.temp.mp4'
    metadata_file = f"{video_path}.metadata.json"
    try:
        metadata = {
            "chapters": [
                {
                    "title": chapter['title'],
                    "start_time": chapter['start_time'],
                    "end_time": chapter['end_time']
                } for chapter in chapters
            ]
        }
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False)

        subprocess.run(['ffmpeg', '-i', video_path, '-i', metadata_file,
                        '-map_metadata', '1', '-codec', 'copy', temp_file],
                       check=True, stderr=subprocess.DEVNULL)
        os.replace(temp_file, video_path)
        print(f"成功嵌入章節: {video_path}")
    except Exception as e:
        print(f"嵌入章節失敗 {video_path}: {str(e)}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(metadata_file):
            os.remove(metadata_file)


def download_video(video_url, output_path, video_number, use_cookies=False):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_path, f'{video_number:03d}-%(title)s.%(ext)s'),
        'writesubtitles': True,
        'subtitleslangs': ['zh.TW', 'zh.CN', 'en', 'ja'],
        'subtitlesformat': 'vtt,srt',
        'writethumbnail': True,
        'skip_download': False,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        }],
    }
    if use_cookies:
        ydl_opts['cookiefile'] = 'cookies.txt'


    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_title = sanitize_filename(info['title'])
            base_filename = f"{video_number:03d}-{video_title}"
            video_path = os.path.join(output_path, f"{base_filename}.mp4")

            # 處理字幕文件
            for lang in ['zh.TW', 'zh.CN', 'en', 'ja']:
                vtt_subtitle = os.path.join(output_path, f"{base_filename}.{lang}.vtt")
                srt_subtitle = os.path.join(output_path, f"{base_filename}.{lang}.srt")
                if os.path.exists(vtt_subtitle):
                    print(f"已下載 VTT 字幕: {vtt_subtitle}")
                    if os.path.exists(srt_subtitle):
                        print(f"發現 SRT 字幕: {srt_subtitle}，將保留 VTT 字幕並刪除 SRT 字幕。")
                        os.remove(srt_subtitle) # 預設刪除 SRT
                else:
                    print(f"未找到 {lang} 的 VTT 字幕")
                    if os.path.exists(srt_subtitle):
                        print(f"已下載 SRT 字幕: {srt_subtitle}")
                    else:
                        print(f"未找到 {lang} 的 SRT 字幕")

            # 設置縮圖
            thumbnail_path = os.path.join(output_path, f"{base_filename}.webp")
            if os.path.exists(thumbnail_path):
                set_thumbnail(video_path, thumbnail_path)

            # 嵌入章節
            if 'chapters' in info:
                embed_chapters(video_path, info['chapters'])
            else:
                print(f"視頻沒有章節信息: {base_filename}")

            print(f"成功下載: {base_filename}")
    except Exception as e:
        print(f"下載失敗 {video_url}: {str(e)}")
        download_with_error_handling(video_url, ydl_opts)


def download_playlist(playlist_url, output_path, use_cookies=False, max_workers=5):
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    with yt_dlp.YoutubeDL({'extract_flat': True, 'quiet': True}) as ydl:
        playlist_dict = ydl.extract_info(playlist_url, download=False)
        if 'entries' not in playlist_dict:
            print('無法找到播放清單')
            return

        video_urls = [(i + 1, entry['url']) for i, entry in enumerate(playlist_dict['entries'])]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_video, url, output_path, num, use_cookies) for num, url in video_urls]
        concurrent.futures.wait(futures)


def cleanup_temp_files(output_path):
    for file_path in glob.glob(os.path.join(output_path, "*.temp.mp4")) + glob.glob(os.path.join(output_path, "*.webp")) + glob.glob(os.path.join(output_path, "*.jpg")):
        try:
            os.remove(file_path)
            print(f"已刪除臨時文件: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"刪除臨時文件失敗 {os.path.basename(file_path)}: {str(e)}")


def download_single_video(video_url, output_path, use_cookies=False):
    video_number = 1  # 單個視頻編號設為1
    download_video(video_url, output_path, video_number, use_cookies)
