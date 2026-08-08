# SpiritVale Game State Bridge 設計

日期：2026-08-08  
分支：`feature/game-state-bridge`

## 目標

建立一個獨立、唯讀的 BepInEx IL2CPP 外掛，從 SpiritVale 客戶端已持有的執行期物件取得：

- 目前地圖識別碼
- 本機玩家世界座標與生命狀態
- 客戶端已生成怪物的識別碼、世界座標、生命值與存活狀態
- 角色目前裝備，以及背包內裝備、神器與其他分類的數量

外掛只輸出遙測快照，不修改遊戲資料、不呼叫戰鬥或移動方法、不送遊戲網路封包，也不嘗試取得伺服器未同步到客戶端的資料。

## 已驗證的遊戲資料鏈

本機 `BepInEx/interop/Assembly-CSharp.dll` 已透過 Mono.Cecil 只讀檢查，確認目前版本包含：

- `App.Player`：本機 `PlayerController`
- `PlayerController.CharacterData.State.MapId`：目前角色的地圖識別碼
- `BaseUnitController.Position`：玩家及怪物的世界座標
- `BaseUnitController.Health.Health` / `MaxHealth`：單位生命值
- `MonsterController.MonsterId` / `ConfigId`：怪物執行期與設定識別碼
- `MonsterController.OnStartNetwork()` / `OnStopNetwork()`：客戶端怪物加入與離開的生命週期
- `CharacterData.Inventory`：完整背包分類字典
- `CharacterData.Equips` / `Artifacts`：目前角色裝備與神器

這些代理型別提供的是 IL2CPP 原生方法的 C# 呼叫入口；不使用固定指標、offset 或外部 `ReadProcessMemory`。

## 架構

### 1. `SpiritValeGameStateBridge` 外掛

新增獨立的 .NET 6 專案，參考本機：

- `BepInEx.Core.dll`
- `BepInEx.Unity.IL2CPP.dll`
- `0Harmony.dll`
- `Il2CppInterop.Runtime.dll`
- `BepInEx/interop/Assembly-CSharp.dll`
- 必要的 Unity interop 組件

外掛啟動時只掛載下列 Harmony patch：

- `MonsterController.OnStartNetwork` postfix：登記怪物
- `MonsterController.OnStopNetwork` prefix：移除怪物
- `PlayerController.Update` postfix：僅對 `App.Player` 節流執行資料快照

怪物清單使用執行期物件參考維護，不在每一幀呼叫 `FindObjectsOfType`。

### 2. 快照收集器

所有 Unity/IL2CPP 物件只在 Unity 主執行緒讀取。預設每 100 ms 建立一次戰鬥快照；背包和裝備資料每 1 秒更新一次並快取，避免高頻走訪大型字典。

每筆怪物資料在輸出前驗證：物件仍存在、生命元件可讀、位置為有限數值。單一壞物件只從該次快照略過，不中止整個外掛。

### 3. 本機 UDP 遙測

外掛將 UTF-8 JSON datagram 發送到 `127.0.0.1:48231`。UDP 是單向、非阻塞且無連線狀態；Python 未啟動時不影響遊戲。每個封包都是完整快照，遺失一包不需要重傳。

設定提供：

- `Enabled`
- `Host`，固定預設 `127.0.0.1`
- `Port`，預設 `48231`
- `SnapshotIntervalMs`，預設 `100`
- `InventoryIntervalMs`，預設 `1000`
- `DiagnosticLogging`，預設 `true`

不接受非 loopback 位址，避免意外把遊戲資料送到外部網路。

### 4. Python 診斷接收器

在 RicValeBot 新增獨立工具，使用 Python 標準函式庫 `socket` 接收 UDP 並驗證 schema。第一階段只輸出地圖、玩家座標、怪物數、最近怪物、背包與裝備摘要，不接入現有按鍵、滑鼠、走路或技能決策。

## 快照格式

```json
{
  "schema_version": 1,
  "sequence": 42,
  "captured_at_unix_ms": 1786123456789,
  "map_id": "stormreef_isle",
  "player": {
    "character_id": "character-42",
    "x": 12.5,
    "y": 0.0,
    "z": 38.2,
    "health": 900,
    "max_health": 1000
  },
  "monsters": [
    {
      "runtime_id": "monster-runtime-127",
      "config_id": "scrapfang",
      "x": 20.0,
      "y": 0.0,
      "z": 40.0,
      "health": 120,
      "max_health": 300,
      "is_alive": true
    }
  ],
  "inventory": {
    "equips": 12,
    "artifacts": 3,
    "cards": 8,
    "gems": 4,
    "junks": 15,
    "consumables": 6,
    "cosmetics": 2
  },
  "equipped_ids": ["stormplate-shoes"],
  "artifact_ids": ["drooping-bat"]
}
```

欄位取不到時使用 `null` 或空集合，不用猜測值。`schema_version` 改變時，Python 接收器必須拒絕未知 major schema。

## 錯誤處理與效能界線

- Harmony 目標不存在時記錄警告並停用該資料來源；其他來源繼續工作。
- 遊戲尚未登入、`App.Player == null` 時不輸出偽造玩家資料，只定期記錄等待狀態。
- UDP 序列化或傳送失敗時限速記錄，不得讓例外離開 patch。
- 收集器每次執行記錄耗時；診斷模式下每 10 秒輸出平均值與最大值。
- 第一階段目標是單次收集平均低於 2 ms；若超標，先降低背包更新頻率，不降低怪物生命週期正確性。

## 測試與驗收

### 自動測試

- Python schema parser 接受完整快照。
- 拒絕未知 schema、非有限座標及錯誤資料型別。
- 正確選出距玩家最近的存活怪物。
- UDP 接收器能忽略損壞 datagram，並繼續接收下一筆合法快照。
- C# 外掛可用本機 BepInEx/interop 組件完成 Release build。
- 既有 Python unittest 全部維持通過。

### 遊戲內唯讀驗收

1. 安裝 DLL 後確認 BepInEx 顯示 patch 掛載成功。
2. 登入不同地圖，確認 `map_id` 隨角色狀態更新。
3. 靠近、擊殺及離開怪物，確認怪物加入、生命降低及移除。
4. 開啟與關閉背包前後，確認背包摘要不依賴 UI 是否正在繪製。
5. 將輸出座標與遊戲畫面人工對照；第一階段不據此發送任何操作。

## 明確不在第一階段

- 不讓 Python 根據資料自動攻擊或走路。
- 不把世界座標轉換成滑鼠座標。
- 不修改角色、怪物、背包或裝備資料。
- 不攔截、偽造或重送 FishNet 封包。
- 不加入防偵測、隱藏 DLL 或繞過保護的功能。
