using System;
using System.Reflection;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using UnityEngine;

namespace SpiritValeGameStateBridge;

[BepInPlugin(Guid, Name, Version)]
public sealed class Plugin : BasePlugin
{
    public const string Guid = "local.spiritvale.gamestatebridge";
    public const string Name = "SpiritVale Game State Bridge";
    public const string Version = "0.1.2";

    internal static ManualLogSource Logger;
    internal static GameStateCollector Collector;
    internal static MonsterRegistry Registry;

    private Harmony _harmony;

    public override void Load()
    {
        Logger = Log;
        var enabled = Config.Bind("Bridge", "Enabled", true, "Enable read-only local telemetry.");
        var host = Config.Bind("Bridge", "Host", "127.0.0.1", "Loopback destination only.");
        var port = Config.Bind("Bridge", "Port", 48_231, "UDP destination port.");
        var snapshotIntervalMs = Config.Bind("Timing", "SnapshotIntervalMs", 100, "Combat snapshot interval.");
        var inventoryIntervalMs = Config.Bind("Timing", "InventoryIntervalMs", 1000, "Inventory refresh interval.");
        var diagnosticLogging = Config.Bind("Diagnostics", "DiagnosticLogging", true, "Log timing every ten seconds.");

        if (!enabled.Value)
        {
            Logger.LogInfo($"{Name} is disabled by configuration.");
            return;
        }

        try
        {
            Registry = new MonsterRegistry();
            Collector = new GameStateCollector(
                Registry,
                new UdpPublisher(host.Value, port.Value),
                Logger,
                snapshotIntervalMs.Value,
                inventoryIntervalMs.Value,
                diagnosticLogging.Value);
        }
        catch (Exception ex)
        {
            Logger.LogError($"Bridge initialization failed: {ex.Message}");
            return;
        }

        _harmony = new Harmony(Guid);
        TryPatch("monster start", AccessTools.Method(typeof(MonsterController), nameof(MonsterController.OnStartNetwork)), postfix: nameof(Patches.MonsterStartedPostfix));
        TryPatch("monster stop", AccessTools.Method(typeof(MonsterController), nameof(MonsterController.OnStopNetwork)), prefix: nameof(Patches.MonsterStoppedPrefix));
        TryPatch("local player update", AccessTools.Method(typeof(PlayerController), "Update"), postfix: nameof(Patches.PlayerUpdatePostfix));
        Logger.LogInfo($"{Name} v{Version} loaded; UDP={host.Value}:{port.Value}");
    }

    private void TryPatch(string label, MethodBase target, string prefix = null, string postfix = null)
    {
        if (target == null)
        {
            Logger.LogWarning($"[{label}] target method was not found; source disabled.");
            return;
        }
        try
        {
            _harmony.Patch(
                target,
                prefix == null ? null : new HarmonyMethod(typeof(Patches), prefix),
                postfix == null ? null : new HarmonyMethod(typeof(Patches), postfix));
            Logger.LogInfo($"[{label}] patch installed.");
        }
        catch (Exception ex)
        {
            Logger.LogWarning($"[{label}] patch failed: {ex.Message}");
        }
    }

    public override bool Unload()
    {
        try
        {
            _harmony?.UnpatchSelf();
            Collector?.Dispose();
        }
        catch (Exception ex)
        {
            Logger?.LogWarning($"Bridge unload failed: {ex.Message}");
        }
        Collector = null;
        Registry = null;
        return true;
    }
}

internal static class Patches
{
    public static void MonsterStartedPostfix(MonsterController __instance)
    {
        try
        {
            Plugin.Registry?.Register(__instance);
        }
        catch (Exception ex)
        {
            Plugin.Logger?.LogWarning($"Monster registration failed: {ex.Message}");
        }
    }

    public static void MonsterStoppedPrefix(MonsterController __instance)
    {
        try
        {
            Plugin.Registry?.Unregister(__instance);
        }
        catch (Exception ex)
        {
            Plugin.Logger?.LogWarning($"Monster removal failed: {ex.Message}");
        }
    }

    public static void PlayerUpdatePostfix(PlayerController __instance)
    {
        try
        {
            var localPlayer = App.Player;
            if (__instance == null || localPlayer == null || __instance != localPlayer) return;
            Plugin.Collector?.Tick(__instance, Time.unscaledTime);
        }
        catch (Exception ex)
        {
            Plugin.Logger?.LogWarning($"Player snapshot callback failed: {ex.Message}");
        }
    }
}
