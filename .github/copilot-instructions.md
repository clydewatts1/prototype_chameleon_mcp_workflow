# GitHub Copilot Instructions for Chameleon MCP Workflow 🦎🔧

## Purpose
Short, action-oriented guidance for AI coding agents (and humans using them) to be productive in this repo.

## Big Picture (what matters) 💡
- This repo implements a Model Context Protocol (MCP) **workflow engine** (FastAPI) that orchestrates AI agents: see `chameleon_workflow_engine/server.py` (entrypoint) and `chameleon_workflow_engine/__init__.py` (architecture notes).
- Data persistence uses a deliberate **air-gapped two‑tier** SQLAlchemy design:
  - **Tier 1 (Templates)**: read-only blueprints — see `database/models_template.py` and `database/README.md`.
  - **Tier 2 (Instances)**: runtime, read/write — see `database/models_instance.py` and tests in `tests/test_schema_generation.py`.
- Templates are instantiated into isolated instances; changes to Tier 1 should not affect running Tier 2 data unless explicitly re-imported.

## What to know about common flows 🔁
- Workflow templates are managed via `tools/workflow_manager.py`:
  - Export YAML uses name-based identifiers (not UUIDs): `role_name`, `interaction_name`, `component_name`.
  - Importing YAML will **delete existing workflow** with the same name (cascade delete) then recreate — expect transactional behavior and rollback on failure.
  - DOT export creates visual graphs; Graphviz (`dot`) required to render PNGs from `.dot` files.
- FastAPI server runs with:
  - `python -m chameleon_workflow_engine.server` or
  - `uvicorn chameleon_workflow_engine.server:app --reload --port 8000`
- Verify developer environment with `python verify_setup.py` and run tests with `pytest`.

## Project-specific conventions & patterns ⚙️
- Two-tier isolation: use separate declarative bases (`TemplateBase` vs `InstanceBase`) and ensure no table overlap. Tests check this explicitly.
- UUIDs are generated client-side (`default=uuid.uuid4`) and used as primary keys in models.
- AI introspection: tables and columns include comments for agent reasoning. Preserve or improve comments when touching schema.
- YAML format: hierarchical `workflow` + sections `roles`, `interactions`, `components`, `guardians`. Use names for cross-references (see `tools/workflow_manager.py`).
- Role types (ALPHA, BETA, OMEGA, EPSILON, TAU) and guardian types (CERBERUS, PASS_THRU, etc.) are defined in `database/enums.py` and used across models and YAML.

## Tests & Quality Checks ✅
- Essential tests: `tests/test_schema_generation.py` validates schema isolation, expected tables, column presence and comments. Use it to validate DB model changes.
- Run full test suite with `pytest` and check coverage with `pytest --cov=chameleon_workflow_engine --cov=database`.
- Pre-commit style: formatting and static analysis tools used are **Black**, **Ruff**, and **MyPy**. CI expects their use (`black --check .`, `ruff check .`, `mypy ...`).

## Integration & env details 🔌
- `.env.example` contains placeholders for external AI service keys (e.g., Claude). Copy to `.env` and configure.
- Project expects to be run locally with SQLite by default. Database URLs are passed to `DatabaseManager(template_url=...)` or `DatabaseManager(instance_url=...)`.

## How AI agents should help (practical guidelines) 🤖
- When proposing code changes, reference exact files and tests to update (e.g., "Update `Template_Components` to include X; update `tests/test_schema_generation.py` to assert X").
- For schema changes:
  - Update model comments and tests that assert comments exist.
  - Keep Tier 1 / Tier 2 separation; do not add cross-tier foreign keys unless the design explicitly requires it and tests are updated.
- For CLI behavior (YAML import/export): preserve name-based references and cascade-delete semantics; mention potential data-loss impact in PR descriptions.
- Use examples in `README.md` and `database/README.md` when writing docs or tests.

## Quick checklist to include in PR descriptions 🧾
1. Describe behavior change and reason (brief). 🔍
2. List updated files and updated or new tests. ✅
3. Mention any DB migration or manual steps needed (if applicable). 🧱
4. For schema edits, confirm `tests/test_schema_generation.py` updated and passing. 🧪
5. If altering YAML import semantics, show an example YAML snippet. 📄

---

If any part of this guidance is unclear or missing examples you'd like automated, tell me which area (schema, YAML, CLI, server) and I'll add or expand the instructions. ✍️