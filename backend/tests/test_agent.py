import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
from app import main

class User: id='agent-test'

@pytest.mark.asyncio
async def test_agent_task_creates_timeline(monkeypatch):
    events=[]
    async def pub(uid,event): events.append(event)
    monkeypatch.setattr(main,'publish',pub)
    async with AsyncClient(transport=ASGITransport(app=main.app),base_url='http://test') as c:
        r=await c.post('/v1/agent/tasks',json={'prompt':'搭建活码系统','target_host':'127.0.0.1'},headers={'Authorization':'Bearer x'})
    # dependency is replaced directly for unit-level handler invocation below
    assert r.status_code in (401, 422)
    t=await main.agent_task(main.AgentTaskIn(prompt='搭建活码系统',target_host='127.0.0.1'),User())
    assert t['status']=='planned'
    assert [s['id'] for s in t['steps']]==['plan','inspect','install','deploy','verify']
    assert events[-1]['type']=='agent.task.created'

@pytest.mark.asyncio
async def test_agent_run_retries_and_completes(monkeypatch,tmp_path):
    key=tmp_path/'id'; key.write_text('key')
    hosts=tmp_path/'known'; hosts.write_text('host')
    monkeypatch.setattr(main,'AGENT_SSH_USER','root',raising=False)
    monkeypatch.setattr(main,'KNOWN_HOSTS',str(hosts))
    monkeypatch.setenv('AGENT_SSH_KEY',str(key))
    events=[]
    async def pub(uid,event): events.append(event)
    monkeypatch.setattr(main,'publish',pub)
    class R:
        def __init__(self,code): self.exit_status=code; self.stdout='ok'; self.stderr='err' if code else ''
    class C:
        n=0
        async def run(self,cmd,check=False):
            self.n+=1
            return R(1 if self.n==1 else 0)
        async def __aenter__(self): return self
        async def __aexit__(self,*a): pass
    monkeypatch.setattr(main.asyncssh,'connect',lambda *a,**k:C())
    t=await main.agent_task(main.AgentTaskIn(prompt='部署',target_host='host',max_retries=1),User())
    out=await main.agent_task_run(t['id'],User())
    assert out['status']=='completed'
    assert any(e['type']=='agent.step.retry' for e in events)

@pytest.mark.asyncio
async def test_agent_run_missing_target_fails(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'AGENT_SSH_KEY',str(tmp_path/'missing'),raising=False)
    t=await main.agent_task(main.AgentTaskIn(prompt='部署'),User())
    with pytest.raises(Exception) as exc: await main.agent_task_run(t['id'],User())
    assert 'not configured' in exc.value.detail
