from __future__ import annotations

import argparse

from walle_bot.bot import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Wall-E Telegram moderation bot")
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to YAML config file",
    )
    args = parser.parse_args()
    run(config_path=args.config)


if __name__ == "__main__":
    main()
