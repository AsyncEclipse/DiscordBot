#!/bin/bash
# Simple script to run the Discord bot with uv (ephemeral dependencies)

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Run the bot using uv with requirements.txt
# --with flag installs packages from requirements.txt ephemerally
uv run --with -r requirements.txt main.py

