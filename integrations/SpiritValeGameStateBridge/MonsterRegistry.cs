using System.Collections.Generic;

namespace SpiritValeGameStateBridge;

internal sealed class MonsterRegistry
{
    private readonly HashSet<MonsterController> _monsters = new();

    public void Register(MonsterController monster)
    {
        if (monster != null) _monsters.Add(monster);
    }

    public void Unregister(MonsterController monster)
    {
        if (monster != null) _monsters.Remove(monster);
    }

    public MonsterController[] Snapshot()
    {
        var valid = new List<MonsterController>(_monsters.Count);
        var stale = new List<MonsterController>();
        foreach (var monster in _monsters)
        {
            if (monster == null)
            {
                stale.Add(monster);
                continue;
            }
            valid.Add(monster);
        }
        foreach (var monster in stale) _monsters.Remove(monster);
        return valid.ToArray();
    }

    public void Clear()
    {
        _monsters.Clear();
    }
}
