# SpiritVale Game State Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only BepInEx IL2CPP plugin that publishes current map, player, monster, inventory, and equipment snapshots to a diagnostic Python receiver over loopback UDP.

**Architecture:** Harmony patches register and unregister `MonsterController` instances and throttle snapshot collection from the local `PlayerController.Update` path. Unity and IL2CPP objects are read only on the Unity main thread, converted to plain DTOs, serialized as schema-versioned JSON, and sent as complete UDP snapshots to `127.0.0.1`. Python owns schema validation and diagnostics but does not connect this data to automation actions in phase one.

**Tech Stack:** C#/.NET 6, BepInEx 6 IL2CPP, Harmony, Il2CppInterop, `System.Text.Json`, UDP loopback, Python 3.13 standard library, `unittest`.

## Global Constraints

- Read only client-visible runtime objects; do not mutate game state, call movement/combat methods, or send FishNet game packets.
- Do not implement fixed pointers, offsets, `ReadProcessMemory`, anti-detection, DLL hiding, or protection bypasses.
- Only send telemetry to a loopback address; reject non-loopback configuration.
- Default snapshot interval is 100 ms and inventory refresh interval is 1000 ms.
- All Unity/IL2CPP access remains on the Unity main thread.
- Phase one never feeds game-state snapshots into existing mouse, keyboard, walking, or skill decisions.

---

### Task 1: Python Snapshot Schema

**Files:**
- Create: `src/screen_automation/game_state.py`
- Create: `tests/test_game_state.py`

**Interfaces:**
- Produces: `decode_game_state(payload: bytes) -> GameStateSnapshot`
- Produces: `nearest_living_monster(snapshot: GameStateSnapshot) -> MonsterSnapshot | None`
- Produces immutable dataclasses `Position3D`, `PlayerSnapshot`, `MonsterSnapshot`, `InventorySummary`, and `GameStateSnapshot`.

- [ ] **Step 1: Write the failing schema tests**

Add tests that pass a complete schema-v1 JSON payload, reject `schema_version=2`, reject `NaN`/infinite coordinates, and choose the nearest monster with `health > 0`.

```python
def test_decodes_schema_v1_snapshot(self):
    snapshot = decode_game_state(valid_payload())
    self.assertEqual(snapshot.map_id, "stormreef_isle")
    self.assertEqual(snapshot.inventory.equips, 12)
    self.assertEqual(len(snapshot.monsters), 2)

def test_rejects_unknown_schema(self):
    with self.assertRaisesRegex(ValueError, "schema_version"):
        decode_game_state(b'{"schema_version":2}')
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe -m unittest tests.test_game_state -v
```

Expected: import failure because `screen_automation.game_state` does not exist.

- [ ] **Step 3: Implement immutable validated DTOs**

Parse JSON explicitly rather than splatting arbitrary dictionaries into dataclasses. Convert numeric values to `float`/`int`, require schema version 1, require finite coordinates with `math.isfinite`, preserve nullable `map_id`, and normalize missing lists to empty tuples.

```python
SUPPORTED_SCHEMA_VERSION = 1

def decode_game_state(payload: bytes) -> GameStateSnapshot:
    raw = json.loads(payload.decode("utf-8"))
    if raw.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")
    return _decode_snapshot(raw)
```

- [ ] **Step 4: Verify GREEN and regression suite**

Run the focused test, then `python -m unittest discover -v`. Expected: all new tests and the existing 115 tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add game state snapshot schema`.

---

### Task 2: Loopback UDP Diagnostic Receiver

**Files:**
- Modify: `src/screen_automation/game_state.py`
- Create: `tools/game_state_listener.py`
- Modify: `tests/test_game_state.py`

**Interfaces:**
- Produces: `receive_game_state(sock: socket.socket) -> GameStateSnapshot`
- Consumes: `decode_game_state(payload: bytes)` from Task 1.

- [ ] **Step 1: Write a failing real-socket test**

Bind a UDP receiver to `127.0.0.1:0`, send one malformed datagram and then one valid datagram from a second real socket, and assert that `receive_game_state` skips the malformed datagram and returns the valid snapshot. Set a one-second timeout so a regression cannot hang the suite.

- [ ] **Step 2: Verify RED**

Run the focused test. Expected: import failure for `receive_game_state`.

- [ ] **Step 3: Implement the receiver and CLI**

`receive_game_state` loops until `decode_game_state` returns a valid snapshot, ignoring `UnicodeDecodeError`, `json.JSONDecodeError`, `KeyError`, `TypeError`, and `ValueError`. The CLI accepts `--host` and `--port`, rejects non-loopback hosts, and prints one concise line containing sequence, map, player position, living monster count, nearest monster, and inventory counts.

- [ ] **Step 4: Verify GREEN and full Python suite**

Run focused and full unittest commands. Expected: all tests pass without warnings.

- [ ] **Step 5: Commit**

Commit message: `feat: add UDP game state listener`.

---

### Task 3: C# Protocol and Loopback Publisher

**Files:**
- Create: `integrations/SpiritValeGameStateBridge/SpiritValeGameStateBridge.csproj`
- Create: `integrations/SpiritValeGameStateBridge/BridgeProtocol.cs`
- Create: `integrations/SpiritValeGameStateBridge/UdpPublisher.cs`
- Create: `integrations/SpiritValeGameStateBridge.ProtocolTests/SpiritValeGameStateBridge.ProtocolTests.csproj`
- Create: `integrations/SpiritValeGameStateBridge.ProtocolTests/Program.cs`

**Interfaces:**
- Produces: `BridgeProtocol.Serialize(BridgeSnapshot snapshot) -> byte[]`
- Produces: `UdpPublisher(string host, int port)` and `Publish(BridgeSnapshot snapshot)`.
- JSON property names exactly match Task 1's schema.

- [ ] **Step 1: Write the dependency-free C# self-test first**

The console self-test creates a snapshot, calls `BridgeProtocol.Serialize`, parses it with `JsonDocument`, and exits nonzero unless `schema_version`, `map_id`, player coordinates, monster values, inventory values, and arrays match. It also asserts that constructing `UdpPublisher` with `8.8.8.8` throws `ArgumentException`.

- [ ] **Step 2: Verify RED**

Run:

```powershell
dotnet run --project integrations/SpiritValeGameStateBridge.ProtocolTests -c Release
```

Expected: compilation fails because `BridgeProtocol.cs` and `UdpPublisher.cs` do not exist.

- [ ] **Step 3: Implement protocol and publisher**

Use plain DTO classes with `[JsonPropertyName]`, `JsonSerializerOptions` configured without indentation, `UdpClient`, and `IPAddress.IsLoopback`. `Publish` sends one complete UTF-8 JSON datagram and never owns game objects.

- [ ] **Step 4: Verify GREEN and Python compatibility**

Run the C# self-test. Save its emitted JSON fixture to a temporary file and pass the bytes through Task 1's `decode_game_state`; expected: both consumers accept the same schema.

- [ ] **Step 5: Commit**

Commit message: `feat: add game state bridge protocol`.

---

### Task 4: BepInEx IL2CPP Read-Only Collector

**Files:**
- Create: `integrations/SpiritValeGameStateBridge/Plugin.cs`
- Create: `integrations/SpiritValeGameStateBridge/MonsterRegistry.cs`
- Create: `integrations/SpiritValeGameStateBridge/GameStateCollector.cs`
- Modify: `integrations/SpiritValeGameStateBridge/SpiritValeGameStateBridge.csproj`

**Interfaces:**
- Consumes: `BridgeSnapshot` and `UdpPublisher` from Task 3.
- Produces Harmony postfix/prefix entry points for `MonsterController.OnStartNetwork`, `MonsterController.OnStopNetwork`, and local `PlayerController.Update`.
- Produces: `GameStateCollector.TryCapture(PlayerController player, long sequence, out BridgeSnapshot snapshot)`.

- [ ] **Step 1: Establish the failing plugin build**

Add the game-reference entries to the csproj and run `dotnet build -c Release`. Expected: build fails because plugin entry points and collector files are not yet defined.

- [ ] **Step 2: Implement plugin configuration and safe patching**

Create a `BasePlugin` with settings `Enabled`, `Host`, `Port`, `SnapshotIntervalMs`, `InventoryIntervalMs`, and `DiagnosticLogging`. Resolve patch targets using `AccessTools.Method`, log a warning for a missing target, and wrap every Harmony callback so no exception escapes into the game loop.

- [ ] **Step 3: Implement event-driven monster registry**

Use a private `HashSet<MonsterController>`. Register on `OnStartNetwork` postfix and unregister on `OnStopNetwork` prefix. Snapshot iteration copies the set first and prunes null/destroyed entries; it never calls `FindObjectsOfType`.

- [ ] **Step 4: Implement throttled main-thread collection**

Only collect when `ReferenceEquals(__instance, App.Player)` or IL2CPP object identity matches the local player. Read:

```text
player.CharacterData.State.MapId
player.Position
player.Health.Health / MaxHealth
monster.GetInstanceID(), MonsterId, ConfigId, Position, Health
player.CharacterData.Inventory.{Equips,Artifacts,Cards,Gems,Junks,Consumables,Cosmetics}.Count
player.CharacterData.Equips[*].Equip.Id
player.CharacterData.Artifacts[*].Id
```

Throttle combat snapshots to 100 ms and inventory refresh to 1000 ms. Reject non-finite positions and skip only the invalid entity.

- [ ] **Step 5: Build and inspect dependencies**

Run Release build against the installed SpiritVale `BepInEx/core` and `BepInEx/interop` assemblies. Inspect the output folder and ensure game assemblies are not copied beside the plugin DLL.

- [ ] **Step 6: Commit**

Commit message: `feat: collect read-only SpiritVale game state`.

---

### Task 5: Build, Install, and Diagnostic Documentation

**Files:**
- Create: `tools/build_game_state_bridge.ps1`
- Create: `tools/install_game_state_bridge.ps1`
- Modify: `README.md`
- Modify: `.gitignore`

**Interfaces:**
- Build script accepts `-GameDir` and forwards it as an MSBuild property.
- Install script copies only `SpiritValeGameStateBridge.dll` into `BepInEx/plugins/SpiritValeGameStateBridge` after a successful build.

- [ ] **Step 1: Add deterministic scripts**

Validate that `SpiritVale.exe`, `BepInEx/core`, and `BepInEx/interop/Assembly-CSharp.dll` exist before build. Fail with a clear message instead of silently using a wrong path. Never overwrite unrelated plugin files.

- [ ] **Step 2: Document operation**

README commands must cover build, install, listener startup, expected BepInEx log entries, expected listener output, configuration path, uninstalling by removing only the bridge plugin directory, and the phase-one read-only boundary.

- [ ] **Step 3: Run complete verification**

Run:

```powershell
C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe -m unittest discover -v
dotnet run --project integrations/SpiritValeGameStateBridge.ProtocolTests -c Release
dotnet build integrations/SpiritValeGameStateBridge/SpiritValeGameStateBridge.csproj -c Release
git diff --check
```

Expected: Python suite reports zero failures, protocol self-test exits 0, plugin build exits 0, and diff check has no output.

- [ ] **Step 4: Static read-only audit**

Search the integration source for `ReadProcessMemory`, pointer/offset APIs, FishNet RPC writer calls, input APIs, and setters on game objects. Expected: no prohibited operation is present; configuration and DTO property setters are allowed.

- [ ] **Step 5: Commit**

Commit message: `docs: add game state bridge workflow`.

---

## Final Manual Validation Boundary

Automated completion includes build, protocol compatibility, regression tests, and static read-only audit. Actual map/monster/inventory values require launching SpiritVale and observing BepInEx plus the listener; do not claim runtime correctness until that manual in-game validation has been performed.
