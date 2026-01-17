req:
	pipreqs . --force

i:
	pip install -r requirements.txt

install-browsers:
	playwright install chromium

up:
	docker compose up -d

b:
	docker compose up -d --build

migrate:
	@bash scripts/run_migrations.sh

m:
	@make migrate

migrate-status:
	@echo "Migration status:"
	@docker compose exec -T postgres psql -U bwired -d bwired_research -c "SELECT version, applied_at::text FROM schema_migrations ORDER BY version;" 2>/dev/null || echo "No migrations applied yet"

migrate-pending:
	@echo "Pending migrations:"
	@for f in migrations/*.sql; do filename=$$(basename "$$f"); version=$${filename%%_*}; echo "  - $$filename (version: $$version)"; done

migrate-reset:
	@echo "WARNING: This will delete all data and reapply migrations!"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker compose exec -T postgres psql -U bwired -d bwired_research -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null; \
		make migrate; \
	else \
		echo "Aborted"; \
	fi

r:
	uvicorn internal.server:app --host 0.0.0.0 --port 8000

d:
	docker exec -it postgres_db psql -U bwired -d bwired_research

logs:
	@echo "Following SearXNG logs (filtered)..."
	docker compose logs -f searxng 2>&1 | sed '/radio_browser/d; /ahmia/d; /torch/d; /botdetection/d; /Unknown host/d; /ERROR:searx.engines/d; /ERROR:searx.search.processors/d; /ERROR:searx.searx.search.processor/d; /socket.herror/d; /server_list/d; /gethostbyaddr/d; /add_unresponsive_engine/d; /duckduckgo.*timeout/d; /can't register atexit after shutdown/d; /Unexpected exit from worker/d; /level=warning/d; /httpx/d; /ConnectError/d; /Temporary failure/d; /name resolution/d; /map_httpcore_exceptions/d; /contextlib/d; /raise mapped_exc/d; /await transport/d; /response = await/d; /handle_async_request/d; /gen\.throw/d; /self\.gen\.throw/d; /_send_handling/d; /with map_httpcore/d; /File \"\/usr\/local\/searxng/d; /File \"\/usr\/lib\/python/d; /site-packages\/httpx/d; /\.\<[0-9]* lines\>/d; /^\s*\+/d; /^\s*~\+/d; /Traceback (most recent call last)/,/httpx\.ConnectError:/d'

logs-simple:
	@echo "Following SearXNG logs (cleaned)..."
	docker compose logs -f searxng 2>&1 | grep -vE "radio_browser|ahmia|torch|botdetection|Traceback|socket.herror|server_list|gethostbyaddr|add_unresponsive_engine|duckduckgo.*timeout|ErrorContext.*duckduckgo|httpx.*ConnectError|Temporary failure|name resolution|site-packages/httpx"
