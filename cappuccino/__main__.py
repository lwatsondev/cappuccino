import os

import irc3

from cappuccino.settings import _build_irc3_config


def main() -> None:
    cfg = _build_irc3_config()
    if os.environ.get("DEBUG", "").lower() in ("1", "true"):
        cfg["debug"] = True
        cfg["raw"] = True
    bot = irc3.IrcBot.from_config(cfg)
    bot.run(forever=True)


if __name__ == "__main__":
    main()
