from __future__ import annotations
import asyncio, base64, hashlib, json, os, secrets, uuid, shlex
from datetime import datetime, timedelta, timezone
from typing import Any
import asyncssh, litellm
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL=os.getenv('DATABASE_URL','postgresql+asyncpg://omnicodex:omnicodex@postgres:5432/omnicodex'); REDIS_URL=os.getenv('REDIS_URL','redis://redis:6379/0'); JWT_SECRET=os.getenv('JWT_SECRET','change-me-in-production'); ACCESS_TTL=int(os.getenv('ACCESS_TTL_SECONDS','900')); REFRESH_TTL=int(os.getenv('REFRESH_TTL_SECONDS','2592000')); KNOWN_HOSTS=os.getenv('SSH_KNOWN_HOSTS','/run/secrets/known_hosts')
engine=create_async_engine(DATABASE_URL,pool_pre_ping=True); Session=async_sessionmaker(engine,expire_on_commit=False); redis:Redis=Redis.from_url(REDIS_URL,decode_responses=True); oauth2=OAuth2PasswordBearer(tokenUrl='/v1/auth/token')
class Base(DeclarativeBase): pass
class User(Base):
 __tablename__='users'; id:Mapped[str]=mapped_column(String(36),primary_key=True); email:Mapped[str]=mapped_column(String(320),unique=True,index=True); password_hash:Mapped[str]=mapped_column(Text)
class Project(Base):
 __tablename__='projects'; id:Mapped[str]=mapped_column(String(36),primary_key=True); user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True); name:Mapped[str]=mapped_column(String(200)); snapshot:Mapped[dict[str,Any]]=mapped_column(JSON,default=dict); version:Mapped[int]=mapped_column(default=1); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Approval(Base):
 __tablename__='approvals'; id:Mapped[str]=mapped_column(String(36),primary_key=True); user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True); command:Mapped[str]=mapped_column(Text); status:Mapped[str]=mapped_column(String(20),default='pending'); decided_by:Mapped[str|None]=mapped_column(String(36),nullable=True); expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class RefreshToken(Base):
 __tablename__='refresh_tokens'; id:Mapped[str]=mapped_column(String(36),primary_key=True); user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True); token_hash:Mapped[str]=mapped_column(String(64),unique=True); expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True)); revoked_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class Credentials(BaseModel): email:str; password:str=Field(min_length=8)
class ProjectIn(BaseModel): name:str; snapshot:dict[str,Any]=Field(default_factory=dict)
class ApprovalIn(BaseModel): command:str; ttl_seconds:int=300
class ChatIn(BaseModel): messages:list[dict[str,str]]; model:str='openai/gpt-4o-mini'
class SSHIn(BaseModel): host:str; username:str; command:str; port:int=22; private_key:str; approval_id:str
COMMAND_ALLOWLIST=tuple(x.strip() for x in os.getenv('COMMAND_ALLOWLIST','docker,systemctl,nginx,python3,python,bash,ls,cat,mkdir,cp,mv,chmod').split(',') if x.strip())
def ph(v):
 s=secrets.token_bytes(16); return base64.b64encode(s+hashlib.pbkdf2_hmac('sha256',v.encode(),s,210000)).decode()
def pok(v,e):
 r=base64.b64decode(e); return secrets.compare_digest(hashlib.pbkdf2_hmac('sha256',v.encode(),r[:16],210000),r[16:])
def tok(uid): return jwt.encode({'sub':uid,'type':'access','exp':datetime.now(timezone.utc)+timedelta(seconds=ACCESS_TTL)},JWT_SECRET,algorithm='HS256')
def refresh_hash(v): return hashlib.sha256(v.encode()).hexdigest()
async def issue_refresh(uid):
 raw=secrets.token_urlsafe(48)
 async with Session() as s: s.add(RefreshToken(id=str(uuid.uuid4()),user_id=uid,token_hash=refresh_hash(raw),expires_at=datetime.now(timezone.utc)+timedelta(seconds=REFRESH_TTL))); await s.commit()
 return raw
async def current(token:str=Depends(oauth2)):
 try: uid=jwt.decode(token,JWT_SECRET,algorithms=['HS256'])['sub']
 except (JWTError,KeyError): raise HTTPException(401,'invalid token')
 async with Session() as s:
  u=await s.get(User,uid)
  if not u: raise HTTPException(401,'user not found')
  return u
async def publish(uid,event): await redis.publish(f'omnicodex:{uid}',json.dumps(event))
app=FastAPI(title='OmniCodex Control Plane',version='0.2.0'); connections={}
@app.post('/v1/auth/register')
async def register(d:Credentials):
 async with Session() as s:
  if await s.scalar(select(User).where(User.email==d.email)): raise HTTPException(409,'email exists')
  u=User(id=str(uuid.uuid4()),email=d.email,password_hash=ph(d.password)); s.add(u); await s.commit(); return {'access_token':tok(u.id),'refresh_token':await issue_refresh(u.id),'token_type':'bearer'}
@app.post('/v1/auth/token')
async def login(f:OAuth2PasswordRequestForm=Depends()):
 async with Session() as s: u=await s.scalar(select(User).where(User.email==f.username))
 if not u or not pok(f.password,u.password_hash): raise HTTPException(401,'invalid credentials')
 return {'access_token':tok(u.id),'refresh_token':await issue_refresh(u.id),'token_type':'bearer'}
@app.post('/v1/auth/refresh')
async def refresh(body:dict):
 raw=body.get('refresh_token','')
 async with Session() as s:
  r=await s.scalar(select(RefreshToken).where(RefreshToken.token_hash==refresh_hash(raw)))
  if not r or r.revoked_at or r.expires_at<datetime.now(timezone.utc): raise HTTPException(401,'invalid refresh token')
  r.revoked_at=datetime.now(timezone.utc); await s.commit()
 return {'access_token':tok(r.user_id),'refresh_token':await issue_refresh(r.user_id),'token_type':'bearer'}
@app.post('/v1/auth/revoke')
async def revoke(body:dict):
 async with Session() as s:
  r=await s.scalar(select(RefreshToken).where(RefreshToken.token_hash==refresh_hash(body.get('refresh_token',''))))
  if r: r.revoked_at=datetime.now(timezone.utc); await s.commit()
 return {'revoked':True}
@app.get('/health')
async def health(): return {'status':'ok','postgres':True,'redis':await redis.ping()}
@app.get('/v1/sync/export')
async def export(user=Depends(current)):
 async with Session() as s: rows=(await s.scalars(select(Project).where(Project.user_id==user.id))).all()
 m={'schema':2,'cursor':datetime.now(timezone.utc).isoformat(),'projects':[{'id':p.id,'name':p.name,'snapshot':p.snapshot,'version':p.version} for p in rows]}; m['sha256']=hashlib.sha256(json.dumps(m,sort_keys=True).encode()).hexdigest(); return {'manifest':m,'events':[]}
@app.put('/v1/projects/{pid}')
async def upsert(pid:str,d:ProjectIn,user=Depends(current)):
 async with Session() as s:
  p=await s.get(Project,pid)
  if p and p.user_id!=user.id: raise HTTPException(403,'forbidden')
  if not p: p=Project(id=pid,user_id=user.id,name=d.name,snapshot=d.snapshot); s.add(p)
  else: p.name,p.snapshot,p.version,p.updated_at=d.name,d.snapshot,p.version+1,datetime.now(timezone.utc)
  await s.commit(); out={'id':p.id,'name':p.name,'snapshot':p.snapshot,'version':p.version}
 await publish(user.id,{'type':'project.updated','project':out}); return out
@app.post('/v1/ai/chat')
async def chat(d:ChatIn,user=Depends(current)):
 r=await litellm.acompletion(model=d.model,messages=d.messages,stream=False); return {'model':d.model,'content':r.choices[0].message.content}
@app.post('/v1/approvals')
async def approval(d:ApprovalIn,user=Depends(current)):
 a=Approval(id=str(uuid.uuid4()),user_id=user.id,command=d.command,expires_at=datetime.now(timezone.utc)+timedelta(seconds=d.ttl_seconds))
 async with Session() as s: s.add(a); await s.commit()
 await publish(user.id,{'type':'approval.pending','approval_id':a.id,'command':a.command}); return {'id':a.id,'status':a.status}
@app.post('/v1/approvals/{aid}/{decision}')
async def decide(aid:str,decision:str,user=Depends(current)):
 if decision not in {'approve','deny'}: raise HTTPException(400,'bad decision')
 async with Session() as s:
  a=await s.get(Approval,aid)
  if not a or a.user_id!=user.id or a.status!='pending' or a.expires_at<datetime.now(timezone.utc): raise HTTPException(409,'approval unavailable')
  a.status='approved' if decision=='approve' else 'denied'; a.decided_by=user.id; await s.commit()
 await publish(user.id,{'type':'approval.resolved','approval_id':aid,'status':a.status}); return {'status':a.status}
@app.post('/v1/ssh/execute')
async def ssh(d:SSHIn,user=Depends(current)):
 try: first=shlex.split(d.command)[0]
 except (ValueError,IndexError): raise HTTPException(400,'invalid command')
 if first not in COMMAND_ALLOWLIST: raise HTTPException(403,'command is not allowlisted')
 async with Session() as s:
  a=await s.get(Approval,d.approval_id)
  if not a or a.user_id!=user.id or a.status!='approved' or a.command!=d.command: raise HTTPException(403,'approved approval required')
 try:
  if not os.path.exists(KNOWN_HOSTS): raise HTTPException(500,'SSH known_hosts is not configured')
  async with asyncssh.connect(d.host,port=d.port,username=d.username,client_keys=[d.private_key],known_hosts=KNOWN_HOSTS) as c:
   r=await c.run(d.command,check=False); await publish(user.id,{'type':'ssh.progress','status':'completed'}); return {'exit_status':r.exit_status,'stdout':r.stdout,'stderr':r.stderr}
 except Exception as e: raise HTTPException(502,f'ssh failed: {e}')
@app.websocket('/v1/ws')
async def ws(w:WebSocket,token:str):
 try: uid=jwt.decode(token,JWT_SECRET,algorithms=['HS256'])['sub']
 except JWTError: await w.close(code=status.WS_1008_POLICY_VIOLATION); return
 await w.accept(); connections.setdefault(uid,set()).add(w); ps=redis.pubsub(); await ps.subscribe(f'omnicodex:{uid}')
 async def reader():
  async for m in ps.listen():
   if m.get('type')=='message':
    for c in list(connections[uid]):
     try: await c.send_text(m['data'])
     except Exception: connections[uid].discard(c)
 task=asyncio.create_task(reader())
 try:
  await w.send_json({'type':'connected','user_id':uid})
  while True: await w.receive_text()
 except WebSocketDisconnect: pass
 finally: task.cancel(); await ps.unsubscribe(f'omnicodex:{uid}'); connections[uid].discard(w)
