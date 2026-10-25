import pytest
from datetime import datetime, timedelta, timezone
from app import main

def test_access_token_contains_short_expiry():
    token = main.tok('user-1')
    payload = main.jwt.decode(token, main.JWT_SECRET, algorithms=['HS256'])
    assert payload['sub'] == 'user-1'
    assert payload['type'] == 'access'
    assert payload['exp'] - int(datetime.now(timezone.utc).timestamp()) <= main.ACCESS_TTL

def test_refresh_tokens_are_hashed_and_unique():
    raw = 'refresh-secret'
    assert main.refresh_hash(raw) != raw
    assert main.refresh_hash(raw) == main.refresh_hash(raw)

@pytest.mark.asyncio
async def test_ssh_rejects_non_allowlisted_command(monkeypatch):
    class User: id = 'u1'
    with pytest.raises(Exception) as exc:
        await main.ssh(main.SSHIn(host='h', username='u', command='rm -rf /', private_key='k', approval_id='a'), User())
    assert 'allowlisted' in exc.value.detail

@pytest.mark.asyncio
async def test_ssh_requires_known_hosts(monkeypatch):
    class User: id = 'u1'
    class Approval:
        user_id='u1'; status='approved'; command='ls'; expires_at=datetime.now(timezone.utc)+timedelta(minutes=1)
    class Result:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def commit(self): pass
        async def get(self,*args): return Approval()
    monkeypatch.setattr(main, 'Session', lambda: Result())
    monkeypatch.setattr(main, 'KNOWN_HOSTS', 'missing-known-hosts')
    with pytest.raises(Exception) as exc:
        await main.ssh(main.SSHIn(host='h', username='u', command='ls', private_key='k', approval_id='a'), User())
    assert 'known_hosts' in exc.value.detail
