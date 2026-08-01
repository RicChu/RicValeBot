# RicValeBot

以 Python 撰寫的背景畫面偵測與鍵盤／滑鼠自動化專題。程式會擷取指定遊戲視窗，在中央偵測區域內辨識血條，並依規則執行滑鼠、技能、群怪應對與走路動作。

> 請只在你擁有權限的遊戲、測試或展示環境使用，並自行確認目標服務的使用規範。

## 目前功能

### 血條 HSV 偵測

- 使用 OpenCV HSV 色域辨識紅／白／黑組成的水平血條。
- 要求固定尺寸範圍、長條比例、黑色邊框、連續水平色帶與色域覆蓋率，降低灰色 UI 或畫面特效誤判。
- 支援兩條可獨立啟用的偵測路徑：
  - `inner_band_enabled`：從紅／白內條加上上下黑邊辨識一般血量。
  - `black_residual_enabled`：從殘血或接近全黑的黑框辨識低血量血條。
- `low_colour_trigger_ratio: 0.40` 用來填補約 30%～60% 血量的偵測交接區間。
- 可同時回傳多個目標；後續攻擊會優先選擇最靠近遊戲畫面中心的目標。

### 目標與技能動作

- 任務 1：偵測到目標後，滑鼠移到血條中心上方 50 px，並按 `3`。
- 中心目標：同一個 HSV 目標進入遊戲視窗中心半徑 350 px 內時，每 0.5 秒可按一次 `2`。
- 群怪技能：當同時偵測到的目標數達 `crowd_combat.min_targets` 時，依優先順序施放 `F2 → F3 → F4`。
  - 每個群怪技能冷卻 6 秒。
  - 技能間最短間隔 0.33 秒。
- 排程技能：可在 `skill_queue.schedules` 設定週期性技能，例如目前設定的 `5`、`6` 與 `V`。

### 走路與怪群避讓

- 支援兩種模式：
  - `random`：在程式維護的安全矩形內隨機移動。
  - `route`：透過小地圖白色標記與錄製地圖，在 A／B／C 等路點間走動；地圖錄製功能可選擇啟用。
- 群怪出現時，隨機走路會先避開朝怪群中心移動的方向。
- 若避讓規則排除所有首選方向，會退回選擇仍在邊界內的方向，不會刻意原地停止。
- 現行保守隨機設定：

```yaml
walking:
  mode: random
  step_distance: 100
  speed_px_per_sec: 300
  boundary_x: 1100
  boundary_y: 600
```

這代表每步約持鍵 0.33 秒，程式維護的安全範圍為起始點 X ±550、Y ±300。這是估算邊界；若需要真實地圖座標回授，請改用 `route` 與地圖錄製模式。

### 獨立輸入控制

- `MovementInput` 只管理 WASD 的按住與放開。
- `SkillTapQueue` 只管理技能點按。
- 技能送出不會重新送出 WASD 狀態，避免群怪技能或排程技能導致移動鍵卡住。

### 其他

- 以 `mss` 擷取遊戲視窗；可設定視窗標題與擷取失敗時的桌面備援。
- `center_roi` 限制偵測於畫面中央區域，減少 HSV 計算量與 UI 誤判。
- `runtime.log_mode` 支援：
  - `off`：只保留錯誤。
  - `events`：記錄實際動作、群怪技能與避讓事件。
  - `diagnostic`：額外記錄偵測時間統計。
- `save_debug_frame` 可選擇儲存標註後的偵測畫面，預設關閉。

## 安裝

需求：Windows、Python 3.11 以上。

```powershell
cd C:\Users\User\Desktop\RicValeBot
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 啟動

先確認 `config.yaml` 中的 `target_window_title` 與實際遊戲視窗標題相符，再執行：

```powershell
cd C:\Users\User\Desktop\RicValeBot
.\.venv\Scripts\python.exe main.py
```

建議第一次先將 `action.dry_run` 設為 `true`，確認偵測與日誌正常後，再改為 `false` 啟用真實鍵盤與滑鼠操作。

## 常用設定

主要設定都在 `config.yaml`：

```yaml
action:
  key: "3"
  dry_run: false

pointer:
  offset_y: -50

center_target:
  radius_px: 350
  key: "2"
  repeat_interval_ms: 500

crowd_combat:
  enabled: true
  keys: ["F2", "F3", "F4"]
  min_targets: 2
```

修改 YAML 後，請停止程式再重新啟動，設定才會重新載入。

## 地圖錄製與路徑模式

錄製小地圖資料：

```powershell
.\.venv\Scripts\python.exe record_map.py
```

錄製完成後，在 `walking` 區段設定：

```yaml
walking:
  mode: route
  route:
    map_recording:
      enabled: true
      manifest_path: maps/underground/manifest.yaml
```

路點座標、迷你地圖大小與到點範圍可在同一個 `route` 區段調整。

## 測試

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

目前測試涵蓋 HSV 血條辨識、中心目標、群怪技能優先序、避怪走路、路徑導航、地圖錄製、獨立輸入與設定載入。

## 專案結構

```text
RicValeBot/
├─ config.yaml                  # 行為、偵測與按鍵設定
├─ main.py                      # 啟動入口
├─ record_map.py                # 地圖錄製入口
├─ assets/                      # 影像範例與中心目標圖片
├─ maps/                        # 錄製的小地圖資料
├─ src/screen_automation/       # 偵測、輸入、走路與導航模組
└─ tests/                       # unittest 測試
```

## Git

專案使用 `main` 分支。常用指令：

```powershell
git status
git add .
git commit -m "描述這次修改"
git push origin main
```

## 斷線登入回復

`login_recovery` 只會在辨識到「連接」或「遊玩角色」按鈕時啟用，因此正常遊戲畫面不會被點擊。登入階段啟用後，程式會先釋放 WASD、清空尚未施放的技能，再依序完成一次選擇與一次確認：

1. 選取 `server.name` 對應的伺服器，再按「連接」。
2. 選取 `character.name` 對應的角色，再按「遊玩角色」。

```yaml
login_recovery:
  enabled: true
  threshold: 0.82
  action_delay_ms: 700
  server:
    name: "SEA"
    template_path: assets/login/server/sea.png
    connect_template_path: assets/login/server/connect.png
  character:
    name: "滴滴殺手"
    template_path: assets/login/character/didi_killer.png
    play_template_path: assets/login/character/play.png
```

`name` 是方便辨識設定用途的標籤；實際畫面比對使用 `template_path` 的裁圖。更換伺服器或角色時，請擷取其名稱／按鈕圖片放入 `assets/login/`，再改掉相應路徑。尚未提供範本的斷線提示或錯誤視窗會被視為未知畫面，程式不會點擊。
