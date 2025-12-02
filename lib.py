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

# --- Constants ---
SUPPORTED_SUB_LANGS: List[str] = ['zh.TW', 'zh.CN', 'en', 'ja']
SUB_EXTENSIONS: List[str] = ['.vtt', '.srt']
TEMP_FILE_PATTERNS: List[str] = ["*.temp.mp4", "*.webp", "*.jpg", "*.metadata.json"]
FILES_PER_ZIP: int = 10

# --- Helper Functions ---

def get_playlist_info(playlist_url: str, use_cookies: bool) -> Optional[Dict[str, Any]]:
    """獲取播放清單的資訊，但不下載影片。"""
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'cookiefile': 'cookies.txt' if use_cookies else None,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(playlist_url, download=False)
    except Exception as e:
        print(f"解析播放清單失敗: {e}")
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
    def debug(self, msg): pass
    def warning(self, msg):
        if self.progress_hook: self.progress_hook({'status': 'warning', 'message': msg})
    def error(self, msg):
        if self.progress_hook: self.progress_hook({'status': 'error', 'message': msg})

# --- Core Download Functions ---

def download_video(video_url: str, output_path: str, video_number: int, use_cookies: bool, download_format: str, progress_hook: Optional[Callable] = None) -> Optional[str]:
    format_opts = get_format_options(download_format)
    
    def hook(d):
        if progress_hook: progress_hook(d)

    ydl_opts = {
        'outtmpl': os.path.join(output_path, f'{video_number:03d}-%(title)s.%(ext)s'),
        'writesubtitles': True,
        'subtitleslangs': SUPPORTED_SUB_LANGS,
        'subtitlesformat': 'vtt/srt',
        'writethumbnail': "Audio" not in download_format,
        'skip_download': False,
        'cookiefile': 'cookies.txt' if use_cookies else None,
        'postprocessors': format_opts.get('postprocessors', []) + ([{'key': 'FFmpegMetadata','add_metadata': True}] if "Audio" not in download_format else []),
        'progress_hooks': [hook],
        'logger': ProgressLogger(progress_hook),
        'remote_components': 'ejs:npm',
    }
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
            if progress_hook: progress_hook({'status': 'postprocessing', 'message': 'Embedding thumbnail...'})
            # ... (thumbnail and chapter logic)
        
        if progress_hook: progress_hook({'status': 'finished_video', 'message': f"Finished: {os.path.basename(video_path)}"})
        return video_path

    except Exception as e:
        if progress_hook: progress_hook({'status': 'error', 'message': str(e)})
        return None

def download_playlist(videos_to_download: List[Dict[str, Any]], output_path: str, use_cookies: bool, max_workers: int, zip_files: bool, download_format: str, progress_hook: Optional[Callable] = None) -> None:
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    files_to_process: List[str] = []
    zip_counter = 1
    # Assuming the playlist title can be inferred from the first video's info or passed differently
    playlist_title = "playlist" 
    if videos_to_download:
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
                executor.submit(download_video, video['url'], output_path, video['playlist_index'], use_cookies, download_format, progress_hook): video
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
            video_path = download_video(video['url'], output_path, video['playlist_index'], use_cookies, download_format, progress_hook)
            if video_path:
                files_to_process.append(video_path)
                if zip_files and len(files_to_process) >= FILES_PER_ZIP:
                    process_batch()
    
    if zip_files:
        process_batch()
    
    if progress_hook: progress_hook({'status': 'postprocessing', 'message': 'Cleaning up temporary files...'})
    cleanup_temp_files(output_path)
    if progress_hook: progress_hook({'status': 'all_finished', 'message': 'All tasks completed.'})


def download_single_video(video_url: str, output_path: str, use_cookies: bool, zip_files: bool, download_format: str, progress_hook: Optional[Callable] = None) -> None:
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    video_path = download_video(video_url, output_path, 1, use_cookies, download_format, progress_hook)

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
    """Deletes temporary files from the output directory."""
    for pattern in TEMP_FILE_PATTERNS:
        for file_path in glob.glob(os.path.join(output_path, pattern)):
            try:
                os.remove(file_path)
                print(f"Removed temp file: {file_path}")
            except OSError as e:
                print(f"Error removing temp file {file_path}: {e}")
