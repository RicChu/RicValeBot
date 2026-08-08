using System.Net;
using System.Net.Sockets;

namespace SpiritValeGameStateBridge;

public sealed class UdpPublisher : IDisposable
{
    private readonly UdpClient _client;
    private readonly IPEndPoint _destination;

    public UdpPublisher(string host, int port)
    {
        if (!IPAddress.TryParse(host, out var address) || !IPAddress.IsLoopback(address))
        {
            throw new ArgumentException("host must be a loopback IP address", nameof(host));
        }
        if (port is < IPEndPoint.MinPort or > IPEndPoint.MaxPort)
        {
            throw new ArgumentOutOfRangeException(nameof(port));
        }

        _client = new UdpClient(address.AddressFamily);
        _destination = new IPEndPoint(address, port);
    }

    public void Publish(BridgeSnapshot snapshot)
    {
        var payload = BridgeProtocol.Serialize(snapshot);
        _client.Send(payload, payload.Length, _destination);
    }

    public void Dispose()
    {
        _client.Dispose();
    }
}
