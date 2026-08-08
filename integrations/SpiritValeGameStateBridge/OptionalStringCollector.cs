using System;
using System.Collections.Generic;

namespace SpiritValeGameStateBridge;

public static class OptionalStringCollector
{
    private static readonly Action<Exception> IgnoreError = _ => { };

    public static string[] Collect(int count, Func<int, string> read)
    {
        return Collect(count, read, IgnoreError);
    }

    public static string[] Collect(int count, Func<int, string> read, Action<Exception> onError)
    {
        ArgumentNullException.ThrowIfNull(read);
        if (count <= 0) return Array.Empty<string>();

        var values = new List<string>(count);
        for (var index = 0; index < count; index++)
        {
            try
            {
                var value = read(index);
                if (!string.IsNullOrEmpty(value)) values.Add(value);
            }
            catch (Exception ex)
            {
                onError?.Invoke(ex);
            }
        }
        return values.ToArray();
    }
}
