.PHONY: gate lint type test replay freeze-check

gate: lint type test replay freeze-check

lint:
	uv run ruff check .
	uv run ruff format --check .

type:
	uv run mypy --strict src/

test:
	uv run pytest -q

replay:
	@echo "replay: stubbed until M2"

freeze-check:
	uv run python tools/schema_freeze_check.py
