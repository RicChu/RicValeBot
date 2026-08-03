# RicValeBot

## Combat skill groups and map-route delay

Each attack mode owns an ordered skill group. A trigger queues at most one skill: after `skill_interval_ms` has elapsed, it selects the first skill whose own `cooldown_ms` is complete. This lets a primary skill run every second and a secondary skill run while the primary skill is cooling down.

```yaml
action:
  skill_interval_ms: 20
  skills:
    - {key: "3", cooldown_ms: 20}

center_target:
  skill_interval_ms: 330
  skills:
    - {key: "2", cooldown_ms: 1000}
    - {key: "3", cooldown_ms: 2000}

crowd_combat:
  skill_interval_ms: 330
  skills:
    - {key: "F2", cooldown_ms: 6000}
    - {key: "F3", cooldown_ms: 6000}
    - {key: "F4", cooldown_ms: 6000}
```

For a scripted route, `route_start_delay_ms` starts counting only after the active map's arrival-minimap image is detected. Movement stays released during that delay.

```yaml
maps:
  the_forge:
    route_start_delay_ms: 1000
```

## Server-disconnect recovery

When the configured disconnect-confirmation dialog is visible, the bot stops movement and skills, clicks `確定` once, and waits for that dialog to close. Existing login recovery then continues with server and character selection.

```yaml
disconnect_recovery:
  enabled: true
  threshold: 0.82
  confirm_template_path: assets/disconnect/confirm.png
```

## Arrival-minimap wait and scripted patrol

When `walking.mode: scripted_route`, a program-driven town teleport waits until the active map's arrival minimap template is detected before replaying its `movement_script_path`. After the script reaches its final segment, the existing bounded random patrol starts automatically.

```yaml
maps:
  the_forge:
    arrival_minimap_threshold: 0.70
```

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
- 地圖鎖敵：當 HSV 沒有找到血條時，才會掃描目前地圖設定的目標範本；辨識成功後沿用任務 1 與中心目標動作。
- 群怪技能：當同時偵測到的目標數達 `crowd_combat.min_targets` 時，依優先順序施放 `F2 → F3 → F4`。
  - 每個群怪技能冷卻 6 秒。
  - 技能間最短間隔 0.33 秒。
- 排程技能：可在 `skill_queue.schedules` 設定週期性技能，例如目前設定的 `5`、`6` 與 `V`。

### 走路與怪群避讓

- 支援兩種模式：
  - `random`：在程式維護的安全矩形內隨機移動。
  - `route`：透過小地圖白色標記與錄製地圖，在 A／B／C 等路點間走動；地圖錄製功能可選擇啟用。
  - `scripted_route`：主城傳送完成後，重播該地圖錄製的 WASD 時間片段，不使用小地圖定位。
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
  avoid_movement_enabled: true
  keys: ["F2", "F3", "F4"]
  min_targets: 2
```

修改 YAML 後，請停止程式再重新啟動，設定才會重新載入。

## 地圖錄製與路徑模式

錄製小地圖資料：

```powershell
.\.venv\Scripts\python.exe record_map.py
```

錄製完成後，若要手動設定 A／B／C 路點，使用 `route` 模式：

```yaml
walking:
  mode: route
  route:
    map_recording:
      enabled: true
      manifest_path: maps/underground/manifest.yaml
```

路點座標、迷你地圖大小與到點範圍可在同一個 `route` 區段調整。

### WASD 路線錄製與重播

在遊戲內手動走一次安全路線，錄製實際按住的 WASD 組合與時間：

```powershell
cd C:\Users\User\Desktop\RicValeBot
.\.venv\Scripts\python.exe record_route.py --output assets\maps\the_forge\movement.yaml
```

聚焦遊戲後按 `F9` 開始錄製，手動走完路線後按 `F10` 儲存。工具不會送出任何按鍵，只讀取你實際按住的 WASD。

儲存後，在 `config.yaml` 設定：

```yaml
active_map: the_forge
maps:
  the_forge:
    movement_script_path: assets/maps/the_forge/movement.yaml

walking:
  mode: scripted_route
```

程式只會在自身完成主城傳送後啟動腳本；每段 WASD 會依錄製時間重播，結束後釋放全部移動鍵。此模式不使用小地圖、不執行 ORB 特徵比對，也不需要小地圖縮放。

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

## 主城傳送石

`town_teleport` 以右上角主城小地圖作為起點判斷。偵測到主城後會暫停走路、技能與 HSV，依序執行：`B` → 消耗品圖示 → 傳送石雙擊 → 傳送石確認 → 指定地圖縮圖 → 「傳送」按鈕。每一階段只有在下一個範本出現時才會前進；8 秒內未出現即停止，不會任意點擊。

傳送石確認畫面可設定多張備選圖片，任一張辨識成功就會點擊分數較高的位置：

```yaml
town_teleport:
  enabled: true
  threshold: 0.70
  action_delay_ms: 700
  stage_timeout_ms: 8000
  town_minimap_template_path: assets/teleport/city_minimap.png
  town_minimap_roi: [2200, 0, 360, 410]
  consumables_template_path: assets/teleport/consumables.png
  waystone_template_path: assets/teleport/waystone.png
  waystone_confirm_template_path: assets/teleport/waystone_confirm.png
  waystone_confirm_template_paths:
    - assets/teleport/waystone_confirm.png
    - assets/teleport/waystone_confirm2.png
  teleport_confirm_template_path: assets/teleport/teleport_confirm.png
  destination:
    name: demon_mouth
    template_path: assets/teleport/maps/demon_mouth.png
```

地圖相關資源統一放在 `assets/maps/<地圖名稱>/`，地圖相關設定統一放在 `active_map` 與 `maps`，切換地圖時只需要改 `active_map`：

```yaml
active_map: night_garden
maps:
  demon_mouth:
    target_template_paths: []
    movement_script_path: null
  night_garden:
    movement_script_path: null
```

未填寫時會自動使用：`teleport.png`、`targets/`、`movement.yaml`、`arrival_minimap.png`。例如 `the_forge` 會依序讀取 `assets/maps/the_forge/` 下對應資源。`target_template_paths: []`、`movement_script_path: null` 或 `arrival_minimap_template_path: null` 可個別停用預設功能。缺少 `targets/` 資料夾時只會停用範本鎖敵，不會阻止 HSV 偵測或程式啟動。

每張地圖可設定傳送縮圖、低優先鎖敵範本資料夾與 WASD 腳本。`movement_script_path: null` 表示該地圖傳送後不啟動腳本；HSV 血條偵測、技能與通用走路設定仍維持全域。`town_minimap_roi` 是目前 2560×1440 視窗的設定；若改變遊戲解析度，需重新裁小地圖並更新這個範圍。

若啟用小地圖縮放，傳送流程會在主城與戰鬥地圖依設定執行滾輪操作；可在 `config.yaml` 調整或關閉。

```yaml
minimap_zoom:
  enabled: true
  town_scroll_steps: 30
  combat_scroll_steps: 30
  combat_load_wait_ms: 5000
  interval_ms: 10
```

`combat_load_wait_ms` 是傳送離開主城後、開始縮放前的等待時間；等待時會釋放 WASD 並清空技能。`interval_ms` 是相鄰縮放事件的最小間隔；實際間隔也會受主迴圈的 `runtime.poll_interval_ms` 限制。乾跑模式只模擬縮放流程，不會送出 Ctrl 或滾輪輸入。

## 恢復後狀態確認技能

死亡復活、斷線回復與傳送石離開主城後，`combat_start` 會檢查左上角狀態圖示。圖示不存在時依序施放整組技能；整組結束等待 `verify_delay_ms` 後再次檢查，直到圖示出現才停止重試。

```yaml
combat_start:
  enabled: true
  skill_interval_ms: 330
  verify_delay_ms: 500
  status_template_path: assets/combat/combat_state_icon.png
  status_threshold: 0.85
  status_roi: [0, 0, 500, 350]
  skills:
    - key: "4"
    - key: "F2"
```

## 死亡回復

死亡回復與登入回復是獨立狀態。只要辨識到「在城鎮重生」按鈕，死亡回復就會取消正在進行的登入與傳送步驟、釋放 WASD、清空技能，再點擊一次重生。死亡視窗還在時不會重複點擊；視窗消失後，程式才重新依目前位置決定是否需要主城傳送。

```yaml
death_recovery:
  enabled: true
  threshold: 0.82
  town_respawn_template_path: assets/death/town_respawn.png
```
