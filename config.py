# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

class ConfigError(Exception):
    pass

# Always load .env from the folder where THIS file lives
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

def _get(name: str, required: bool = True, default=None):
    value = os.getenv(name, default)
    if required and not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value

OMDB_API_KEY = _get("OMDB_API_KEY")
FIREBASE_API_KEY = _get("FIREBASE_API_KEY")
FIREBASE_DB_URL = _get("FIREBASE_DB_URL")
# Optional – Perplexity can be missing
PERPLEXITY_API_KEY = _get("PERPLEXITY_API_KEY", required=False, default=None)
