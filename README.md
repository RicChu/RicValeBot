# PYTHON 畢業專題：背景畫面偵測與按鍵自動化

本專案是一個 Windows 上的 Python 專題骨架：持續擷取指定視窗、以 OpenCV 尋找範本圖片，偵測成功後對該視窗送出按鍵訊息。

> 僅請用於你擁有或已取得授權的軟體與測試環境。預設 `dry_run: true`，只會記錄動作、不會真的送鍵。

## 功能

- 指定視窗標題，自動取得目標視窗。
- 優先透過 Windows `PrintWindow` 截圖；視窗截圖失敗時可退回桌面擷取。
- OpenCV 模板比對，輸出最高相似度與位置。
- 游標移至圖案中心上方的可設定位置，並以可設定間隔重複送出按鍵。
- 偵測消失時立即停止送鍵；提供乾跑模式與偵錯截圖。

## 安裝

建議使用 Python 3.11+：

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 設定

1. 開啟 `config.yaml`。
2. 將 `target_window_title` 改為目標視窗標題中穩定的一段文字。
3. 把要尋找的小圖放入 `assets/target.png`，或改寫 `detection.template_path`。
4. 先維持 `action.dry_run: true` 測試；確認偵測位置與頻率正確後，才改成 `false`。實際移動游標時，目標視窗必須可見、且不能被遮住。

## 執行

```powershell
python main.py --config config.yaml
```

按 `Ctrl+C` 停止。加上 `--once` 可只檢測一次，適合校正範本與門檻：

```powershell
python main.py --once
```

## 重要限制

- `PrintWindow` 對部分 GPU 渲染或權限較高的程式可能得到黑畫面；專案會依設定退回到桌面擷取，這時目標視窗必須可見且未被遮住。
- 實際移動游標時，畫面上的目標視窗必須可見且未被遮住；這種模式無法完全在背景運作。
- `PostMessage` 並非所有程式都接受；特別是遊戲、系統管理員權限的程式與使用 DirectInput 的軟體。請不要嘗試繞過應用程式的安全、反自動化或存取限制。
- 請選擇辨識度高、大小固定的範本；必要時調低 `detection.threshold`（如 0.82）或設定 ROI。

## 專題可延伸方向

- 多範本／多動作規則。
- 紀錄偵測結果至 CSV 或 SQLite，製作準確率與延遲分析。
- 網頁儀表板顯示即時畫面與偵測框。
- 將模板比對替換為 YOLO 物件偵測模型。
