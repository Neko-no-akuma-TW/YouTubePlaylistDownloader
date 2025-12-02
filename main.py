from lib import *
import os
import threading
import argparse
import sys
import shutil
import webbrowser
import json
from typing import Dict, Any, List, Callable
from queue import Queue

if len(sys.argv) == 1:
    import tkinter as tk
    import customtkinter as ctk
    from tkinter import filedialog, messagebox

# --- Config Functions ---
CONFIG_FILE = "config.json"

def load_config() -> Dict[str, Any]:
    defaults = {
        "path": "", "use_cookies": False, "multithread": False, 
        "threads": 5, "zip_files": True, "format": "Best Video"
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            try:
                loaded_config = json.load(f)
                defaults.update(loaded_config)
            except json.JSONDecodeError:
                pass # Use defaults if config is corrupted
    return defaults

def save_config(config: Dict[str, Any]) -> None:
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def check_ffmpeg() -> bool: return shutil.which('ffmpeg') is not None

def handle_ffmpeg_not_found() -> None:
    # ... (implementation unchanged)
    sys.exit(1)

class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__(fg_color="white")
        self.config = load_config()
        self.progress_queue = Queue()
        self.video_checkboxes: List[ctk.CTkCheckBox] = []

        self.title("YouTube Downloader")
        self.geometry(f"{800}x900")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.grid_columnconfigure(0, weight=1)

        # --- Widgets ---
        # ... (Top label)
        self.label = ctk.CTkLabel(self, text="YouTube Downloader", font=ctk.CTkFont(size=20, weight="bold"))
        self.label.grid(row=0, column=0, columnspan=3, padx=20, pady=10)

        self.mode_button = ctk.CTkSegmentedButton(self, values=["Video", "Playlist"], command=self.toggle_mode)
        self.mode_button.grid(row=1, column=0, columnspan=3, padx=20, pady=10, sticky="ew")

        self.url_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.url_frame.grid(row=2, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        self.url_frame.grid_columnconfigure(0, weight=1)
        self.entry_url = ctk.CTkEntry(self.url_frame, placeholder_text="影片或播放清單 URL")
        self.entry_url.grid(row=0, column=0, sticky="ew")
        self.analyze_button = ctk.CTkButton(self.url_frame, text="分析", width=80, command=self.analyze_playlist)
        self.analyze_button.grid(row=0, column=1, padx=(10, 0))

        # ... (Path, Format, and other options)
        self.path_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.path_frame.grid(row=3, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        self.path_frame.grid_columnconfigure(0, weight=1)
        self.entry_path = ctk.CTkEntry(self.path_frame, placeholder_text="儲存路徑")
        self.entry_path.grid(row=0, column=0, sticky="ew")
        self.browse_button = ctk.CTkButton(self.path_frame, text="瀏覽", width=80, command=self.browse_directory)
        self.browse_button.grid(row=0, column=1, padx=(10, 0))

        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.grid(row=4, column=0, columnspan=3, padx=20, pady=0, sticky="ew")
        self.options_frame.grid_columnconfigure(0, weight=1)
        self.options_frame.grid_columnconfigure(1, weight=1)

        self.format_label = ctk.CTkLabel(self.options_frame, text="下載格式:")
        self.format_label.grid(row=0, column=0, padx=(0,10), pady=5, sticky="w")
        self.format_var = tk.StringVar()
        self.format_menu = ctk.CTkOptionMenu(self.options_frame, values=["Best Video", "1080p", "720p", "Audio (MP3)"], variable=self.format_var)
        self.format_menu.grid(row=1, column=0, sticky="ew", padx=(0,10))

        self.thread_slider_label = ctk.CTkLabel(self.options_frame, text="線程數: 5")
        self.thread_slider_label.grid(row=0, column=1, padx=(10,0), pady=5, sticky="w")
        self.thread_slider = ctk.CTkSlider(self.options_frame, from_=1, to=10, number_of_steps=9, command=self.update_thread_label)
        self.thread_slider.grid(row=1, column=1, sticky="ew", padx=(10,0))

        self.checkbox_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.checkbox_frame.grid(row=5, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        self.use_cookies_var = tk.BooleanVar()
        self.use_cookies_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="使用 cookies.txt", variable=self.use_cookies_var)
        self.use_cookies_checkbox.pack(side="left", padx=(0, 20))
        self.zip_files_var = tk.BooleanVar()
        self.zip_files_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="下載後壓縮", variable=self.zip_files_var)
        self.zip_files_checkbox.pack(side="left", padx=(0, 20))
        self.multithread_var = tk.BooleanVar()
        self.multithread_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="多線程下載", variable=self.multithread_var, command=self.toggle_multithread_options)
        self.multithread_checkbox.pack(side="left")

        # Playlist Frame
        self.playlist_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.playlist_frame.grid(row=6, column=0, columnspan=3, padx=20, pady=10, sticky="nsew")
        self.playlist_frame.grid_columnconfigure(0, weight=1)
        self.playlist_controls_frame = ctk.CTkFrame(self.playlist_frame, fg_color="transparent")
        self.playlist_controls_frame.pack(fill="x")
        self.select_all_button = ctk.CTkButton(self.playlist_controls_frame, text="全選", command=lambda: self.toggle_all_videos(True))
        self.select_all_button.pack(side="left")
        self.deselect_all_button = ctk.CTkButton(self.playlist_controls_frame, text="取消全選", command=lambda: self.toggle_all_videos(False))
        self.deselect_all_button.pack(side="left", padx=10)
        self.video_list_frame = ctk.CTkScrollableFrame(self.playlist_frame, label_text="播放清單影片")
        self.video_list_frame.pack(fill="both", expand=True, pady=(10,0))
        self.grid_rowconfigure(6, weight=1)

        # --- Bottom Widgets ---
        self.download_button = ctk.CTkButton(self, text="下載", command=self.start_download)
        self.download_button.grid(row=7, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        self.progressbar = ctk.CTkProgressBar(self)
        self.progressbar.grid(row=8, column=0, columnspan=3, padx=20, pady=(0, 10), sticky="ew")
        self.progressbar.set(0)
        self.log_box = ctk.CTkTextbox(self, height=100, state="disabled")
        self.log_box.grid(row=9, column=0, columnspan=3, padx=20, pady=(0, 10), sticky="nsew")

        # --- Initial State ---
        self.load_settings_to_ui()
        self.toggle_mode(self.mode_button.get() or "Video")
        self.check_progress_queue()

    def toggle_mode(self, mode: str):
        is_playlist = mode == "Playlist"
        self.analyze_button.configure(state=tk.NORMAL if is_playlist else tk.DISABLED)
        self.multithread_checkbox.configure(state=tk.NORMAL if is_playlist else tk.DISABLED)
        if not is_playlist:
            self.multithread_var.set(False)
            # Hide playlist frame
            self.playlist_frame.grid_remove()
            self.grid_rowconfigure(6, weight=0)
        else:
            # Show playlist frame
            self.playlist_frame.grid()
            self.grid_rowconfigure(6, weight=1)
        self.toggle_multithread_options()

    def analyze_playlist(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showerror("錯誤", "請先輸入播放清單 URL")
            return
        
        self.log("正在分析播放清單...")
        self.analyze_button.configure(state=tk.DISABLED)
        # Clear old checkboxes
        for checkbox in self.video_checkboxes:
            checkbox.destroy()
        self.video_checkboxes.clear()

        analysis_thread = threading.Thread(target=self.run_analysis, args=(url,))
        analysis_thread.start()

    def run_analysis(self, url: str):
        playlist_info = get_playlist_info(url, self.use_cookies_var.get())
        self.after(0, self.populate_playlist_frame, playlist_info)

    def populate_playlist_frame(self, playlist_info: Optional[Dict[str, Any]]):
        self.analyze_button.configure(state=tk.NORMAL)
        if not playlist_info or 'entries' not in playlist_info:
            self.log("[錯誤] 無法獲取播放清單資訊。\n")
            messagebox.showerror("錯誤", "無法獲取播放清單資訊，請檢查 URL 或網路連線。\n")
            return

        entries = playlist_info['entries']
        self.log(f"分析完成，找到 {len(entries)} 個影片。\n")
        for i, entry in enumerate(entries):
            if not entry: continue
            var = tk.IntVar(value=1)
            checkbox = ctk.CTkCheckBox(self.video_list_frame, text=f"{i+1:03d} - {entry.get('title', '未知標題')}", variable=var)
            checkbox.video_info = {'url': entry['url'], 'title': entry.get('title', '未知標題'), 'playlist_index': i + 1}
            checkbox.pack(anchor="w", padx=5, pady=2)
            self.video_checkboxes.append(checkbox)

    def toggle_all_videos(self, select: bool):
        for checkbox in self.video_checkboxes:
            if select:
                checkbox.select()
            else:
                checkbox.deselect()

    def start_download(self):
        self.save_settings_from_ui()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state="disabled")
        self.log("開始準備下載...")
        self.progressbar.set(0)

        mode = self.mode_button.get()
        url = self.entry_url.get().strip()
        path = self.entry_path.get().strip()
        if not url or not path:
            messagebox.showerror("錯誤", "請輸入 URL 和儲存路徑")
            return

        self.download_button.configure(state=tk.DISABLED)
        self.progressbar.configure(mode="indeterminate")

        args = {
            "output_path": path,
            "use_cookies": self.use_cookies_var.get(),
            "zip_files": self.zip_files_var.get(),
            "download_format": self.format_var.get(),
            "progress_hook": self.progress_queue.put
        }

        if mode == "Video":
            args["video_url"] = url
            target = download_single_video
        else: # Playlist
            videos_to_download = [cb.video_info for cb in self.video_checkboxes if cb.get() == 1]
            if not videos_to_download:
                messagebox.showwarning("提示", "請至少選擇一個播放清單中的影片。\n")
                self.download_button.configure(state=tk.NORMAL)
                return
            args["videos_to_download"] = videos_to_download
            args["max_workers"] = int(self.thread_slider.get()) if self.multithread_var.get() else 1
            target = download_playlist

        download_thread = threading.Thread(target=target, kwargs=args)
        download_thread.start()

    # ... (other methods like on_closing, load_settings, save_settings, logging, progress handling are mostly the same)
    def on_closing(self) -> None:
        self.save_settings_from_ui()
        self.destroy()

    def load_settings_to_ui(self) -> None:
        self.entry_path.insert(0, self.config.get("path", ""))
        self.use_cookies_var.set(self.config.get("use_cookies", False))
        self.zip_files_var.set(self.config.get("zip_files", True))
        self.multithread_var.set(self.config.get("multithread", False))
        thread_count = self.config.get("threads", 5)
        self.thread_slider.set(thread_count)
        self.update_thread_label(thread_count)
        self.format_var.set(self.config.get("format", "Best Video"))

    def save_settings_from_ui(self) -> None:
        self.config["path"] = self.entry_path.get().strip()
        self.config["use_cookies"] = self.use_cookies_var.get()
        self.config["zip_files"] = self.zip_files_var.get()
        self.config["multithread"] = self.multithread_var.get()
        self.config["threads"] = int(self.thread_slider.get())
        self.config["format"] = self.format_var.get()
        save_config(self.config)

    def browse_directory(self) -> None:
        directory = filedialog.askdirectory()
        if directory:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, directory)

    def toggle_multithread_options(self) -> None:
        is_multithread_enabled = self.multithread_var.get() and self.mode_button.get() == "Playlist"
        self.thread_slider_label.configure(state=tk.NORMAL if is_multithread_enabled else tk.DISABLED)
        self.thread_slider.configure(state=tk.NORMAL if is_multithread_enabled else tk.DISABLED)

    def update_thread_label(self, value: float) -> None:
        self.thread_slider_label.configure(text=f"線程數: {int(value)}")

    def check_progress_queue(self):
        try:
            while True:
                progress_data = self.progress_queue.get_nowait()
                self.handle_progress_update(progress_data)
        except Exception:
            pass
        self.after(100, self.check_progress_queue)

    def handle_progress_update(self, data: Dict[str, Any]):
        status = data.get('status')
        if status == 'downloading':
            self.progressbar.configure(mode="determinate")
            total_bytes = data.get('total_bytes') or data.get('total_bytes_estimate')
            downloaded_bytes = data.get('downloaded_bytes')
            if total_bytes and downloaded_bytes:
                self.progressbar.set(downloaded_bytes / total_bytes)
        elif status == 'finished':
            self.progressbar.set(1)
            self.log("下載完成，正在進行後處理...")
        elif status == 'all_finished':
            self.on_download_complete()
        elif status in ['info', 'postprocessing', 'finished_video', 'warning', 'error']:
            self.log(f"[{status.upper()}] {data.get('message')}")

    def log(self, message: str):
        """Appends a message to the log box."""
        if self.log_box.winfo_exists(): # Check if widget exists
            self.log_box.configure(state="normal")
            self.log_box.insert(tk.END, message + "\n")
            self.log_box.configure(state="disabled")
            self.log_box.see(tk.END)

    def on_download_complete(self) -> None:
        self.progressbar.set(1)
        self.progressbar.configure(mode="determinate")
        self.download_button.configure(state=tk.NORMAL)
        self.log("全部任務完成！")
        messagebox.showinfo("完成", "下載完成！")

    def on_download_error(self, error: Exception) -> None:
        self.progressbar.stop()
        self.progressbar.set(0)
        self.download_button.configure(state=tk.NORMAL)
        self.log(f"[CRITICAL ERROR] {error}")
        messagebox.showerror("錯誤", f"下載時發生嚴重錯誤：\n{error}")

if __name__ == "__main__":
    if not check_ffmpeg():
        handle_ffmpeg_not_found()

    update_yt_dlp()

    # CLI mode is not updated with new features in this pass
    if len(sys.argv) > 1:
        print("CLI mode is not fully featured. Please run the GUI.")
    else:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        app = App()
        app.mainloop()
