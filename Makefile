.PHONY: help lint test

.DEFAULT: help
help:
	@echo "make lint"
	@echo "  run pylint and mypy"

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	mypy ./src
