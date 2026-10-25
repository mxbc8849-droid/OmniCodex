# OmniCodex

Cloud-Controlled AI agent skeleton for synchronized PC/mobile operations.

## Run backend

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The default implementation uses an in-memory repository so it runs immediately. Set `DATABASE_URL` and `REDIS_URL` when wiring PostgreSQL/Redis adapters.

## Generate Flutter client

Copy `client/lib` into a Flutter project, add `http` and `web_socket_channel`, then run `flutter pub get`.

## Validate CI locally

Install `actionlint` and `yamllint`, then run `scripts/validate-ci.ps1` on Windows or `bash scripts/validate-ci.sh` on Linux/macOS.

