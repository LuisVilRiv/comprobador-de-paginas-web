.PHONY: lint lint-py lint-js typecheck format check all

# ── Atajos principales ────────────────────────────────────────────────────────

all: check          ## Ejecuta lint + typecheck completo

check: lint typecheck  ## Lint + typecheck (sin modificar ficheros)

# ── Python (ruff + mypy) ──────────────────────────────────────────────────────

lint-py:            ## Lint Python con ruff
	ruff check .

typecheck:          ## Typecheck Python con mypy
	mypy config/ shared/ scraper/ docker/dashboard/api/ docker/scraper/

format:             ## Formatear Python con ruff (modifica ficheros)
	ruff format .
	ruff check --fix .

# ── JavaScript (eslint) ──────────────────────────────────────────────────────

lint-js:            ## Lint JavaScript con eslint
	cd docker/dashboard && npx eslint frontend/ server.js

# ── Combinados ───────────────────────────────────────────────────────────────

lint: lint-py lint-js  ## Lint completo (Python + JavaScript)

help:               ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
