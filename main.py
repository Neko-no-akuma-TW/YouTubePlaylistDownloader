import tkinter as tk
import customtkinter as ctk
from lib import *  # 假設你的下載程式碼在 lib.py 中
import os
from tkinter import filedialog
from tkinter import messagebox
import threading

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color="white")

        self.title("YouTube Downloader")
        self.geometry(f"{720}x{540}")
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, width=50, text="YouTube 下載器")
        self.label.grid(row=0, column=0, padx=20, pady=20)

        self.mode_button = ctk.CTkSegmentedButton(self)
        self.mode_button.configure(values=["Video", "Playlist"])
        self.mode_button.set("Video")  # 預設選擇 Video
        self.mode_button.grid(row=1, column=0, padx=(20, 10), pady=(10, 10))

        self.entry_url = ctk.CTkEntry(self, placeholder_text="影片 URL", width=500)
        self.entry_url.grid(row=2, column=0, padx=(20, 0), pady=(20, 20))

        self.entry_path = ctk.CTkEntry(self, placeholder_text="儲存路徑", width=500)
        self.entry_path.grid(row=3, column=0, padx=(20, 0), pady=(20, 20))

        self.browse_button = ctk.CTkButton(master=self, text="瀏覽", width=100, command=self.browse_directory)
        self.browse_button.grid(row=3, column=1, padx=(0, 20), pady=(20, 20))

        self.use_cookies_var = tk.BooleanVar(value=False)  # 預設不使用 cookies
        self.use_cookies_checkbox = ctk.CTkCheckBox(self, text="使用 cookies.txt", variable=self.use_cookies_var)
        self.use_cookies_checkbox.grid(row=4, column=0, padx=(20, 20), pady=(10, 10), sticky="w")

        self.button_1 = ctk.CTkButton(master=self, fg_color="transparent", border_width=2,
                                      text_color=("gray10", "#DCE4EE"), text="下載",
                                      command=self.start_download)
        self.button_1.grid(row=5, column=0, padx=(20, 20), pady=(20, 20))

        self.progressbar = ctk.CTkProgressBar(self, width=500)
        self.progressbar.grid(row=6, column=0, padx=(20, 20), pady=(10, 10), sticky="ew")
        self.progressbar.set(0)
        self.progressbar.configure(mode="indeterminate")

    def browse_directory(self):
        """開啟資料夾選擇對話框，並將選取的路徑填入路徑輸入框。"""
        directory = filedialog.askdirectory()
        if directory:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, directory)

    def start_download(self):
        mode = self.mode_button.get()
        url = self.entry_url.get().strip()
        path = self.entry_path.get().strip()
        use_cookies = self.use_cookies_var.get()

        if not url:
            messagebox.showerror("錯誤", "請輸入影片 URL")
            return
        if not path:
            messagebox.showerror("錯誤", "請輸入儲存路徑")
            return

        # 建立新的執行緒來執行下載
        download_thread = threading.Thread(target=self.run_download, args=(mode, url, path, use_cookies))
        download_thread.start()
        self.progressbar.start()


    def run_download(self, mode, url, path, use_cookies):
        """在背景執行緒中執行下載，並處理完成或錯誤訊息。"""
        try:
            self.download(mode, url, path, use_cookies)
            self.after(0, lambda: messagebox.showinfo("完成", "下載完成"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("錯誤", f"下載時發生錯誤：{e}"))
        finally:
            self.after(0, self.stop_progress)

    def stop_progress(self):
        """停止進度條"""
        self.progressbar.stop()
        self.progressbar.set(0)

    def download(self, mode, url, path, use_cookies):
        if mode == "Video":
            download_single_video(url, path, use_cookies)
        elif mode == "Playlist":
            download_playlist(url, path, use_cookies, 5)
        cleanup_temp_files(path)


if __name__ == "__main__":
    app = App()
    app.mainloop()
