# Wall-E Telegram Moderation Bot

Python Telegram group moderation bot with configurable anti-ad rules.

## Features

- Monitor selected group chats only (configured by env `MONITORED_CHAT_IDS`)
- Whitelist exempt users (`WHITELIST_USER_IDS`)
- Detect ad-like behavior when the same user sends duplicate content or links in a short time window
- On violation: delete duplicate messages, warn user, mute for configurable duration
- Auto-kick user after configurable violation count
- `/start` in group registers that group into managed group list (stored in SQLite, owner/admin only)
- `/release @username` clears violation records of the target user in current group (owner/admin only)
- `/list` shows all commands and required permissions
- Scheduler sends current Beijing time report to all managed groups every 8 hours
- `/whoami` command returns caller identity info

## Project structure

- `main.py`: root entrypoint, supports direct startup with `python main.py`
- `src/walle_bot/bot.py`: app wiring and handler registration
- `src/walle_bot/config.py`: YAML + env config loader
- `src/walle_bot/services/moderation.py`: moderation actions
- `src/walle_bot/services/state.py`: duplicate detection and SQLite-backed violation state
- `config/settings.yaml`: non-sensitive policy config
- `.env` (local): token/chat/user sensitive data
- `tests/`: pytest test suite

## Setup (Windows PowerShell)

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Create env file:

```powershell
Copy-Item .env.example .env
```

3. Edit `.env` with real values:

```env
BOT_TOKEN=your-real-token
MONITORED_CHAT_IDS=-1001234567890
WHITELIST_USER_IDS=12345678
```

4. Adjust moderation values in `config/settings.yaml` if needed.
5. Optional: change `storage.sqlite_db_path` (default: `data/walle.db`).

## Setup (Ubuntu / Linux)

1. Install Python 3 and pip (if not installed):

```bash
sudo apt update
sudo apt install -y python3 python3-pip
```

2. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

3. Create env file:

```bash
cp .env.example .env
```

4. Edit `.env` with real values:

```env
BOT_TOKEN=your-real-token
MONITORED_CHAT_IDS=-1001234567890
WHITELIST_USER_IDS=12345678
```

5. Adjust moderation values in `config/settings.yaml` if needed.
6. Optional: change `storage.sqlite_db_path` (default: `data/walle.db`).

## Run

### Windows

```powershell
python main.py --config config/settings.yaml
```

### Ubuntu / Linux

```bash
python3 main.py --config config/settings.yaml
```

## Logs

- Runtime logs are written under `logs/` in the project root.
- Logs rotate daily (`walle.log.YYYY-MM-DD`) and only keep warning/error level entries.

## Test

### Windows

```powershell
python -m pytest
```

### Ubuntu / Linux

```bash
python3 -m pytest
```
