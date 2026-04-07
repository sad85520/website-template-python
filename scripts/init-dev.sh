#!/usr/bin/env bash
# 一鍵初始化開發環境
set -e

echo "=== Website Template Python - 初始化開發環境 ==="

if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未啟動，請先啟動 Docker Desktop"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "📋 建立 .env 從範本..."
    cp .env.example .env
    echo "⚠️  請編輯 .env 填入你的設定"
    echo "   按 Enter 繼續..."
    read -r
fi

echo "🚀 啟動 Docker 服務..."
docker compose up -d --build

echo "⏳ 等待 PostgreSQL 啟動..."
timeout 60 bash -c 'until docker compose exec postgres pg_isready -U postgres; do sleep 2; done'

echo "🗄️  執行 Django Migration..."
docker compose run --rm backend python manage.py migrate

echo ""
echo "✅ 初始化完成！"
echo ""
echo "   應用程式: http://localhost"
echo "   API 文件:  http://localhost/api/schema/swagger-ui/"
echo "   健康檢查:  http://localhost/api/health/"
echo ""
echo "   建立管理員帳號: make superuser"
