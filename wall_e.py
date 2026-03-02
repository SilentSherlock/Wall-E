from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running directly via `python wall_e.py` without editable install.
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

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