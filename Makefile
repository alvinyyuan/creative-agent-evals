MODEL ?= claude-haiku-5-5
PY := .venv/bin/python

setup:  ## submodule, both Node builds, Python venv
	git submodule update --init
	cd mcp/piclumen-api-mock && npm install --no-audit --no-fund && npm run build
	cd mcp/piclumen-mcp-server && npm install --no-audit --no-fund && npm run build
	uv venv -p 3.12 .venv && uv pip install -p .venv -r requirements.txt

eval:   ## run all 40 tasks, then score with the LLM judge
	$(PY) -m evals.run --model $(MODEL)
	$(PY) -m evals.score --label $(MODEL) --judge

score:  ## re-score saved traces (judge verdicts are cached)
	$(PY) -m evals.score --label $(MODEL) --judge

tasks:  ## regenerate evals/tasks.jsonl from evals/make_tasks.py
	$(PY) evals/make_tasks.py

.PHONY: setup eval score tasks
