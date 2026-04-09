.PHONY: dev dev-build stop clean test migrate frontend-test backend-test lint

# 啟動開發環境
dev:
	docker compose up

dev-d:
	docker compose up -d

dev-build:
	docker compose up --build

stop:
	docker compose down

clean:
	docker compose down -v --remove-orphans

# 執行前端測試
frontend-test:
	docker compose run --rm frontend pnpm test

# 執行後端測試
backend-test:
	docker compose run --rm backend uv run pytest

# 執行所有測試
test: frontend-test backend-test

# 執行 linting
lint:
	docker compose run --rm backend uv run ruff check .
	docker compose run --rm backend uv run mypy .

# 資料庫 Migration
migrate:
	docker compose run --rm backend python manage.py migrate

# 新增 Migration
# 用法: make migration APP=accounts NAME=add_user_table
migration:
	docker compose run --rm backend python manage.py makemigrations $(APP)

# 建立超級使用者
superuser:
	docker compose run --rm backend python manage.py createsuperuser

# 收集靜態檔案
collectstatic:
	docker compose run --rm backend python manage.py collectstatic --noinput

ps:
	docker compose ps

logs:
	docker compose logs -f
