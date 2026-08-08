using System.Text;
using System.Text.Json;
using SpiritValeGameStateBridge;

static void Require(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}

var snapshot = new BridgeSnapshot
{
    SchemaVersion = 1,
    Sequence = 42,
    CapturedAtUnixMs = 1_786_123_456_789,
    MapId = "stormreef_isle",
    Player = new PlayerSnapshot
    {
        CharacterId = "character-42",
        X = 10.0f,
        Y = 2.0f,
        Z = 20.0f,
        Health = 900,
        MaxHealth = 1000,
    },
    Monsters =
    [
        new MonsterSnapshot
        {
            RuntimeId = "monster-runtime-127",
            ConfigId = "scrapfang",
            X = 30.0f,
            Y = 2.0f,
            Z = 20.0f,
            Health = 120,
            MaxHealth = 300,
            IsAlive = true,
        },
    ],
    Inventory = new InventorySummary
    {
        Equips = 12,
        Artifacts = 3,
        Cards = 8,
        Gems = 4,
        Junks = 15,
        Consumables = 6,
        Cosmetics = 2,
    },
    EquippedIds = ["stormplate-shoes"],
    ArtifactIds = ["drooping-bat"],
};

var payload = BridgeProtocol.Serialize(snapshot);
using var json = JsonDocument.Parse(payload);
var root = json.RootElement;
Require(root.GetProperty("schema_version").GetInt32() == 1, "schema_version mismatch");
Require(root.GetProperty("map_id").GetString() == "stormreef_isle", "map_id mismatch");
Require(root.GetProperty("player").GetProperty("x").GetSingle() == 10.0f, "player.x mismatch");
Require(root.GetProperty("monsters")[0].GetProperty("health").GetInt32() == 120, "monster health mismatch");
Require(root.GetProperty("inventory").GetProperty("equips").GetInt32() == 12, "inventory mismatch");
Require(root.GetProperty("equipped_ids")[0].GetString() == "stormplate-shoes", "equipped ids mismatch");

var rejectedExternalAddress = false;
try
{
    using var publisher = new UdpPublisher("8.8.8.8", 48_231);
}
catch (ArgumentException)
{
    rejectedExternalAddress = true;
}
Require(rejectedExternalAddress, "publisher accepted a non-loopback address");

var optionalIds = OptionalStringCollector.Collect(3, index => index switch
{
    0 => "equip-one",
    1 => throw new ArrayTypeMismatchException("simulated IL2CPP generic element mismatch"),
    2 => "equip-two",
    _ => string.Empty,
});
Require(optionalIds.SequenceEqual(new[] { "equip-one", "equip-two" }),
    "optional field failure blocked readable items");

Console.WriteLine(Encoding.UTF8.GetString(payload));
