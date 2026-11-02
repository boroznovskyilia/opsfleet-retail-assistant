.PHONY: docs check progress setup test run doctor evaluate verify

docs:
	@if command -v tree >/dev/null 2>&1; then tree docs; else find docs -type f | sort; fi

check:
	python3 -m unittest discover -s scripts -p 'test_*.py'
	python3 scripts/check_docs.py
	python3 scripts/check_progress.py

progress:
	python3 scripts/check_progress.py

setup:
	uv sync --locked --python 3.12

test:
	.venv/bin/python -m unittest discover -s tests -v

run:
	.venv/bin/python -m retail_assistant

doctor:
	.venv/bin/python -m retail_assistant --doctor

evaluate:
	.venv/bin/python -m retail_assistant.evaluation

verify: check test
