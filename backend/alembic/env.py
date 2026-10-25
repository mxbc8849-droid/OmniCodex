from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import Base
config=context.config
if os.getenv('DATABASE_URL'): config.set_main_option('sqlalchemy.url', os.environ['DATABASE_URL'].replace('%','%%'))
# The project uses a minimal alembic.ini without logging sections; avoid
# fileConfig() so migration startup does not fail with KeyError: formatters.
target_metadata=Base.metadata
def run_migrations_offline():
 context.configure(url=config.get_main_option('sqlalchemy.url'),target_metadata=target_metadata,literal_binds=True,compare_type=True)
 with context.begin_transaction(): context.run_migrations()
async def run_async():
 connectable=async_engine_from_config(config.get_section(config.config_ini_section,{}),prefix='sqlalchemy.',poolclass=pool.NullPool)
 async with connectable.connect() as connection: await connection.run_sync(do_run_migrations)
 await connectable.dispose()
def do_run_migrations(connection:Connection):
 context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
 with context.begin_transaction(): context.run_migrations()
if context.is_offline_mode(): run_migrations_offline()
else:
 import asyncio; asyncio.run(run_async())
