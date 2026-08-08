using System.Collections.Generic;

namespace SpiritValeGameStateBridge;

internal sealed class MonsterRegistry
{
    private readonly ReferenceRegistry<MonsterController> _monsters = new();

    public void Register(MonsterController monster)
    {
        _monsters.Register(monster);
    }

    public void Unregister(MonsterController monster)
    {
        _monsters.Unregister(monster);
    }

    public IEnumerable<MonsterController> Enumerate()
    {
        return _monsters.Enumerate(monster => monster != null);
    }

    public void Clear()
    {
        _monsters.Clear();
    }
}
