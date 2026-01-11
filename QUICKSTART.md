# Quick Start Guide

## Running with uv (Ephemeral Dependencies)

The simplest way to run this bot is using `uv`, which installs dependencies in an ephemeral virtual environment.

### macOS/Linux:
```bash
./run.sh
```

### Windows:
```cmd
run.bat
```

### Manual (if scripts don't work):
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run the bot (uv automatically creates venv and installs deps)
uv run main.py
```

## Configuration

Before running, make sure you have a `config.json` file in the project root with:
```json
{
  "token": "YOUR_DISCORD_BOT_TOKEN",
  "game_number": 0,
  "gamestate_path": "path/to/gamestate/files"
}
```

## How it works

- `uv run` automatically creates a temporary virtual environment
- Installs all dependencies from `requirements.txt`
- Runs the script
- Cleans up when done (dependencies are ephemeral)

No permanent changes to your system Python environment!

Scratch that, do this instead after defining a venv
```
source discordbot/bin/activate
uv pip install -r requirements.txt
uv run main.py
```
