#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for database..."
python -c "
import time, sqlalchemy, os
url = os.environ['DATABASE_URL']
for _ in range(30):
    try:
        sqlalchemy.create_engine(url).connect().close()
        print('Database is up'); break
    except Exception as e:
        print('db not ready, retrying...', e); time.sleep(2)
else:
    raise SystemExit('Database never became available')
"

echo "Running migrations..."
alembic upgrade head

echo "Bootstrapping admin / seed data..."
python -m app.bootstrap

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
