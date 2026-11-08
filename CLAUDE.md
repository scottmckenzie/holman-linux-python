# holman-linux-python

Python SDK and `holmanctl` CLI for controlling Holman Bluetooth tap timers (CO3015, BTX1/CO3011, BX2 MK1/CO3112, and experimentally BX1/CO3111) on Linux via BlueZ.

## Tech Stack
- Python 3, built on the `gatt` library (which wraps BlueZ's D-Bus API)
- `python3-dbus` comes from apt, not PyPI, and is not in `dependencies`

## Layout
- `holman/__init__.py` — public API re-exports; update it when adding public classes
- `tests/` — pytest suite; `conftest.py` swaps `gatt` for an in-memory fake (real `gatt` calls `sys.exit` on import without dbus)
- `typings/gatt/` — pyrefly stub pinning `gatt` to its BlueZ backend (it picks a backend at runtime, which the checker can't narrow)

## Development
- Before finishing a change, run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run pyrefly check`
- CI (`.github/workflows/ci.yml`) runs the same checks, with pytest on Python 3.11 and 3.14; keep `requires-python` and that matrix in sync
- Ruff formats the Python snippets in `README.md` too
- Tests run with `--import-mode=importlib`, so share test helpers as fixtures in `conftest.py`, not by importing modules from `tests/`
- Tests cover logic only; when adding a `gatt` API call, add it to the fakes in `tests/conftest.py`
- Real verification needs hardware: a tap timer in range, `bluetoothd` running, and root (`sudo holmanctl --discover`, `--connect <MAC>`)
- Event-driven: nothing happens until `TapTimerManager.run()` starts the GLib loop; results arrive through listener callbacks, not return values

## Device Protocol
- Supported models are identified by GATT service UUID. A new model means adding its UUID to `SERVICE_UUIDS`
- Discovery also filters on the exact BLE alias in `TapTimer.ALIASES` (`Tap Timer`, `BX1`, `BX2`)
- If the service has the `c001` unlock characteristic (BX1/BX2), `services_resolved` writes `AE 8E` to it and only reports `connect_succeeded` once that write is acknowledged
- Start/stop write a 4-byte value to the manual characteristic (byte 0 = on/off, byte 1 = outlet: 0 = zone 1, 1 = zone 2 on BX2, byte 3 = minutes, capped at 255)
- On/off state is the last byte of the state characteristic
- Battery level is not decoded yet (`battery_level()` always returns `None`)

## Releasing
- Bump `version` in `pyproject.toml` and run `uv lock`; merge that via PR
- Then tag the merge commit with the bare version (`git tag 0.2.0`, no `v` prefix) and push the tag. `.github/workflows/publish.yml` builds and publishes to PyPI with trusted publishing (`pypi` environment); it fails if the tag doesn't match `version`

## Python Version

Python 3.11 minimum (`requires-python` in pyproject.toml; ruff and pyrefly also target 3.11). Python 3.10 reached end of life in October 2026. Use the newest syntax 3.11 supports:
- `X: TypeAlias = ...` (from `typing`) for type aliases; `type X = ...` is 3.12+
- Match statements for enum/type dispatch where appropriate
- `typing.Self` for methods returning their own class, and `tomllib` for reading TOML

## Manage packages

This project uses uv. Do not use pip, pip-tools, poetry, or conda.

## Run code

Always use `uv run` to execute Python code and tools. Never call `python`, `pytest`, `ruff`, or other tools directly. They may not resolve to the project's virtual environment.

## Test code

- Coverage: `uv add --dev coverage`, then `uv run coverage run -m pytest` and `uv run coverage report`

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

### GitHub Actions
- Pin every action to a full commit SHA, with the release tag in a comment:
  `uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`. Never use a tag or branch
  (`@v7`, `@main`), which can be moved to different code
- Look up a release's SHA with `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`, and update the
  SHA and the comment together

### Testing Requirements
- Minimum 80% code coverage
- All critical paths must have tests

