import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health(monkeypatch):
    class R:
        async def ping(self): return True
    monkeypatch.setattr('app.main.redis', R())
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        r=await c.get('/health')
    assert r.status_code == 200

def test_command_allowlist():
    from app.main import COMMAND_ALLOWLIST
    assert 'docker' in COMMAND_ALLOWLIST
