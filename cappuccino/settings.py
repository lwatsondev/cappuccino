import os
from pathlib import Path

from dynaconf import Dynaconf

_BASE_DIR = Path(__file__).parent
_CONFIG_DIR = os.getenv("ROOT_PATH_FOR_DYNACONF", _BASE_DIR / "config")

settings = Dynaconf(
    envvar_prefix="CAPPUCCINO",
    root_path=_CONFIG_DIR,
    settings_files=[str(_BASE_DIR / "config" / "default.toml"), "*.toml"],
    load_dotenv=True,
)


_DYNACONF_INTERNAL = frozenset({"LOAD_DOTENV", "RENAMED_VARS"})


def _flatten_section(cfg: dict, section: dict, prefix: str) -> None:
    leaf: dict = {}
    for key, value in section.items():
        if isinstance(value, dict):
            _flatten_section(cfg, value, f"{prefix}.{key.lower()}")
        else:
            leaf[key.lower()] = value
    if leaf:
        cfg[prefix] = leaf


def _build_irc3_config() -> dict:
    cfg: dict = {}
    for key, value in settings.as_dict().items():
        if key.endswith("_FOR_DYNACONF") or key in _DYNACONF_INTERNAL:
            continue
        if isinstance(value, dict):
            _flatten_section(cfg, value, key.lower())
        else:
            cfg[key.lower()] = value

    # irc3 uses these for configparser-style interpolation. Harmless when set.
    cfg.setdefault("hash", "#")
    cfg.setdefault("#", "#")
    return cfg
