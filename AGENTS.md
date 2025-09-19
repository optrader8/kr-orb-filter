# Repository Guidelines

## Project Structure & Module Organization
Core code lives in `src/`: `config.py` centralizes defaults, `data/` handles ingestion, `features/` calculates NR7/ORB metrics, `screen/` and `backtest/` drive workflows, `notify/` and `store/` cover alerts and persistence, while `cli.py` and optional `app.py` expose entrypoints. Use `notebooks/` for experiments and promote reusable logic back into `src/` once validated. Keep `.env.example` and `requirements.md` updated whenever dependencies or runtime knobs change.

## Build, Test, and Development Commands
Create a clean virtualenv (`python -m venv .venv` + activation) before installing. Install dependencies with `pip install -r requirements.txt`. Run key flows with `python -m src.cli screener daily`, `python -m src.cli monitor --provider intraday --simulate`, and `python -m src.cli backtest --strategy orb_nr7 --universe KOSPI200`; keep CLI flags synchronized with `config.py`.

## Coding Style & Naming Conventions
Follow PEP 8, four-space indentation, snake_case for modules and functions, and CapWords for classes. Annotate public functions with type hints and keep feature functions pure; shared constants belong in `config.py`. Use concise docstrings where behavior is not obvious and ensure CLI option names mirror user-facing terminology.

## Testing Guidelines
Use `pytest` and mirror `src/` layout under `tests/` (e.g., `tests/features/test_nr7.py`). Mock external data providers and seed deterministic replay fixtures for ORB simulations. Target >85% coverage for new modules and run `pytest` before submitting changes.

## Commit & Pull Request Guidelines
Adopt Conventional Commit prefixes such as `feat(screen): add liquidity filter`. Each pull request needs a brief problem statement, change summary, test evidence (`pytest` output or monitor logs), and notes for config or schema updates. Link related issues and request reviews from owners of data, screening, or infra components when touched.

## Environment & Security Notes
Do not commit `.env`; generate it from `.env.example` and describe new keys inline. Secrets for Slack, Telegram, or database access must stay in env vars or a secrets store, and optional dependencies (e.g., TA-Lib) should degrade gracefully with guarded imports and install notes in `requirements.md`.