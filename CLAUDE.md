# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

cappuccino is an [irc3](https://github.com/gawel/irc3)-based IRC bot, built as a collection of plugins primarily
for `#rice@irc.rizon.net`. It runs on Python 3.14, uses SQLAlchemy/Alembic against PostgreSQL, and ships as a
Docker Compose stack.

## Commands

All commands run through `uv` and Docker Compose. There is no bare `pytest`/`python` workflow, as the app and its
tests expect a running Postgres instance.

```sh
make setup   # uv sync --all-groups && uv run prek install (installs git hooks)
make lint    # uv run prek run --all-files --skip pytest (ruff, yamllint, hadolint, shellcheck, etc.)
make run     # docker compose -f docker/compose.yaml up --build
make test    # docker compose ... --profile test run --build --rm test  (runs `uv run pytest` in a container)
make clean   # tear down containers/volumes, wipe __pycache__/.pytest_cache/.ruff_cache
```

- `make run` requires `docker/.env` (copy from `docker/.env.example` and set `CAPPUCCINO_HOST` etc).
- To run a single test inside the container: edit the `test` service command or run
  `docker compose -f docker/compose.yaml --profile test run --build --rm test uv run pytest tests/plugins/test_ircdb.py -k some_test`.
- Tests use `pytest-postgresql`: a real Postgres instance is spun up per session (`postgresql_proc` fixture) and
  torn down via `DatabaseJanitor`. There's no SQLite/mock DB fallback.
- Migration tests (`tests/test_migrations.py`) run Alembic against a separate `test_migrations` database
  (`migration_db_url` / `alembic_cfg` fixtures in `tests/conftest.py`).
- Pre-commit hooks are managed by `prek` (a Rust pre-commit-style tool), configured in `prek.toml`, not
  `.pre-commit-config.yaml`.

## Architecture

**Bootstrapping** (`cappuccino/__main__.py`): `sentry.init()` -> `settings._build_irc3_config()` converts the
Dynaconf settings tree into a flat irc3-style config dict -> `Bot.from_config(cfg)` -> `bot.run(forever=True)`.

**Settings** (`cappuccino/settings.py`): Dynaconf loads `cappuccino/config/default.toml` plus any `*.toml` in the
configured root (`ROOT_PATH_FOR_DYNACONF`, mounted as `/config` in the container), with `CAPPUCCINO_`-prefixed env
vars and `.env` support. `_build_irc3_config()` lowercases and flattens nested sections (e.g. `[plugins.rice]`
becomes irc3 config key `plugins.rice`) since irc3 expects a flat dict rather than nested config.

**Bot & database** (`cappuccino/bot.py`, `cappuccino/database.py`): `Bot` subclasses `irc3.IrcBot` and lazily
attaches an `IrcDatabase` (a thin SQLAlchemy session wrapper) as `bot.ircdb` the first time plugins are included.
`IrcDatabase.get/set/del_user_value` and the `*_channel_value` equivalents are a generic key-value interface over
the `User`/`Channel` ORM columns. Most plugins persist state by calling these rather than writing raw queries.

**Plugins** (`cappuccino/plugins/`): each module is an irc3 plugin (`@irc3.plugin`) subclassing the shared
`Plugin` base in `cappuccino/plugins/__init__.py`. The base class wires up a logger (`irc3.<module>`), an async
HTTP client (`niquests.AsyncSession`, `self._http`), and a `self.config` property that reads
`settings.PLUGINS.<plugin_name>` (module name-derived, e.g. `cappuccino/plugins/rice.py` -> `settings.PLUGINS.rice`).
New plugins should follow this pattern rather than reading `settings` directly.

**Database models & migrations** (`cappuccino/db/`): SQLAlchemy models live under `db/models/` (`ircdb.py` with
`User`/`Channel`, plus `ai.py` and `triggers.py`), all declared against the shared `BaseModel` in `db/models/__init__.py`.
Alembic lives under `db/alembic/` (env at `db/alembic/env.py`, revisions in `db/alembic/versions/`) and is driven
by `alembic.ini` at the repo root. When adding/changing a model, add a corresponding Alembic revision.

**Sentry** (`cappuccino/sentry.py`): initialized only if a DSN is configured, and filters out irc connection-reset
noise and `niquests`/timeout exceptions via `before_send` before sending events.

**Versioning** (`cappuccino/util/meta.py`): the running version/commit shown in the bot's `User-Agent` and Sentry
release comes from `META_VERSION`/`META_COMMIT` env vars, injected at Docker build time (see `release.yml` and
`docker/Dockerfile`), not read from `pyproject.toml` at runtime.

## Releases

- Git tags are bare version numbers (`1.27.1`), never a `v` prefix.
- Version bumps update every file that declares the version and regenerate
  every lockfile that goes with it, across all package managers in the repo.
- The bump is always its own isolated commit + tag containing only those
  files, made after the commits being released, and never mixed with
  other changes.

## Python conventions

- `from module import Name`, not `import module` + `module.Name` at call
  sites, including type annotations. Import needed submodules directly with
  an alias rather than keeping the top-level package import. Exception: keep
  the `import module` + `module.Name` form when the bare name would shadow a
  builtin or read ambiguously out of context (e.g. `sys.exit`,
  `subprocess.run`, `os.environ`).
- No single-character variable names anywhere, including loop and
  comprehension variables. Name caught exceptions `exc`, never `e`.
- f-strings for all interpolation, including logging calls, never %-style.
- Don't manually sort or group imports: ruff handles it. Ignore IDE
  import-sort warnings.
- Don't flag or "fix" unusual-looking syntax that already exists (e.g.
  `except A, B:`). If it runs, it's valid here.
- New source files carry the project's license header, matching the exact
  format used by existing files in the repo (SPDX or otherwise). In shell
  scripts, separate the header block from the shebang and the following code
  with a blank line on each side.
- Install dependencies with `uv sync`, update them with
  `uv sync --upgrade --all-groups`.
