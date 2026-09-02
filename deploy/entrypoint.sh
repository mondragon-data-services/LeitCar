#!/usr/bin/env bash
# Espera o Postgres, gera a landing do SEO e sobe o app.
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "aguardando o banco..."
  for _ in $(seq 1 60); do
    psql "$DATABASE_URL" -c 'select 1' >/dev/null 2>&1 && break
    sleep 1
  done
  python landing/gerar_landing.py /app/landing/dist/index.html || \
    echo "landing nao gerada (segue o jogo)"
fi

exec "$@"
