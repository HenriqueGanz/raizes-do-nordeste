#!/bin/sh
# script apenas para o docker rodar scripts no deploy do render e popular o banco
set -e
python scripts/init_db.py
python scripts/seed_db.py
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:$PORT
