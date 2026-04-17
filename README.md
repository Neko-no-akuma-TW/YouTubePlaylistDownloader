# YouTubeDownloader 

---

## 介紹
這是一個用於下載YouTube播放清單的Python程式碼</br>
此程式支援多執行緒下載，並且也同時支援下載字幕  
(不會下載自動生成的字幕與翻譯字幕)  
(僅會下載繁體中文、簡體中文、英文、日文語言的字幕)  
(優先選擇.vtt檔案，如果沒有，則會下載.srt檔案)  

### 功能
- ✅ 下載並保留影片縮圖 (.webp/.jpg 格式)
- ✅ 自動將縮圖嵌入到影片檔案中（作為封面）
- ✅ 下載影片資訊 (JSON 格式資訊)
- ✅ 支援多執行緒加速下載
- ✅ 支援下載字幕和影片資訊  
- ✅ 持續偵測特定頻道直播並下載  

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

## 檔案說明
下載完成後，輸出目錄中會包含以下檔案：

| 檔案類型 | 說明 | 備註 |
|---------|------|------|
| `.mp4` / `.mp3` | 影片或聲音檔案 | 縮圖會嵌入其中 |
| `.webp` / `.jpg` | 影片縮圖 | 同時保留供使用者使用 |
| `.json` | 影片資訊 | 包含標題、描述、上傳時間等資訊 |
| `.vtt` / `.srt` | 字幕檔案 | 支援的語言自動下載 |
| `.info.json` | 原始URL資訊 | 用於追蹤下載來源 |

---

## 提示
本程式支援透過Google帳號登入下載被授權可瀏覽的私人影片與播放清單，以下是使用教學(如不需下載私人影片可以不用進行下方操作)
1. 開啟瀏覽器的無痕模式
2. 開啟YouTube並登入帳號
3. 在登入完成的無痕瀏覽器分頁瀏覽後方網址(https://youtube.com/robots.txt)
4. 透過獲取Cookie的插件將Cookie匯出成純文字檔，如果沒有，可以到[這裡](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)獲取一個

PS: 如果你在使用Cookie後有出現警告，可以使用這個[專案](https://github.com/Brainicism/bgutil-ytdlp-pot-provider)，具體操作步驟請自行參考該專案的README檔案。完成伺服器的啟動後，重啟本應用即可。

## 關於縮圖嵌入
本程式會自動嘗試將下載的縮圖嵌入到 MP4 檔案中（作為封面圖片），此功能需要 FFmpeg 支援。
- 如果嵌入成功，影片播放器會顯示縮圖作為封面
- 如果嵌入失敗，縮圖檔案 (.webp/.jpg) 會被保留在輸出目錄中，您可以手動使用
- 若要使用此功能，請確保已正確安裝並配置 FFmpeg


# ⚠️cookies.txt內有您的登入以及其他隱私資訊，請勿分享給他人
# ⚠️如果因為使用cookie進行下載而造成帳號被封鎖、停權等，開發者不負相關責任


---

## 歡迎各位創建PR(Pull Request)讓這個專案變得更好

---

## 感謝以下的協作者們
因為有你們，所以這個專案才會變得更好。<br/>
<!-- readme: collaborators,contributors -start -->
<table>
<tr>
    <td align="center">
        <a href="https://github.com/Neko-no-akuma-TW">
            <img src="https://avatars.githubusercontent.com/u/80331285?v=4" width="100;" alt="Neko-no-akuma-TW"/>
            <br />
            <sub><b>Neko No Akuma</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/amoeba1125">
            <img src="https://avatars.githubusercontent.com/u/36722679?v=4" width="100;" alt="amoeba1125"/>
            <br />
            <sub><b>Amoeba</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://github.com/majin1005">
            <img src="https://avatars.githubusercontent.com/u/72547221?v=4" width="100;" alt="majin1005"/>
            <br />
            <sub><b>Tam Yat Hei</b></sub>
        </a>
    </td></tr>
</table>
<!-- readme: collaborators,contributors -end -->

---

# 版權聲明
此專案僅在此網站(Github)發布並開源，若於其他網站下載，造成使用者財產損失，開發者將不負相關責任。

此外，本專案為完全免費開源，若使用者於其他網站花費購買此開源軟件，開發者將不負賠償責任。

最後，任何使用者皆可以使用此專案進行二次開發，但是禁止將此專案用於商業與營利用途，並且需要標示原創作者與作品來源。
