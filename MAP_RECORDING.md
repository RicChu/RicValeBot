# 全域迷你地圖錄製

固定的迷你地圖像素會隨角色移動而改變。這個功能先將有重疊的迷你地圖畫面拼成一張全域地圖，再用它換算角色與路點的位置。

## 錄製

手動移動角色，讓相鄰迷你地圖畫面有足夠的道路或地形重疊；錄製指令不會送出任何鍵盤或滑鼠輸入：

```powershell
.\.venv\Scripts\python.exe record_map.py --seconds 60 --interval-ms 250
```

輸出資料夾 `maps\<時間>\` 會有：

- `recorded_map.png`：拼接後的全域地圖。
- `manifest.yaml`：定位程式使用的影格位置資料。

## 啟用路線

將 `config.yaml` 改為：

```yaml
walking:
  mode: route
  route:
    map_recording:
      enabled: true
      manifest_path: maps/20260731_120000/manifest.yaml
```

此時 A/B/C 的 `x`、`y` 改填 `recorded_map.png` 上量得的像素位置。若即時迷你地圖無法定位，程式會放開 WASD，不會繼續盲走。

錄製結果僅適用於同一張地圖、相同遊戲 UI 比例與相近迷你地圖縮放。
