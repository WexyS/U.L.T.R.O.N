"""Provider Router Verification Test."""
import asyncio
from ultron.v2.providers.router import ProviderRouter


async def test():
    r = ProviderRouter()
    print("Aktif providers:", r.list_providers())
    status = await r.provider_status()
    for name, s in status.items():
        icon = "OK" if s["available"] else "X"
        print(f"  [{icon}] {name}: {s['latency_ms']}ms - {s['model']}")


asyncio.run(test())
