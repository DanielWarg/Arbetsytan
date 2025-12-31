#!/bin/bash
set -e

# Wait for postgres to be ready
until PGPASSWORD=arbetsytan psql -h postgres -U arbetsytan -d arbetsytan -c '\q' 2>/dev/null; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - executing init script"

# Run init script
PGPASSWORD=arbetsytan psql -h postgres -U arbetsytan -d arbetsytan -f /app/init_db.sql

# Start uvicorn
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload

