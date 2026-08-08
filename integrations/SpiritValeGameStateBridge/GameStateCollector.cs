using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using BepInEx.Logging;
using UnityEngine;

namespace SpiritValeGameStateBridge;

internal sealed class GameStateCollector : IDisposable
{
    private readonly MonsterRegistry _registry;
    private readonly UdpPublisher _publisher;
    private readonly ManualLogSource _logger;
    private readonly float _snapshotIntervalSeconds;
    private readonly float _inventoryIntervalSeconds;
    private readonly bool _diagnosticLogging;
    private float _nextSnapshotTime;
    private float _nextInventoryTime;
    private float _nextDiagnosticTime;
    private long _sequence;
    private long _sampleCount;
    private double _totalElapsedMs;
    private double _maxElapsedMs;
    private InventorySummary _inventory = new();
    private string[] _equippedIds = Array.Empty<string>();
    private string[] _artifactIds = Array.Empty<string>();
    private bool _optionalInventoryWarningLogged;

    public GameStateCollector(
        MonsterRegistry registry,
        UdpPublisher publisher,
        ManualLogSource logger,
        int snapshotIntervalMs,
        int inventoryIntervalMs,
        bool diagnosticLogging)
    {
        _registry = registry;
        _publisher = publisher;
        _logger = logger;
        _snapshotIntervalSeconds = Math.Max(20, snapshotIntervalMs) / 1000f;
        _inventoryIntervalSeconds = Math.Max(100, inventoryIntervalMs) / 1000f;
        _diagnosticLogging = diagnosticLogging;
    }

    public void Tick(PlayerController player, float now)
    {
        if (player == null || now < _nextSnapshotTime) return;
        _nextSnapshotTime = now + _snapshotIntervalSeconds;

        var watch = Stopwatch.StartNew();
        try
        {
            if (!TryCapture(player, now, out var snapshot)) return;
            _publisher.Publish(snapshot);
        }
        catch (Exception ex)
        {
            _logger.LogWarning($"Game-state snapshot failed: {ExceptionDiagnostic.Format(ex)}");
        }
        finally
        {
            watch.Stop();
            RecordTiming(now, watch.Elapsed.TotalMilliseconds);
        }
    }

    private bool TryCapture(PlayerController player, float now, out BridgeSnapshot snapshot)
    {
        snapshot = null;
        var character = player.CharacterData;
        var health = player.Health;
        if (character == null || health == null) return false;

        var playerPosition = player.Position;
        if (!IsFinite(playerPosition)) return false;
        var camera = Camera.main;
        if (camera == null) return false;

        if (now >= _nextInventoryTime)
        {
            _nextInventoryTime = now + _inventoryIntervalSeconds;
            try
            {
                RefreshInventory(character);
            }
            catch (Exception ex)
            {
                LogOptionalInventoryFailure(ex);
            }
        }

        var monsters = new List<MonsterSnapshot>();
        foreach (var monster in _registry.Enumerate())
        {
            try
            {
                var monsterHealth = monster.Health;
                var position = monster.Position;
                if (monsterHealth == null || !IsFinite(position)) continue;
                var viewport = camera.WorldToViewportPoint(position);
                var view = camera.transform.InverseTransformPoint(position);
                if (!IsFinite(viewport) || !IsFinite(view)) continue;
                var configId = monster.ConfigId;
                if (string.IsNullOrEmpty(configId)) configId = monster.MonsterId;
                monsters.Add(new MonsterSnapshot
                {
                    RuntimeId = monster.GetInstanceID().ToString(CultureInfo.InvariantCulture),
                    ConfigId = configId ?? string.Empty,
                    X = position.x,
                    Y = position.y,
                    Z = position.z,
                    Health = monsterHealth.Health,
                    MaxHealth = monsterHealth.MaxHealth,
                    IsAlive = monsterHealth.Health > 0,
                    ViewportX = viewport.x,
                    ViewportY = viewport.y,
                    ViewportDepth = viewport.z,
                    ViewX = view.x,
                    ViewZ = view.z,
                });
            }
            catch (Exception ex)
            {
                if (_diagnosticLogging) _logger.LogWarning($"Skipped invalid monster: {ex.Message}");
            }
        }

        snapshot = new BridgeSnapshot
        {
            SchemaVersion = 2,
            Sequence = ++_sequence,
            CapturedAtUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            MapId = character.State == null ? null : character.State.MapId,
            Player = new PlayerSnapshot
            {
                CharacterId = character.UID ?? string.Empty,
                X = playerPosition.x,
                Y = playerPosition.y,
                Z = playerPosition.z,
                Health = health.Health,
                MaxHealth = health.MaxHealth,
            },
            Monsters = monsters.ToArray(),
            Inventory = _inventory,
            EquippedIds = _equippedIds,
            ArtifactIds = _artifactIds,
        };
        return true;
    }

    private void RefreshInventory(CharacterData character)
    {
        var inventory = character.Inventory;
        _inventory = new InventorySummary
        {
            Equips = inventory == null || inventory.Equips == null ? 0 : inventory.Equips.Count,
            Artifacts = inventory == null || inventory.Artifacts == null ? 0 : inventory.Artifacts.Count,
            Cards = inventory == null || inventory.Cards == null ? 0 : inventory.Cards.Count,
            Gems = inventory == null || inventory.Gems == null ? 0 : inventory.Gems.Count,
            Junks = inventory == null || inventory.Junks == null ? 0 : inventory.Junks.Count,
            Consumables = inventory == null || inventory.Consumables == null ? 0 : inventory.Consumables.Count,
            Cosmetics = inventory == null || inventory.Cosmetics == null ? 0 : inventory.Cosmetics.Count,
        };

        _equippedIds = ReadEquippedIds(character);
        _artifactIds = ReadArtifactIds(character);
    }

    private string[] ReadEquippedIds(CharacterData character)
    {
        var typedSource = character.Equips;
        var source = typedSource?.TryCast<Il2CppSystem.Collections.IList>();
        if (source == null) return Array.Empty<string>();
        return OptionalStringCollector.Collect(typedSource.Count, index =>
        {
            var slot = source[index]?.TryCast<EquipSlotData>();
            return slot?.Equip?.Id;
        }, LogOptionalInventoryFailure);
    }

    private string[] ReadArtifactIds(CharacterData character)
    {
        var typedSource = character.Artifacts;
        var source = typedSource?.TryCast<Il2CppSystem.Collections.IList>();
        if (source == null) return Array.Empty<string>();
        return OptionalStringCollector.Collect(typedSource.Count, index =>
        {
            var artifact = source[index]?.TryCast<ArtifactData>();
            return artifact?.Id;
        }, LogOptionalInventoryFailure);
    }

    private void LogOptionalInventoryFailure(Exception ex)
    {
        if (_optionalInventoryWarningLogged) return;
        _optionalInventoryWarningLogged = true;
        _logger.LogWarning($"Optional inventory IDs were skipped: {ex.Message}");
    }

    private void RecordTiming(float now, double elapsedMs)
    {
        _sampleCount++;
        _totalElapsedMs += elapsedMs;
        _maxElapsedMs = Math.Max(_maxElapsedMs, elapsedMs);
        if (!_diagnosticLogging || now < _nextDiagnosticTime) return;
        _nextDiagnosticTime = now + 10f;
        var mean = _sampleCount == 0 ? 0d : _totalElapsedMs / _sampleCount;
        _logger.LogInfo($"Game-state timing: samples={_sampleCount}; mean={mean:F2}ms; max={_maxElapsedMs:F2}ms");
        _sampleCount = 0;
        _totalElapsedMs = 0d;
        _maxElapsedMs = 0d;
    }

    private static bool IsFinite(Vector3 position)
    {
        return IsFinite(position.x) && IsFinite(position.y) && IsFinite(position.z);
    }

    private static bool IsFinite(float value)
    {
        return !float.IsNaN(value) && !float.IsInfinity(value);
    }

    public void Dispose()
    {
        _publisher.Dispose();
        _registry.Clear();
    }
}
