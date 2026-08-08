using System;

namespace SpiritValeGameStateBridge;

public static class ExceptionDiagnostic
{
    public static string Format(Exception exception)
    {
        ArgumentNullException.ThrowIfNull(exception);
        return exception.ToString();
    }
}
