# holman-linux-python

Python SDK and `holmanctl` CLI for controlling Holman Bluetooth tap timers (CO3015, BTX1/CO3011) on Linux via BlueZ.

## Tech Stack
- Python 3, built on the `gatt` library (which wraps BlueZ's D-Bus API)
- `python3-dbus` comes from apt, not PyPI, and is not in `dependencies`
- Managed with uv; `pyproject.toml` (hatchling backend) is the only packaging config; published to PyPI as `holman`

## Layout
- `holman/holman.py` — the whole SDK: `TapTimerManager` (discovery), `TapTimer` (connection + control), and the two listener base classes
- `holman/__init__.py` — public API re-exports; update it when adding public classes
- `holmanctl.py` — demo/test CLI, installed as the `holmanctl` console script
- `tests/` — pytest suite; `conftest.py` swaps `gatt` for an in-memory fake (real `gatt` calls `sys.exit` on import without dbus)
- `typings/gatt/` — pyrefly stub pinning `gatt` to its BlueZ backend (it picks a backend at runtime, which the checker can't narrow)

## Development
- Before finishing a change, run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run pyrefly check`
- CI (`.github/workflows/ci.yml`) runs the same checks, with pytest on Python 3.9 and 3.14; keep `requires-python` and that matrix in sync
- Ruff formats the Python snippets in `README.md` too
- Tests run with `--import-mode=importlib`, so share test helpers as fixtures in `conftest.py`, not by importing modules from `tests/`
- Tests cover logic only; when adding a `gatt` API call, add it to the fakes in `tests/conftest.py`
- Real verification needs hardware: a tap timer in range, `bluetoothd` running, and root (`sudo holmanctl --discover`, `--connect <MAC>`)
- Event-driven: nothing happens until `TapTimerManager.run()` starts the GLib loop; results arrive through listener callbacks, not return values

## Device Protocol
- Supported models are identified by GATT service UUID — `holman/holman.py:90-95`. A new model means adding its UUID to `SERVICE_UUIDS`
- Discovery also filters on the BLE alias `'Tap Timer'` — `holman/holman.py:41`
- Start/stop write a 4-byte value to the manual characteristic (byte 0 = on/off, byte 3 = minutes, capped at 255) — `holman/holman.py:228-243`
- On/off state is the last byte of the state characteristic — `holman/holman.py:217-221`
- Battery level is not decoded yet (`battery_level()` always returns `None`)

## Releasing
- Bump `version` in `pyproject.toml`, then `uv lock`, `uv build` and `uv publish`

## Python Version

Python 3.9 minimum (`requires-python` in pyproject.toml; ruff and pyrefly also target 3.9). Use the newest syntax 3.9 supports:
- `list[str]` instead of `List[str]`
- `dict[str, Any]` instead of `Dict[str, Any]`
- `tuple[int, str]` instead of `Tuple[int, str]`
- `X | None` instead of `Optional[X]` only in annotations, with `from __future__ import annotations` at the top of the module; `|` between types fails at runtime on 3.9 anywhere else (e.g. `isinstance`, aliases)
- No `match` statements (3.10) or `type X = ...` aliases (3.12); use `if`/`elif` and plain `X = ...` alias assignments (`typing.TypeAlias` is 3.10+, and `typing_extensions` isn't a dependency)

## Manage packages

This project uses uv. Do not use pip, pip-tools, poetry, or conda.

- Add runtime dependency: `uv add <package>` (writes to `[project.dependencies]`)
- Add dev dependency: `uv add --dev <package>` (writes to `[dependency-groups]` per PEP 735)
- Remove dependency: `uv remove <package>`
- Sync environment from lockfile: `uv sync`
- Regenerate lockfile from constraints: `uv lock`
- Upgrade locked versions: `uv lock --upgrade`
- Commit `uv.lock` to version control (current uv guidance is to commit it for applications, CLIs, and libraries)

## Run code

Always use `uv run` to execute Python code and tools. Never call `python`, `pytest`, `ruff`, or other tools directly. They may not resolve to the project's virtual environment.

- Run a script: `uv run python script.py`
- Run a module: `uv run python -m module_name`
- Run a tool: `uv run pytest`, `uv run ruff check .`
- One-off tool (not a project dependency): `uvx <tool>`

## Test code

- Framework: pytest
- Run tests: `uv run pytest`
- Test files go in `tests/` at the project root
- Test file naming: `test_*.py`
- Test function naming: `test_*`
- No `__init__.py` needed in `tests/`
- Coverage: `uv add --dev coverage`, then `uv run coverage run -m pytest` and `uv run coverage report`

## Lint and format code

- Tool: ruff (handles both linting and formatting)
- Lint: `uv run ruff check .`
- Lint and auto-fix: `uv run ruff check --fix .`
- Format: `uv run ruff format .`
- Check formatting: `uv run ruff format --check .`
- Configuration lives in `pyproject.toml` under `[tool.ruff]`

## Check types

- Tool: pyrefly (preferred), ty, or mypy
- Run: `uv run pyrefly check`, `uv run ty check`, or `uv run mypy .`
- Configuration lives in `pyproject.toml` under `[tool.pyrefly]`, `[tool.ty]`, or `[tool.mypy]`

## Avoid these practices

- Do not create or activate virtual environments manually. uv manages `.venv/` automatically.
- Do not install packages globally or with `pip install`.
- Do not create `requirements.txt` for dependency management. Use `pyproject.toml` and `uv.lock`.
- Do not run `python setup.py` commands.
- Do not add dependencies to pyproject.toml by hand. Use `uv add`.
- If you must edit pyproject.toml directly, write dev dependencies under `[dependency-groups]` (PEP 735), not the legacy `[tool.uv.dev-dependencies]` table.

## Development Standards

### Git Workflow
- Branch names: `feature/description` or `fix/description`
- Commit messages: Follow conventional commits
- PR required before merge
- All CI/CD checks must pass
- Minimum 1 approval required

### Testing Requirements
- Minimum 80% code coverage
- All critical paths must have tests

