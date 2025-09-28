"""
Main entry point for Bookwyrm's Hoard CLI.
"""

import os
from pathlib import Path
from bookwyrms.cli import cli

def load_env_file() -> None:
    """Load environment variables from .env file if it exists."""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value

if __name__ == '__main__':
    load_env_file()
    cli()