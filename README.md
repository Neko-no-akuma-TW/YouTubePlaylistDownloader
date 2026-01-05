# YouTubeDownloader 

---

## 介紹
這是一個用於下載YouTube播放清單的Python程式碼</br>
此程式支援多線程下載，並且也同時支援下載字幕  
(不會下載自動生成的字幕與翻譯字幕)  
(僅會下載繁體中文、簡體中文、英文、日文語言的字幕)  
(優先選擇.vtt檔案，如果沒有，則會下載.srt檔案)  

---

## 使用方法
1. 安裝Python
2. 安裝 [FFmpeg](https://ffmpeg.org/download.html)，並將其執行檔路徑加入到系統的 `PATH` 環境變數中。程式在執行時會需要它。
3. 安裝所需套件
```
pip install -r requirements.txt
```
4. 執行程式
```
python main.py
```

---

## 提示
本程式支持透過Google帳號登入下載被授權可瀏覽的私人影片與播放清單，以下是使用教學(如不需下載私人影片可以不用進行下方操作)
1. 開啟瀏覽器的無痕模式
2. 開啟YouTube並登入帳號
3. 在登入完成的無痕瀏覽器分頁瀏覽後方網址(https://youtube.com/robots.txt)
4. 透過獲取Cookie的插件將Cookie匯出成純文字檔，如果沒有，可以到[這裡](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)獲取一個

PS: 如果你在使用Cookie後有出現警告，可以使用這個[專案](https://github.com/Brainicism/bgutil-ytdlp-pot-provider)，具體操作步驟請自行參考該專案的README文件。完成伺服器的啟動後，重啟本應用即可。


# ⚠️cookies.txt必須在使用此程式前更新，否則可能會無法下載私人影片
# ⚠️cookies.txt內有您的登入以及其他隱私資訊，請勿分享給他人
# ⚠️如果因為使用cookie進行下載而造成帳號被封鎖、停權等，開發者不負相關責任


---

## 歡迎各位創建PR(Pull Request)讓這個專案變得更好

---

## 感謝以下的協作者們
因為有你們，所以這個專案才會變得更好。<br/>
<a href="https://github.com/Neko-no-akuma-TW/YouTubePlaylistDownloader/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Neko-no-akuma-TW/YouTubePlaylistDownloader" />
</a>

---

# 版權聲明
此專案僅在此網站(Github)發布並開源，若於其他網站下載，造成使用者財產損失，開發者將不負相關責任。

此外，本專案為完全免費開源，若使用者於其他網站花費購買此開源軟件，開發者將不負賠償責任。

最後，任何使用者皆可以使用此專案進行二次開發，但是禁止將此專案用於商業與營利用途，並且需要標示原創作者與作品來源。
