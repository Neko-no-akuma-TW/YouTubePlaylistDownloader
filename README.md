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
2. 安裝ffmepg 把exe 放入 Python的 Scripts 文件夾
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
1. 在瀏覽器安裝[此套件](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. 登入Google帳號
3. 前往YouTube並登入
4. 點擊套件圖示，並且點擊`Export All Cookies`，將cookies.txt下載下來
5. 將cookies.txt放入程式資料夾
6. 執行程式

# ⚠️cookies.txt必須在使用此程式前更新，否則可能會無法下載私人影片
# ⚠️cookies.txt內有您的登入以及其他隱私資訊，請勿分享給他人


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
