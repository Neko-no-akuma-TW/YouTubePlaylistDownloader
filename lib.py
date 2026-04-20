import os
import re
import json
import shutil
import sys
import subprocess
import yt_dlp
import concurrent.futures
import glob
import time
import zipfile
from typing import List, Dict, Any, Optional, Callable

# --- Version Check ---
if sys.version_info < (3, 10):
    print("[WARNING] Your Python version is 3.9 or below. yt-dlp has deprecated support for Python 3.9.")
    print("[WARNING] Please upgrade to Python 3.10 or above for optimal compatibility.")
    print("[INFO] Current version: Python {}.{}".format(sys.version_info.major, sys.version_info.minor))

# --- Constants ---
SUPPORTED_SUB_LANGS: List[str] = ['zh.TW', 'zh.CN', 'en', 'ja']
SUB_EXTENSIONS: List[str] = ['.vtt', '.srt']
# Only delete actual temporary files, NOT thumbnails (webp/jpg are valid downloads)
TEMP_FILE_PATTERNS: List[str] = ["*.temp.mp4", "*.tmp.mp4", "*.part", "*.metadata.json", "*.[0-9][0-9][0-9]"]
THUMBNAIL_PATTERNS: List[str] = ["*.webp", "*.jpg"]  # Keep these as they are thumbnails
FILES_PER_ZIP: int = 10

# --- Helper Functions ---

def get_playlist_info(playlist_url: str, use_cookies: bool, use_pot: bool) -> Optional[Dict[str, Any]]:
    """獲取播放清單的資訊，但不下載影片。"""
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'cookiefile': 'cookies.txt' if use_cookies else None,
    }
    if not use_pot:
        ydl_opts['nop_plugins'] = True
    else:
        ydl_opts['quiet'] = False  # Show messages for PotProvider debugging
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(playlist_url, download=False)
    except Exception as e:
        print(f"解析播放清單失敗: {e}")
        if use_pot:
            print(f"[提示] 如果 PotProvider 伺服器未運行，請禁用「使用 PotProvider」選項")
        return None
    
def channel_info(channel_url: str):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            return info
    except yt_dlp.utils.DownloadError as e:
        return None

def get_format_options(format_selection: str) -> Dict[str, Any]:
    if format_selection == "Audio (MP3)":
        return {
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        }
    elif format_selection == "1080p":
        return {'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'merge_output_format': 'mp4'}
    elif format_selection == "720p":
        return {'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'merge_output_format': 'mp4'}
    else: # Best Video
        return {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'merge_output_format': 'mp4'}

class ProgressLogger:
    def __init__(self, progress_hook: Optional[Callable] = None):
        self.progress_hook = progress_hook
    def debug(self, msg, **kwargs): 
        pass
    def warning(self, msg, **kwargs):
        # Filter out non-critical warnings
        if self.progress_hook:
            # Show important warnings, suppress verbose ones
            if "Deprecated Feature" not in msg:  # Filter out Python version warnings (already shown)
                self.progress_hook({'status': 'warning', 'message': msg})
    def error(self, msg, **kwargs):
        if self.progress_hook: self.progress_hook({'status': 'error', 'message': msg})

# --- Core Download Functions ---

def download_video(video_url: str, output_path: str, video_number: int, use_cookies: bool, download_format: str, use_pot: bool, progress_hook: Optional[Callable] = None, write_info_json: bool = True, live_from_start: bool = False) -> Optional[str]:
    format_opts = get_format_options(download_format)
    
    def hook(d):
        if progress_hook: progress_hook(d)

    # Build postprocessors list
    postprocessors = format_opts.get('postprocessors', [])
    if "Audio" not in download_format:
        # Add FFmpeg metadata processor for video files
        postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})

    ydl_opts = {
        'outtmpl': os.path.join(output_path, (f'{video_number:03d}-' if video_number > 0 else '') + '%(title)s.%(ext)s'),
        'writesubtitles': True,
        'subtitleslangs': SUPPORTED_SUB_LANGS,
        'subtitlesformat': 'vtt/srt',
        'writethumbnail': "Audio" not in download_format,
        'writeinfojson': write_info_json,  # Download video info as JSON
        'writeoriginalurl': True,  # Write original URL for reference
        'skip_download': False,
        'cookiefile': 'cookies.txt' if use_cookies else None,
        'postprocessors': postprocessors,
        'progress_hooks': [hook],
        'logger': ProgressLogger(progress_hook),
        'download_archive': os.path.join(output_path, 'downloaded.txt'),
        'skip_unavailable_fragments': True,  # Skip unavailable fragments robustly
    }
    if live_from_start:
        ydl_opts['live_from_start'] = True
    if not use_pot:
        ydl_opts['nop_plugins'] = True
    ydl_opts.update(format_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
        
        final_ext = ".mp3" if "Audio" in download_format else ".mp4"
        if not filename.endswith(final_ext):
             base, _ = os.path.splitext(filename)
             filename = base + final_ext

        if not os.path.exists(filename):
            if progress_hook: progress_hook({'status': 'error', 'message': f"File {filename} not found after download."})
            return None

        video_path = filename
        if "Audio" not in download_format:
            # Try to embed thumbnail into video
            base, _ = os.path.splitext(video_path)
            # Look for thumbnail files (webp or jpg)
            thumbnail_file = None
            for thumb_ext in ['.webp', '.jpg', '.png']:
                potential_thumb = base + thumb_ext
                if os.path.exists(potential_thumb):
                    thumbnail_file = potential_thumb
                    break
            
            if thumbnail_file:
                if progress_hook: progress_hook({'status': 'postprocessing', 'message': 'Embedding thumbnail into video...'})
                if embed_thumbnail_to_video(video_path, thumbnail_file):
                    if progress_hook: progress_hook({'status': 'postprocessing', 'message': 'Thumbnail embedded successfully'})
                else:
                    if progress_hook: progress_hook({'status': 'info', 'message': f'Thumbnail file preserved: {os.path.basename(thumbnail_file)}'})
        
        if progress_hook: progress_hook({'status': 'finished_video', 'message': f"Finished: {os.path.basename(video_path)}"})
        return video_path

    except Exception as e:
        error_msg = str(e)
        # More informative error messages
        if "127.0.0.1:4416" in error_msg or "PotProvider" in error_msg.lower() or "TransportError" in error_msg:
            if progress_hook: 
                progress_hook({'status': 'warning', 'message': 'PotProvider 伺服器未運行或無法連線。將使用普通模式繼續下載。'})
                progress_hook({'status': 'warning', 'message': '如需使用 PotProvider，請啟動本地伺服器：python -m http.server 4416'})
            # Try again without PotProvider
            if use_pot:
                ydl_opts['nop_plugins'] = True
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(video_url, download=True)
                        filename = ydl.prepare_filename(info)
                    final_ext = ".mp3" if "Audio" in download_format else ".mp4"
                    if not filename.endswith(final_ext):
                         base, _ = os.path.splitext(filename)
                         filename = base + final_ext
                    if os.path.exists(filename):
                        if progress_hook: progress_hook({'status': 'finished_video', 'message': f"Finished (without PotProvider): {os.path.basename(filename)}"})
                        return filename
                except Exception as retry_e:
                    if progress_hook: progress_hook({'status': 'error', 'message': f'重試失敗: {str(retry_e)}'})
                    return None
        if progress_hook: progress_hook({'status': 'error', 'message': error_msg})
        return None

def download_playlist(videos_to_download: List[Dict[str, Any]], output_path: str, use_cookies: bool, max_workers: int, zip_files: bool, download_format: str, use_pot: bool, progress_hook: Optional[Callable] = None, playlist_title_override: Optional[str] = None, write_info_json: bool = True) -> None:
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    files_to_process: List[str] = []
    zip_counter = 1
    # Assuming the playlist title can be inferred from the first video's info or passed differently
    playlist_title = playlist_title_override or "playlist" 
    if videos_to_download and not playlist_title_override:
        # A bit of a hack to get a playlist title if possible
        with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
            try:
                info = ydl.extract_info(videos_to_download[0]['webpage_url'], download=False)
                playlist_title = sanitize_filename(info.get('playlist_title', 'playlist'))
            except:
                pass


    def process_batch() -> None:
        nonlocal zip_counter
        if not files_to_process: return
        if zip_files:
            if progress_hook: progress_hook({'status': 'postprocessing', 'message': f'Zipping part {zip_counter}...'})
            zip_name = f"{playlist_title}_part_{zip_counter}.zip"
            zip_and_cleanup_files(list(files_to_process), zip_name, output_path)
        files_to_process.clear()
        zip_counter += 1

    total_videos = len(videos_to_download)
    if max_workers > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_video = {
                executor.submit(download_video, video['url'], output_path, video['playlist_index'], use_cookies, download_format, use_pot, progress_hook, write_info_json): video
                for video in videos_to_download
            }
            for i, future in enumerate(concurrent.futures.as_completed(future_to_video)):
                video = future_to_video[future]
                if progress_hook: progress_hook({'status': 'info', 'message': f'Processing video {i+1}/{total_videos}: {video["title"]}'})
                try:
                    video_path = future.result()
                    if video_path:
                        files_to_process.append(video_path)
                        if zip_files and len(files_to_process) >= FILES_PER_ZIP:
                            process_batch()
                except Exception as exc:
                    if progress_hook: progress_hook({'status': 'error', 'message': f'Error downloading {video["title"]}: {exc}'})
    else:
        for i, video in enumerate(videos_to_download):
            if progress_hook: progress_hook({'status': 'info', 'message': f'Processing video {i+1}/{total_videos}: {video["title"]}'})
            video_path = download_video(video['url'], output_path, video['playlist_index'], use_cookies, download_format, use_pot, progress_hook, write_info_json)
            if video_path:
                files_to_process.append(video_path)
                if zip_files and len(files_to_process) >= FILES_PER_ZIP:
                    process_batch()
    
    if zip_files:
        process_batch()
    
    if progress_hook: progress_hook({'status': 'postprocessing', 'message': 'Cleaning up temporary files...'})
    cleanup_temp_files(output_path)
    if progress_hook: progress_hook({'status': 'all_finished', 'message': 'All tasks completed.'})

def download_channel(channel_url: str, output_path: str, dl_type: dict[str, bool], 
                     use_cookies: bool, max_workers: int, zip_files: bool, download_format: str, use_pot: bool, progress_hook: Optional[Callable] = None, write_info_json: bool = True) -> None:
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    for key, value in dl_type.items():
        if value:
            target_url = f"{channel_url}/{key}"
            if progress_hook: progress_hook({'status': 'info', 'message': f'Analyzing {key} list...'})
            
            info = get_playlist_info(target_url, use_cookies, use_pot)
            if not info or 'entries' not in info:
                if progress_hook: progress_hook({'status': 'error', 'message': f'Failed to get videos for {key}'})
                continue
            
            entries = info['entries']
            if not entries: continue
            
            videos_to_download = []
            for i, entry in enumerate(entries):
                if entry and entry.get('url'):
                    videos_to_download.append({
                        'url': entry.get('url'),
                        'title': entry.get('title', 'Unknown'),
                        'playlist_index': i + 1,
                        'webpage_url': entry.get('url')
                    })
            
            channel_title = sanitize_filename(info.get('title', 'channel'))
            download_playlist(videos_to_download, output_path, use_cookies, max_workers, zip_files, download_format, use_pot, progress_hook, playlist_title_override=f"{channel_title}_{key}", write_info_json=write_info_json)

def _normalize_channel_url(channel_url: str) -> str:
    normalized = channel_url.strip().rstrip("/")
    normalized = re.sub(r"/(videos|shorts|streams|featured|live)$", "", normalized)
    return normalized

def _iter_live_entries(entries: Any):
    if not isinstance(entries, list):
        return
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("live_status") == "is_live":
            yield entry
        nested_entries = entry.get("entries")
        if isinstance(nested_entries, list):
            yield from _iter_live_entries(nested_entries)

def _get_live_candidate_urls(channel_url: str) -> List[str]:
    base_url = _normalize_channel_url(channel_url)
    candidates = [
        f"{base_url}/live",
        f"{base_url}/streams",
        base_url,
    ]
    deduped: List[str] = []
    seen = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped

def download_streaming(
    channel_url: str,
    output_path: str,
    use_cookies: bool,
    zip_files: bool,
    download_format: str,
    use_pot: bool,
    progress_hook: Optional[Callable] = None,
    write_info_json: bool = True,
    check_interval: int = 60,
    stop_flag: Optional[Callable[[], bool]] = None
) -> None:
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    downloaded_live_ids = set()

    def log(msg, status="info"):
        if progress_hook:
            progress_hook({'status': status, 'message': msg})

    log("Streaming 模式啟動：開始監控直播...")

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "cookiefile": 'cookies.txt' if use_cookies else None,
        'live_from_start': True,
    }

    if not use_pot:
        ydl_opts['nop_plugins'] = True

    try:
        while True:
            if stop_flag and stop_flag():
                log("Streaming 已停止", "warning")
                break
            try:
                log("檢查是否有直播中...")

                found_live = False
                for candidate_url in _get_live_candidate_urls(channel_url):
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(candidate_url, download=False)

                    if not info:
                        continue

                    live_entries = []
                    if info.get("live_status") == "is_live":
                        live_entries.append(info)
                    live_entries.extend(_iter_live_entries(info.get("entries")))

                    for entry in live_entries:
                        live_id = entry.get("id")
                        live_url = entry.get("webpage_url") or entry.get("url")

                        if not live_id or not live_url:
                            continue

                        found_live = True

                        if live_id in downloaded_live_ids:
                            continue

                        log(f"偵測到直播：{entry.get('title', 'Unknown')}")
                        downloaded_live_ids.add(live_id)

                        video_path = download_video(
                            video_url=live_url,
                            output_path=output_path,
                            video_number=0,
                            use_cookies=use_cookies,
                            download_format=download_format,
                            use_pot=use_pot,
                            progress_hook=progress_hook,
                            write_info_json=write_info_json,
                            live_from_start=True
                        )

                        if zip_files and video_path:
                            log("直播下載完成，開始壓縮...", "postprocessing")
                            base_name = os.path.splitext(os.path.basename(video_path))[0]
                            zip_name = f"{base_name}.zip"
                            zip_and_cleanup_files([video_path], zip_name, output_path)

                        cleanup_temp_files(output_path)

                if not found_live:
                    log("目前沒有直播")

            except Exception as e:
                log(f"偵測錯誤: {str(e)}", "error")

            time.sleep(check_interval)

    except KeyboardInterrupt:
        log("Streaming 監控已停止", "warning")

def download_single_video(video_url: str, output_path: str, use_cookies: bool, zip_files: bool, download_format: str, use_pot: bool, progress_hook: Optional[Callable] = None, write_info_json: bool = True) -> None:
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    video_path = download_video(video_url, output_path, 0, use_cookies, download_format, use_pot, progress_hook, write_info_json)

    if zip_files and video_path:
        if progress_hook: progress_hook({'status': 'postprocessing', 'message': 'Zipping file...'})
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        zip_name = f"{base_name}.zip"
        zip_and_cleanup_files([video_path], zip_name, output_path)

    if progress_hook: progress_hook({'status': 'postprocessing', 'message': 'Cleaning up temporary files...'})
    cleanup_temp_files(output_path)
    if progress_hook: progress_hook({'status': 'all_finished', 'message': 'All tasks completed.'})

# --- Unchanged Functions ---
def update_yt_dlp():
    try:
        subprocess.check_call([sys.executable, "-m", "yt_dlp", "-U"])
        print("yt-dlp updated successfully.")
    except Exception as e:
        print(f"Failed to update yt-dlp: {e}")
def sanitize_filename(filename: str) -> str: return re.sub(r'[\/*?:"<>|]', "", filename)
def embed_thumbnail_to_video(video_path: str, thumbnail_path: str) -> bool:
    """使用 FFmpeg 將縮圖嵌入到 MP4 檔案中。"""
    if not os.path.exists(video_path) or not os.path.exists(thumbnail_path):
        return False
    
    try:
        # Create temporary output file
        temp_output = video_path + ".tmp.mp4"
        
        # Use FFmpeg to embed thumbnail as cover art
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', thumbnail_path,
            '-c', 'copy',  # Copy streams without re-encoding
            '-map', '0',
            '-map', '1',
            '-c:v:1', 'mjpeg',  # Set picture codec
            '-disposition:v:1', 'attached_pic',  # Mark as cover art
            '-y',  # Overwrite output
            temp_output
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and os.path.exists(temp_output):
            # Replace original with embedded version
            os.remove(video_path)
            os.rename(temp_output, video_path)
            return True
        else:
            # Cleanup temp file if failed
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False
    except Exception as e:
        print(f"[警告] 縮圖嵌入失敗: {e}")
        return False

def set_thumbnail(video_path: str, thumbnail_path: str): pass
def embed_chapters(video_path: str, chapters: List[Dict[str, Any]]): pass
def zip_and_cleanup_files(file_list: List[str], zip_name: str, output_path: str):
    """Zips the given files and then deletes them."""
    zip_path = os.path.join(output_path, zip_name)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in file_list:
            if os.path.exists(file):
                zipf.write(file, os.path.basename(file))
                print(f"Added to zip: {file}")
    
    # After zipping, remove the original files
    for file in file_list:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"Removed original file: {file}")
            except OSError as e:
                print(f"Error removing original file {file}: {e}")
def cleanup_temp_files(output_path: str):
    """Deletes temporary files from the output directory, but preserves thumbnails."""
    # Only delete actual temporary files
    for pattern in TEMP_FILE_PATTERNS:
        for file_path in glob.glob(os.path.join(output_path, pattern)):
            try:
                os.remove(file_path)
                print(f"Removed temp file: {file_path}")
            except OSError as e:
                print(f"Error removing temp file {file_path}: {e}")
    
    # Keep thumbnail files (.webp, .jpg) - do NOT delete them
    print(f"[Info] Thumbnail files (.webp, .jpg) preserved in output directory")
