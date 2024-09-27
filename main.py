import tkinter as tk
import customtkinter as ctk
from lib import *

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color="white")

        self.title("Youtube Downloader")
        self.geometry(f"{720}x{540}")
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, width=50, text="YouTube 下載器")
        self.label.grid(row=0, column=0, padx=20, pady=20)

        self.mode_button = ctk.CTkSegmentedButton(self)
        self.mode_button.configure(values=["Video", "Playlist"])
        self.mode_button.set("Value 2")
        self.mode_button.grid(row=1, column=0, padx=(20, 10), pady=(10, 10))

        self.entry_path = ctk.CTkEntry(self, placeholder_text="Route", width=500)
        self.entry_path.grid(row=2, column=0, padx=(20, 0), pady=(20, 20))

        self.entry_url = ctk.CTkEntry(self, placeholder_text="Url", width=500)
        self.entry_url.grid(row=3, column=0, padx=(20, 0), pady=(20, 20))

        self.button_1 = ctk.CTkButton(master=self, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), text="Download", command=lambda: self.download(self.mode_button.get(), self.entry_url.get(), self.entry_path.get()))
        self.button_1.grid(row=4, column=0, padx=(20, 20), pady=(20, 20))

    def download(self, mode, url, path):
        if mode == "Video":
            download_single_video(url, path)
        elif mode == "Playlist":
            download_playlist(url, path, 5)
        cleanup_temp_files()

if __name__ == "__main__":
    app = App()
    app.mainloop()
