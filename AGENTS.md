# AGENTS.md

Guidance for agents working in this repository.

## Project

`internet-speed` is a console utility that measures download throughput
against a URL. It issues sequential HTTP requests, waits for each response and
reports average request time, total downloaded volume and speed in MB/s.

## Layout

- `src/internet_speed/measurement.py` — core measurement logic (no CLI, no
  import of the concrete session class).
- `src/internet_speed/cli.py` — argparse entrypoint and console rendering.
- `src/internet_speed/models.py` — dataclasses for samples and results.
- `tests/` — pytest suite; runs without network access.

## Commands

```bash
uv sync                 # create the environment and install dependencies
uv run ruff check .     # lint
uv run ruff format .    # format
uv run pytest           # run the test suite
uv run internet-speed <URL>   # run the utility
```

Without uv:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m internet_speed <URL>
```

## Conventions

- Python 3.11+, line length 88, type hints on public functions.
- Core logic stays decoupled from `requests.Session` so it can be tested with a
  fake session; pass sessions in rather than constructing them inside logic.
- Follow test-driven development: write a failing test first, then the minimal
  implementation, then refactor.
- Keep the CLI thin; put computation in `measurement.py`.
- Every function has a docstring in Russian describing its purpose, arguments
  and return value. Do not add inline comments that merely restate the code.
