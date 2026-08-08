using System;
using System.Collections.Generic;

namespace SpiritValeGameStateBridge;

public sealed class ReferenceRegistry<T> where T : class
{
    private readonly HashSet<T> _items = new();

    public void Register(T item)
    {
        if (item != null) _items.Add(item);
    }

    public void Unregister(T item)
    {
        if (item != null) _items.Remove(item);
    }

    public IEnumerable<T> Enumerate(Func<T, bool> isValid)
    {
        ArgumentNullException.ThrowIfNull(isValid);
        foreach (var item in _items)
        {
            if (isValid(item)) yield return item;
        }
    }

    public void Clear()
    {
        _items.Clear();
    }
}
