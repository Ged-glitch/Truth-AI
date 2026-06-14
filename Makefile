.PHONY: gate lint type test replay freeze-check frontend

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
