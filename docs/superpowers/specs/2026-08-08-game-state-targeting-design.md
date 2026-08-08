# Game-State Targeting and Distance-Band Design

日期：2026-08-08  
分支：`feature/game-state-bridge`

## 目標

把第一階段的唯讀遊戲狀態快照接入 RicValeBot 的目標選擇、滑鼠鎖敵、怪群計數與走路決策。目標來源必須由 YAML 明確選擇；原有 HSV 血條與地圖目標圖片完整保留為 `screen` 模式，但不與 `game_state` 模式同時運作。

## 設計原則

- 不保留舊設定格式的相容別名或隱式遷移。
- 不做自動 fallback。執行期間不會從 `game_state` 自動切回 `screen`。
- BepInEx 外掛仍然唯讀：只讀取客戶端已持有的狀態與 Unity 攝影機投影，不呼叫移動、戰鬥或網路封包方法。
- 目標來源、戰鬥決策與輸入輸出維持分離，既有技能冷卻和技能組不重寫。
- 先完成單一最近目標的端到端流程，再以同一份快照加入怪群判斷。

## 設定

`config.yaml` 與其他可直接啟動的設定檔使用下列新結構：

```yaml
targeting:
  mode: game_state  # game_state 或 screen

  game_state:
    host: 127.0.0.1
    port: 48231
    stale_after_ms: 500

    distance_band:
      near: 3.0
      far: 7.0

    crowd_radius: 10.0
```

規則：

- `mode` 只接受 `game_state` 或 `screen`。
- `host` 必須是 loopback IP。
- `stale_after_ms` 必須大於零。
- `near` 必須大於等於零，`far` 必須嚴格大於 `near`。
- `crowd_radius` 必須大於零。
- 怪群觸發數量、技能組與技能冷卻繼續使用既有 `crowd_combat` 設定。
- `screen` 模式繼續使用既有 `detection`、HSV、地圖 targets、中心圈與游標偏移設定。

## 橋接協定

協定升級為 schema version 2。每個怪物除了世界座標、血量與存活狀態之外，新增由目前 Unity 攝影機計算的唯讀投影：

- `viewport_x`、`viewport_y`：正規化畫面座標。
- `viewport_depth`：大於零表示位於攝影機前方。
- `view_x`：怪物相對攝影機的左右距離，正值為右。
- `view_z`：怪物相對攝影機的前後距離，正值為前。

外掛使用 Unity 既有的 `WorldToViewportPoint` 與 `InverseTransformPoint`，不在 Python 重新實作攝影機矩陣。若當幀找不到有效攝影機，該幀不發布快照，避免產生錯誤方向或游標位置。

## Python 接收器

新增一個只負責接收狀態的背景元件：

- 綁定設定中的 loopback UDP 位址。
- 持續解碼 schema version 2，原子性保存最新不可變快照。
- 主迴圈只讀取最新快照，不等待 socket，避免拖慢畫面迴圈。
- 以本機收到資料的單調時間判斷新鮮度，不依賴兩個程序的系統時鐘完全同步。
- 關閉程式時停止執行緒並關閉 socket。

只有 `targeting.mode: game_state` 才建立接收器。`screen` 模式不開啟 UDP socket。

## 目標選擇與畫面位置

`game_state` 模式從最新且未過期的快照中篩選：

1. `is_alive` 為真。
2. `health > 0`。
3. 世界座標為有限數字。

選擇玩家 XZ 平面世界距離最近的怪物。世界距離用於距離帶和怪群計算；投影位置用於滑鼠和中心目標技能：

- 當 `viewport_depth > 0` 且投影在 `[0, 1]` 範圍內，將正規化座標換算成遊戲視窗客戶區座標。
- Unity 的 viewport Y 軸由下往上，換算 Windows 游標座標時使用 `1 - viewport_y`。
- 既有 `pointer.offset_y` 繼續作為游標垂直微調。
- 怪物不在畫面內時仍可供走路決策使用，但不移動滑鼠，也不執行需要畫面目標的技能。

`screen` 模式完全沿用目前 `_detect_targets` 的 HSV 優先與地圖圖片次要規則。

## 可設定距離帶走路

以最近怪物和玩家的 XZ 平面距離決定目標導引：

- 距離大於 `far`：依怪物的 `view_x/view_z` 產生朝向怪物的 WASD。
- 距離小於 `near`：反轉相同方向，產生遠離怪物的 WASD。
- 距離位於閉區間 `[near, far]`：不施加目標導引，交回既有 random 走路控制器。
- 快照過期或不存在：立即移除遊戲狀態導引；不切換 HSV，也不沿用過期方向。

目標導引優先於 random 走路，但不改寫路線播放、登入恢復、死亡恢復與傳送流程的既有輸入所有權。控制流程不持有永久按鍵；每次決策只透過既有 `MovementInput` 更新目前 WASD 集合。

## 怪群行為

以玩家為圓心、`crowd_radius` 為半徑，計算範圍內存活怪物：

- 數量交給既有 `CrowdSkillGroup`，沿用 `crowd_combat.min_targets` 與技能冷卻。
- 達到怪群門檻且啟用躲避時，計算範圍內怪物的世界座標中心，再用攝影機相對方向產生遠離怪群中心的 WASD。
- 怪群躲避優先於單一目標距離帶；技能施放與走路仍由各自控制器獨立執行。

## 模式切換行為

模式只在程式啟動時從 YAML 載入：

- `game_state`：不執行 HSV 或地圖目標圖片掃描；畫面擷取仍可供登入、死亡、傳送等 UI 狀態辨識使用。
- `screen`：不開啟遊戲狀態 UDP 接收器；戰鬥與走路維持目前行為。
- 修改 YAML 後需重新啟動程式，不實作執行中熱切換。

## 錯誤與診斷

- 設定錯誤在啟動時直接拒絕執行並指出欄位。
- UDP 封包格式錯誤時丟棄該封包，保留上一份仍未過期的有效快照。
- schema 不相符時不做相容解析。
- 診斷 log 只記錄狀態變更：接收器啟動、資料由新鮮轉過期、選擇的 runtime target 改變、距離帶區段改變、怪群進入或離開門檻。
- 不逐封包或逐幀輸出，避免 I/O 影響效能。

## 測試與驗收

### 自動測試

- schema version 2 的 C# 序列化與 Python 解碼一致。
- 攝影機投影欄位拒絕 NaN、Infinity 與缺失值。
- 接收器不阻塞主執行緒，並能判斷快照新鮮／過期。
- 最近存活怪物選擇正確。
- viewport 到視窗座標的 Y 軸反轉正確。
- 距離小於 `near`、位於距離帶、超過 `far` 的三種走路結果正確。
- 怪群中心與遠離方向正確。
- `screen` 模式不建立 UDP 接收器；`game_state` 模式不執行戰鬥目標畫面掃描。
- 完整 Python 測試、C# protocol tests、Release build 全部通過。

### 遊戲內驗收

- 監聽器持續接收 schema version 2，沒有 BepInEx 快照錯誤。
- 怪物在畫面內移動時，滑鼠位置跟隨投影而非舊血條位置。
- 遠距離會靠近、近距離會遠離、中間距離維持既有 random 走路。
- 三隻以上近距離怪物能觸發既有怪群技能並往怪群中心反方向走。
- 切換成 `screen` 並重啟後，原 HSV 血條功能仍可使用且不占用 UDP 連接埠。

## 不在本階段範圍

- 不讀取或掃描 SpiritVale 程序記憶體。
- 不修改遊戲內狀態或直接呼叫遊戲移動／攻擊方法。
- 不建立路徑尋路、障礙物網格或自動地圖探索。
- 不使用背包資料自動出售、丟棄或裝備物品。
- 不支援兩種目標來源融合或自動 fallback。
