import yt_dlp
import concurrent.futures
import os
import re
import subprocess
import json


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def set_thumbnail(video_path, thumbnail_path):
    temp_file = f'{video_path}.temp.mp4'
    try:
        # Convert webp to jpg
        jpg_thumbnail = f'{thumbnail_path}.jpg'
        subprocess.run(['ffmpeg', '-i', thumbnail_path, jpg_thumbnail], check=True, stderr=subprocess.DEVNULL)

        # Embed jpg thumbnail
        subprocess.run(['ffmpeg', '-i', video_path, '-i', jpg_thumbnail,
                        '-map', '0', '-map', '1', '-c', 'copy',
                        '-disposition:v:1', 'attached_pic', temp_file],
                       check=True, stderr=subprocess.DEVNULL)

        os.replace(temp_file, video_path)
        print(f"成功設置縮圖: {video_path}")

        # Clean up
        os.remove(jpg_thumbnail)
    except subprocess.CalledProcessError as e:
        print(f"設置縮圖失敗: {video_path}. 錯誤: {str(e)}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


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


def download_video(video_url, output_path, video_number):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_path, f'{video_number:03d}-%(title)s.%(ext)s'),
        'writesubtitles': True,
        'subtitleslangs': ['zh.TW', 'zh.CN', 'en', 'ja'],
        'subtitlesformat': 'vtt,srt',
        'writethumbnail': True,
        'skip_download': False,
        'merge_output_format': 'mp4',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=True)
            video_title = sanitize_filename(info['title'])
            base_filename = f"{video_number:03d}-{video_title}"
            video_path = os.path.join(output_path, f"{base_filename}.mp4")

            # 處理字幕文件
            for lang in ['zh.TW', 'zh.CN', 'en', 'ja']:
                vtt_subtitle = os.path.join(output_path, f"{base_filename}.{lang}.vtt")
                if os.path.exists(vtt_subtitle):
                    print(f"已下載 VTT 字幕: {vtt_subtitle}")
                else:
                    print(f"未找到 {lang} 的 VTT 字幕")

            for lang in ['zh.TW', 'zh.CN', 'en', 'ja']:
                srt_subtitle = os.path.join(output_path, f"{base_filename}.{lang}.srt")
                if os.path.exists(srt_subtitle):
                    print(f"已下載 SRT 字幕: {srt_subtitle}")
                    vtt_subtitle = os.path.join(output_path, f"{base_filename}.{lang}.vtt")
                    if os.path.exists(vtt_subtitle):
                        os.remove(srt_subtitle)  # 刪除 SRT 字幕文件
                else:
                    print(f"未找到 {lang} 的 SRT 字幕")

            # 設置縮圖
            thumbnail_path = os.path.join(output_path, f"{base_filename}.webp")
            if os.path.exists(thumbnail_path):
                set_thumbnail(video_path, thumbnail_path)
                os.remove(thumbnail_path)  # 刪除原始縮圖文件

            # 嵌入章節
            if 'chapters' in info:
                embed_chapters(video_path, info['chapters'])
            else:
                print(f"視頻沒有章節信息: {base_filename}")

            print(f"成功下載: {base_filename}")
        except Exception as e:
            print(f"下載失敗 {video_url}: {str(e)}")


def download_playlist(playlist_url, output_path, max_workers=5):
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    with yt_dlp.YoutubeDL({'extract_flat': True, 'quiet': True}) as ydl:
        playlist_dict = ydl.extract_info(playlist_url, download=False)
        if 'entries' not in playlist_dict:
            print('無法找到播放清單')
            return

        video_urls = [(i + 1, entry['url']) for i, entry in enumerate(playlist_dict['entries'])]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_video, url, output_path, num) for num, url in video_urls]
        concurrent.futures.wait(futures)


def cleanup_temp_files(output_path):
    for filename in os.listdir(output_path):
        if filename.endswith('.temp.mp4'):
            file_path = os.path.join(output_path, filename)
            try:
                os.remove(file_path)
                print(f"已刪除臨時文件: {filename}")
            except Exception as e:
                print(f"刪除臨時文件失敗 {filename}: {str(e)}")


if __name__ == "__main__":
    playlist_url = input("請輸入YouTube播放清單URL: ")
    output_path = input("請輸入保存路徑: ")
    max_workers = int(input("請輸入同時下載的最大線程數 (建議 5): "))

    download_playlist(playlist_url, output_path, max_workers)
    cleanup_temp_files(output_path)
    print("下載完成！")