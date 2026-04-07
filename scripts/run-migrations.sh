#!/usr/bin/env bash
set -e
echo "=== 執行 Django Migration ==="
docker compose run --rm backend python manage.py migrate
echo "✅ Migration 完成"
