"""Provider Router Verification Test."""
import pytest
from ultron.v2.providers.router import ProviderRouter


@pytest.mark.asyncio
async def test_provider_router_list():
    """Test listing of available providers."""
    r = ProviderRouter()
    providers = r.list_providers()
    assert isinstance(providers, list)
    assert len(providers) > 0, "En az 1 provider olmalı"


@pytest.mark.asyncio
async def test_all_providers_status():
    """Test the status of all providers."""
    r = ProviderRouter()
    status = await r.provider_status()
    assert isinstance(status, dict)
    for name, s in status.items():
        assert "available" in s, f"{name}: 'available' field eksik"
        assert "latency_ms" in s, f"{name}: 'latency_ms' field eksik"
        assert "model" in s, f"{name}: 'model' field eksik"
        print(f"  [OK] {name}: {s['latency_ms']}ms - {s['model']}")
