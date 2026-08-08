# Game-State Targeting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add an explicit game_state/screen targeting switch, configurable world-distance band, camera-projected mouse targeting, and world-coordinate crowd decisions without removing the existing HSV health-bar mode.

**Architecture:** Upgrade the read-only BepInEx snapshot to schema v2 with camera-relative and viewport fields. A dedicated Python UDP source owns the receiver thread and exposes only a fresh immutable snapshot; a pure targeting module converts that snapshot into mouse, distance-band, and crowd decisions. AutomationApp selects exactly one combat target source at startup and continues to use the existing MovementInput, SkillTapQueue, cooldown groups, and UI recovery flow.

**Tech Stack:** Python 3.13, standard-library socket/threading, PyYAML, OpenCV, pywin32, C#/.NET 6, BepInEx IL2CPP, UnityEngine APIs, unittest.

## Global Constraints

- Do not preserve backward compatibility. Remove obsolete paths instead of adding compatibility layers, fallbacks, or migrations.
- Choose the simplest implementation that fully meets the current requirements. Avoid speculative abstractions, configuration, and indirection.
- Grow the system in layers. Every task must end with a working and independently testable product.
- Keep protocol decoding, UDP lifecycle, pure targeting decisions, and Windows input ownership in separate modules.
- Use existing project and standard-library dependencies; add no package.
- The bridge remains read-only and loopback-only. Do not call game movement/combat methods or send game network packets.
- Do not automatically fall back between game_state and screen.
- Follow strict TDD for every production behavior: add one failing behavior test, run it and confirm the expected failure, then implement the minimum code.

---

### Task 1: Parse the explicit targeting mode and distance band

**Files:**
- Modify: src/screen_automation/config.py
- Modify: tests/test_config.py
- Modify: config.yaml
- Modify: config-didi.yaml

**Interfaces:**
- Produces: DistanceBandConfig(near: float, far: float).
- Produces: GameStateTargetingConfig(host: str, port: int, stale_after_ms: int, distance_band: DistanceBandConfig, crowd_radius: float).
- Produces: TargetingConfig(mode: str, game_state: GameStateTargetingConfig).
- Extends: AppConfig.targeting: TargetingConfig.

- [ ] **Step 1: Write the failing happy-path configuration test**

~~~python
def test_reads_explicit_game_state_targeting_and_distance_band(self) -> None:
    config = load_config(Path(__file__).parents[1] / "config.yaml")

    self.assertEqual(config.targeting.mode, "game_state")
    self.assertEqual(config.targeting.game_state.host, "127.0.0.1")
    self.assertEqual(config.targeting.game_state.port, 48_231)
    self.assertEqual(config.targeting.game_state.stale_after_ms, 500)
    self.assertEqual(config.targeting.game_state.distance_band.near, 3.0)
    self.assertEqual(config.targeting.game_state.distance_band.far, 7.0)
    self.assertEqual(config.targeting.game_state.crowd_radius, 10.0)
~~~

- [ ] **Step 2: Run the focused test and verify RED**

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest tests.test_config.ConfigTests.test_reads_explicit_game_state_targeting_and_distance_band -v
~~~

Expected: FAIL because AppConfig has no targeting field.

- [ ] **Step 3: Add the required dataclasses and parser**

~~~python
@dataclass(frozen=True)
class DistanceBandConfig:
    near: float
    far: float


@dataclass(frozen=True)
class GameStateTargetingConfig:
    host: str
    port: int
    stale_after_ms: int
    distance_band: DistanceBandConfig
    crowd_radius: float


@dataclass(frozen=True)
class TargetingConfig:
    mode: str
    game_state: GameStateTargetingConfig
~~~

Parse raw["targeting"] as required. Validate mode in {"game_state", "screen"}, an IP literal whose ipaddress.ip_address(host).is_loopback is true, 1 <= port <= 65535, positive staleness, 0 <= near < far, and positive crowd radius. Do not default a missing targeting section.

Add this structure to both executable YAML files. Use mode game_state in config.yaml and mode screen in config-didi.yaml:

~~~yaml
targeting:
  mode: game_state
  game_state:
    host: 127.0.0.1
    port: 48231
    stale_after_ms: 500
    distance_band: {near: 3.0, far: 7.0}
    crowd_radius: 10.0
~~~

- [ ] **Step 4: Run the focused test and verify GREEN**

Run Step 2. Expected: PASS.

- [ ] **Step 5: Add validation tests one at a time**

Use yaml.safe_load on config.yaml, change one literal value, write a temporary YAML, and assert unknown mode, near >= far, and non-loopback host each raise ValueError naming the invalid field. Run each new test before its validation and confirm RED, then add only that validation and confirm GREEN.

- [ ] **Step 6: Run all config tests and commit**

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest tests.test_config -v
git add src/screen_automation/config.py tests/test_config.py config.yaml config-didi.yaml
git commit -m "feat: configure game state targeting"
~~~

Expected: all configuration tests PASS before commit.

---

### Task 2: Upgrade the bridge and Python decoder to camera-aware schema v2

**Files:**
- Modify: integrations/SpiritValeGameStateBridge/BridgeProtocol.cs
- Modify: integrations/SpiritValeGameStateBridge/GameStateCollector.cs
- Modify: integrations/SpiritValeGameStateBridge/Plugin.cs
- Modify: integrations/SpiritValeGameStateBridge.ProtocolTests/Program.cs
- Modify: src/screen_automation/game_state.py
- Modify: tests/test_game_state.py

**Interfaces:**
- Extends C# and Python MonsterSnapshot with viewport_x, viewport_y, viewport_depth, view_x, and view_z floats.
- Changes SUPPORTED_SCHEMA_VERSION and emitted BridgeSnapshot.SchemaVersion to 2.
- Keeps decode_game_state(payload) and nearest_living_monster(snapshot) signatures.

- [ ] **Step 1: Write failing C# protocol assertions**

Set SchemaVersion to 2 and add these literal fields to the test monster:

~~~csharp
ViewportX = 0.75f,
ViewportY = 0.25f,
ViewportDepth = 12.0f,
ViewX = 4.0f,
ViewZ = 12.0f,
~~~

Assert schema_version equals 2, viewport_x equals 0.75, and view_z equals 12.0.

- [ ] **Step 2: Run C# protocol tests and verify RED**

~~~powershell
dotnet run --project integrations/SpiritValeGameStateBridge.ProtocolTests -c Release
~~~

Expected: compile failure because the five properties do not exist.

- [ ] **Step 3: Add schema v2 properties and collector projection**

Add five JsonPropertyName float properties to C# MonsterSnapshot. In TryCapture, require Camera.main and derive:

~~~csharp
var camera = Camera.main;
if (camera == null) return false;

var viewport = camera.WorldToViewportPoint(position);
var view = camera.transform.InverseTransformPoint(position);
~~~

Copy viewport.x/y/z and view.x/z into each monster snapshot. Emit schema 2 and bump the plugin version to 0.2.0.

- [ ] **Step 4: Run C# protocol tests and build; verify GREEN**

~~~powershell
dotnet run --project integrations/SpiritValeGameStateBridge.ProtocolTests -c Release
dotnet build integrations/SpiritValeGameStateBridge/SpiritValeGameStateBridge.csproj -c Release
~~~

Expected: both succeed with zero errors.

- [ ] **Step 5: Write failing Python schema v2 tests**

Update valid_snapshot_payload to schema 2 and the same five literal values. Assert all five decoded fields. In a separate test replace view_x with float("nan") and require ValueError containing view_x.

- [ ] **Step 6: Run Python tests and verify RED**

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest tests.test_game_state -v
~~~

Expected: FAIL because schema 2 and the fields are unsupported.

- [ ] **Step 7: Implement the Python schema v2 decoder and verify GREEN**

Add the fields to Python MonsterSnapshot, set SUPPORTED_SCHEMA_VERSION = 2, and parse each with _finite_number. Do not parse schema 1.

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest tests.test_game_state -v
dotnet run --project integrations/SpiritValeGameStateBridge.ProtocolTests -c Release
~~~

Expected: all tests PASS.

- [ ] **Step 8: Commit the protocol layer**

~~~powershell
git add integrations/SpiritValeGameStateBridge integrations/SpiritValeGameStateBridge.ProtocolTests src/screen_automation/game_state.py tests/test_game_state.py
git commit -m "feat: add camera projection to game state"
~~~

---

### Task 3: Receive fresh snapshots without blocking the automation loop

**Files:**
- Create: src/screen_automation/game_state_source.py
- Create: tests/test_game_state_source.py

**Interfaces:**
- Produces GameStateSource(host, port, stale_after_ms, clock=time.monotonic).
- Produces start(), latest(now=None), stop(), and address.
- start and stop are idempotent.

- [ ] **Step 1: Write a failing real-UDP freshness test**

Use a real loopback sender and ephemeral receiver port:

~~~python
def test_returns_received_snapshot_until_it_becomes_stale(self) -> None:
    clock = FakeClock(10.0)
    source = GameStateSource("127.0.0.1", 0, 500, clock)
    source.start()
    try:
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender.sendto(encode(valid_snapshot_payload()), source.address)
        wait_until(lambda: source.latest() is not None)
        self.assertEqual(source.latest().sequence, 42)
        clock.now = 10.501
        self.assertIsNone(source.latest())
    finally:
        source.stop()
        sender.close()
~~~

FakeClock and bounded wait_until stay in the test module.

- [ ] **Step 2: Run the focused test and verify RED**

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest tests.test_game_state_source -v
~~~

Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement the smallest source**

Own one UDP socket and daemon thread. Use a 100 ms socket timeout so stop joins promptly. The loop receives a datagram, calls decode_game_state, and atomically stores (snapshot, clock()) under threading.Lock. Ignore malformed payloads. latest returns None when absent or when now - received_at exceeds stale_after_ms / 1000.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run Step 2. Expected: PASS.

- [ ] **Step 5: Add lifecycle tests one at a time**

Add one test proving a malformed datagram does not replace seq 42, and another proving stop releases the UDP port so a new socket can bind it. Confirm RED before each missing behavior, then GREEN.

- [ ] **Step 6: Run source/protocol tests and commit**

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest tests.test_game_state tests.test_game_state_source -v
git add src/screen_automation/game_state_source.py tests/test_game_state_source.py
git commit -m "feat: receive fresh game state snapshots"
~~~

---

### Task 4: Convert world state into pure target, distance-band, and crowd decisions

**Files:**
- Create: src/screen_automation/game_state_targeting.py
- Create: tests/test_game_state_targeting.py

**Interfaces:**
- Produces immutable GameStateDecision(target, target_distance, target_client_position, band, movement_keys, crowd_count, crowd_avoidance).
- Produces decide_game_state(snapshot, frame_width, frame_height, near, far, crowd_radius, crowd_min_targets, avoid_crowd).
- band is "near", "inside", or "far".

- [ ] **Step 1: Write failing target/projection tests**

A nearer monster has viewport (0.75, 0.25, 12.0) in a 1000 x 800 frame:

~~~python
decision = decide_game_state(snapshot, 1000, 800, 3.0, 7.0, 10.0, 3, True)
self.assertEqual(decision.target.runtime_id, "near-monster")
self.assertEqual(decision.target_client_position, (750, 600))
~~~

Add a negative viewport_depth case: the target remains selected for movement but target_client_position is None.

- [ ] **Step 2: Run tests and verify RED**

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest tests.test_game_state_targeting -v
~~~

Expected: import failure.

- [ ] **Step 3: Implement selection and viewport conversion**

Reuse nearest_living_monster. Convert Unity bottom-up viewport Y to top-down client Y:

~~~python
x = round(monster.viewport_x * frame_width)
y = round((1.0 - monster.viewport_y) * frame_height)
~~~

Return no client position unless depth is positive and normalized X/Y are both in [0, 1].

- [ ] **Step 4: Verify GREEN, then write the failing three-zone tests**

Use view_x=4 and view_z=8 with hand-calculated XZ distances 2, 5, and 8. Assert:

~~~python
self.assertEqual(near_decision.movement_keys, ("A", "S"))
self.assertIsNone(inside_decision.movement_keys)
self.assertEqual(far_decision.movement_keys, ("D", "W"))
~~~

- [ ] **Step 5: Implement band movement and verify GREEN**

Far uses signs of view_x/view_z; near inverts them. Ignore a component below 25% of the larger horizontal component so tiny noise does not force diagonals. Preserve key order horizontal then vertical. Inside returns None for the random walker.

- [ ] **Step 6: Add failing crowd tests**

Use three living monsters within 10 world units and one outside. Their average view_x/view_z is positive. Assert crowd_count is 3 and crowd_avoidance is ("A", "S"). Add a below-threshold case that yields None.

- [ ] **Step 7: Implement crowd decision and verify GREEN**

Count only living monsters within crowd_radius in player XZ space. At the threshold, average their camera-relative view_x/view_z and invert the direction. Crowd avoidance stays separate so app priority is explicit.

- [ ] **Step 8: Run tests and commit**

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest tests.test_game_state_targeting -v
git add src/screen_automation/game_state_targeting.py tests/test_game_state_targeting.py
git commit -m "feat: decide world distance targeting"
~~~

---

### Task 5: Share direct screen-position targeting without changing cooldowns

**Files:**
- Modify: src/screen_automation/pointer.py
- Modify: src/screen_automation/app.py
- Modify: tests/test_pointer.py
- Modify: tests/test_app_logging.py

**Interfaces:**
- Produces move_cursor_to_screen_position(position).
- Changes private app method to _handle_task_one(cursor_position, now).
- Keeps all task and center skill cooldown behavior unchanged.

- [ ] **Step 1: Write the failing pointer behavior test**

Patch win32api.SetCursorPos, call move_cursor_to_screen_position((321, 654)), assert the same tuple is returned and Windows receives that exact tuple.

- [ ] **Step 2: Run test and verify RED**

Expected: import failure for move_cursor_to_screen_position.

- [ ] **Step 3: Add the minimal function and verify GREEN**

~~~python
def move_cursor_to_screen_position(position: tuple[int, int]) -> tuple[int, int]:
    win32api.SetCursorPos(position)
    return position
~~~

- [ ] **Step 4: Write a failing cooldown-independent app test**

Update the existing pointer tracking test to call _handle_task_one((50, 40), now) twice, patch the direct-position function, assert two cursor moves, and inspect the real skill queue for only cooldown-permitted taps.

- [ ] **Step 5: Refactor the private method and verify GREEN**

Remove WindowInfo and DetectionResult from _handle_task_one. Move the supplied absolute cursor position directly, then run the unchanged PrioritySkillGroup. The screen-mode caller computes image_hover_position first.

- [ ] **Step 6: Run tests and commit**

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest tests.test_pointer tests.test_app_logging -v
git add src/screen_automation/pointer.py src/screen_automation/app.py tests/test_pointer.py tests/test_app_logging.py
git commit -m "refactor: target direct screen positions"
~~~

---

### Task 6: Select exactly one combat target source in AutomationApp

**Files:**
- Modify: src/screen_automation/app.py
- Modify: tests/test_app_logging.py
- Modify: tests/test_input_coordinator.py

**Interfaces:**
- Adds AutomationApp.game_state_source: GameStateSource | None.
- Adds _game_state_decision(frame_width, frame_height, now).
- Extracts current screen combat block to _process_screen_combat without behavioral change.
- Adds _process_game_state_combat for the new source.

- [ ] **Step 1: Write failing mode-isolation tests**

For game_state mode, use a fake source with a valid snapshot and an HSV detector that raises if called; assert the game-state runtime ID is selected. For screen mode, use a source that raises if latest is called and assert _detect_targets returns the HSV target. The fakes include every method the branch calls.

- [ ] **Step 2: Run focused tests and verify RED**

Expected: fail because mode selection and _game_state_decision do not exist.

- [ ] **Step 3: Construct only the selected source**

~~~python
self.game_state_source = (
    GameStateSource(
        config.targeting.game_state.host,
        config.targeting.game_state.port,
        config.targeting.game_state.stale_after_ms,
    )
    if config.targeting.mode == "game_state"
    else None
)
~~~

Construct detector, negative_detector, map_target_detector, and hsv_detector only in screen mode. Login, disconnect, death, teleport, combat-status, and minimap detectors remain independent.

- [ ] **Step 4: Add source lifecycle**

Start the source before the run loop and stop it in AutomationApp.stop. If port 48231 is already owned, raise a clear RuntimeError instructing the operator to close tools/game_state_listener.py. Never switch modes.

- [ ] **Step 5: Write failing app behavior tests separately**

Add one test per observable behavior:

- Visible game-state target moves the cursor and queues the existing task skill.
- Projected target inside center radius uses the existing center skill group.
- World-radius crowd_count drives the existing crowd skill group.
- Crowd avoidance overrides a single-target near/far movement.
- Inside band leaves the random walker in control.
- A stale snapshot releases previously held game-state guidance.

Use literal frame/window sizes and real GameStateDecision objects. Check MovementInput.held via patched low-level post_key_state and inspect the real SkillTapQueue queue.

- [ ] **Step 6: Implement the two explicit branches**

After existing UI recovery and teleport gates:

~~~python
if self.config.targeting.mode == "game_state":
    decision = self._game_state_decision(frame.shape[1], frame.shape[0], now)
    self._process_game_state_combat(window, frame, now, decision)
else:
    self._process_screen_combat(window, frame, now)
~~~

The game-state branch must:

1. Convert client projection to absolute Windows coordinates and add pointer.offset_y.
2. Move the cursor and run task-one skills only for a visible target.
3. Use projected client distance for existing center_target.radius_px.
4. Pass crowd_count to CombatController.
5. Apply movement priority: active scripted route/navigation owner, crowd avoidance, near/far keys, then random walker for inside/no guidance.
6. Track whether held keys came from game-state guidance and release them when the snapshot becomes stale.
7. Process SkillTapQueue independently from movement.
8. Log only transitions: fresh/stale source, runtime target ID, distance-band state, and crowd threshold entry/exit. Add one test that repeats the same decision twice and asserts no duplicate event is emitted.

Extract the old inline screen combat block; remove it after the extraction and do not keep a compatibility wrapper.

- [ ] **Step 7: Run focused and full tests**

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest tests.test_app_logging tests.test_input_coordinator tests.test_game_state_targeting tests.test_game_state_source -v
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest discover -s tests -v
~~~

Expected: all tests PASS without thread/socket leak warnings.

- [ ] **Step 8: Commit app integration**

~~~powershell
git add src/screen_automation/app.py tests/test_app_logging.py tests/test_input_coordinator.py
git commit -m "feat: drive combat from game state"
~~~

---

### Task 7: Document, verify, build, and perform controlled runtime installation

**Files:**
- Modify: README.md
- Modify: tools/game_state_listener.py
- Modify the approved design spec only if implementation reveals a factual mismatch; do not broaden scope.

**Interfaces:**
- Listener prints schema v2 projected values.
- README documents both modes, world units, single UDP consumer, build/install, and restart requirement.

- [ ] **Step 1: Update listener diagnostics**

Append nearest target viewport and camera-relative values to its existing concise line:

~~~python
nearest_view = (
    "none"
    if nearest is None
    else (
        f"{nearest.config_id}@viewport="
        f"({nearest.viewport_x:.2f},{nearest.viewport_y:.2f},{nearest.viewport_depth:.1f}) "
        f"view=({nearest.view_x:.1f},{nearest.view_z:.1f})"
    )
)
~~~

Do not add file logging.

- [ ] **Step 2: Update README**

Document that game_state opens UDP and performs no HSV combat scan; screen opens no UDP and keeps HSV/templates. State that the standalone listener must be stopped before main.py in game_state mode. Explain near, far, crowd_radius, restart after edits, v0.2.0 build/install, and no snapshot when Unity has no active camera.

- [ ] **Step 3: Run complete automated verification**

~~~powershell
& 'C:\Users\User\Desktop\RicValeBot\.venv\Scripts\python.exe' -m unittest discover -s tests -v
dotnet run --project integrations/SpiritValeGameStateBridge.ProtocolTests -c Release
dotnet build integrations/SpiritValeGameStateBridge/SpiritValeGameStateBridge.csproj -c Release
~~~

Expected: all succeed; build has zero errors.

- [ ] **Step 4: Run safety and diff checks**

~~~powershell
rg -n "WriteProcessMemory|OpenProcess|VirtualAllocEx|CreateRemoteThread|SendServerRpc|ServerRpc" integrations/SpiritValeGameStateBridge src/screen_automation
git diff --check
git status --short
~~~

Expected: safety scan has no matches, diff check is clean, status has only intended documentation/listener changes.

- [ ] **Step 5: Commit docs**

~~~powershell
git add README.md tools/game_state_listener.py
git commit -m "docs: explain game state targeting"
~~~

- [ ] **Step 6: Install only while SpiritVale is closed**

Check Get-Process -Name SpiritVale first. When absent, run tools/install_game_state_bridge.ps1. Hash the built and installed DLL with Get-FileHash -Algorithm SHA256 and require exact equality.

- [ ] **Step 7: Perform two-mode runtime acceptance**

1. Run the standalone listener and verify schema 2 projection changes as monsters move.
2. Stop the listener, start main.py in game_state mode, and verify far/inside/near movement and cursor tracking.
3. Stop the app, set screen mode, restart, and verify HSV targeting while port 48231 is not owned by RicValeBot.
4. Restore the user's chosen final mode.

- [ ] **Step 8: Final branch verification**

~~~powershell
git status --short
git log --oneline -8
~~~

Expected: clean worktree and one focused commit per completed layer.
