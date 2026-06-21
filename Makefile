.PHONY: gate lint type test replay freeze-check frontend adapter

gate: lint type test replay freeze-check

lint:
	uv run ruff check .
	uv run ruff format --check .

type:
	uv run mypy --strict src/

test:
	uv run pytest -q

replay:
	uv run truth replay fixtures/golden --runs 30 --byte-equal

freeze-check:
	uv run python tools/schema_freeze_check.py

frontend:
	uv run python -m http.server 4173 --directory frontend

adapter:
	uv run truth-verified-chat --store-root adapters/verified-chat --rulepack rulepacks/strict-default/rulepack.json --host 127.0.0.1 --port 8010
