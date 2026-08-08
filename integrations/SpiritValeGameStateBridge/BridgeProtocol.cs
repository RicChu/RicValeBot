using System;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace SpiritValeGameStateBridge;

public sealed class BridgeSnapshot
{
    [JsonPropertyName("schema_version")]
    public int SchemaVersion { get; set; } = 2;

    [JsonPropertyName("sequence")]
    public long Sequence { get; set; }

    [JsonPropertyName("captured_at_unix_ms")]
    public long CapturedAtUnixMs { get; set; }

    [JsonPropertyName("map_id")]
    public string MapId { get; set; } = string.Empty;

    [JsonPropertyName("player")]
    public PlayerSnapshot Player { get; set; } = new();

    [JsonPropertyName("monsters")]
    public MonsterSnapshot[] Monsters { get; set; } = Array.Empty<MonsterSnapshot>();

    [JsonPropertyName("inventory")]
    public InventorySummary Inventory { get; set; } = new();

    [JsonPropertyName("equipped_ids")]
    public string[] EquippedIds { get; set; } = Array.Empty<string>();

    [JsonPropertyName("artifact_ids")]
    public string[] ArtifactIds { get; set; } = Array.Empty<string>();
}

public sealed class PlayerSnapshot
{
    [JsonPropertyName("character_id")]
    public string CharacterId { get; set; } = string.Empty;

    [JsonPropertyName("x")]
    public float X { get; set; }

    [JsonPropertyName("y")]
    public float Y { get; set; }

    [JsonPropertyName("z")]
    public float Z { get; set; }

    [JsonPropertyName("health")]
    public int Health { get; set; }

    [JsonPropertyName("max_health")]
    public int MaxHealth { get; set; }
}

public sealed class MonsterSnapshot
{
    [JsonPropertyName("runtime_id")]
    public string RuntimeId { get; set; } = string.Empty;

    [JsonPropertyName("config_id")]
    public string ConfigId { get; set; } = string.Empty;

    [JsonPropertyName("x")]
    public float X { get; set; }

    [JsonPropertyName("y")]
    public float Y { get; set; }

    [JsonPropertyName("z")]
    public float Z { get; set; }

    [JsonPropertyName("health")]
    public int Health { get; set; }

    [JsonPropertyName("max_health")]
    public int MaxHealth { get; set; }

    [JsonPropertyName("is_alive")]
    public bool IsAlive { get; set; }

    [JsonPropertyName("viewport_x")]
    public float ViewportX { get; set; }

    [JsonPropertyName("viewport_y")]
    public float ViewportY { get; set; }

    [JsonPropertyName("viewport_depth")]
    public float ViewportDepth { get; set; }

    [JsonPropertyName("view_x")]
    public float ViewX { get; set; }

    [JsonPropertyName("view_z")]
    public float ViewZ { get; set; }
}

public sealed class InventorySummary
{
    [JsonPropertyName("equips")]
    public int Equips { get; set; }

    [JsonPropertyName("artifacts")]
    public int Artifacts { get; set; }

    [JsonPropertyName("cards")]
    public int Cards { get; set; }

    [JsonPropertyName("gems")]
    public int Gems { get; set; }

    [JsonPropertyName("junks")]
    public int Junks { get; set; }

    [JsonPropertyName("consumables")]
    public int Consumables { get; set; }

    [JsonPropertyName("cosmetics")]
    public int Cosmetics { get; set; }
}

public static class BridgeProtocol
{
    private static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = false,
    };

    public static byte[] Serialize(BridgeSnapshot snapshot)
    {
        ArgumentNullException.ThrowIfNull(snapshot);
        return JsonSerializer.SerializeToUtf8Bytes(snapshot, Options);
    }
}
