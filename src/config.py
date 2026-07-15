"""
config.py
---------
Centralized application configuration.

All configurable values are loaded from environment variables (via a `.env`
file in development, or real environment variables in production). No
secrets or environment-specific values are ever hardcoded here.

Usage:
    from src.config import settings
    print(settings.MODEL_NAME)
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load variables from a .env file if one is present. This is a no-op in
# production environments where real env vars are already set (e.g. Docker,
# Streamlit Cloud secrets, Heroku config vars, etc.).
load_dotenv()


def _get_bool(key: str, default: bool) -> bool:
    """Parse a boolean-ish environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    """
    Immutable application settings.

    MODEL / GENERATION
    -------------------
    The project uses GPT-Neo (1.3B) from EleutherAI, as specified in the
    original project report. Two execution modes are supported:

    1. LOCAL mode (default): the model and tokenizer are downloaded from
       Hugging Face and run locally via `transformers` + `torch`. This
       requires no API key but needs a reasonable amount of RAM/VRAM and
       disk space (~5 GB) the first time it runs.

    2. INFERENCE API mode: if `USE_INFERENCE_API=true` and a valid
       `HUGGINGFACEHUB_API_TOKEN` is provided, generation is delegated to
       the Hugging Face Inference API instead of loading the model
       in-process. This is useful for lightweight deployments (e.g. small
       cloud instances) that cannot hold a 1.3B parameter model in memory.

    The API token (when used) is NEVER hardcoded -- it is always read from
    the environment / `.env` file.
    """

    # --- Model configuration ---
    MODEL_NAME: str = os.getenv("MODEL_NAME", "EleutherAI/gpt-neo-1.3B")
    TOKENIZER_NAME: str = os.getenv("TOKENIZER_NAME", "EleutherAI/gpt-neo-1.3B")

    # --- Execution mode ---
    USE_INFERENCE_API: bool = _get_bool("USE_INFERENCE_API", False)
    HUGGINGFACEHUB_API_TOKEN: str = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")

    # --- Generation hyperparameters (tunable, per the report's methodology) ---
    MAX_NEW_TOKENS: int = _get_int("MAX_NEW_TOKENS", 200)
    TEMPERATURE: float = _get_float("TEMPERATURE", 0.9)
    TOP_K: int = _get_int("TOP_K", 50)
    TOP_P: float = _get_float("TOP_P", 0.95)
    REPETITION_PENALTY: float = _get_float("REPETITION_PENALTY", 1.3)
    NO_REPEAT_NGRAM_SIZE: int = _get_int("NO_REPEAT_NGRAM_SIZE", 3)

    # --- Prompt engineering ---
    STOP_DELIMITER: str = os.getenv("STOP_DELIMITER", "---")

    # --- App metadata ---
    APP_TITLE: str = os.getenv("APP_TITLE", "Personalized Email Generator")
    APP_ICON: str = os.getenv("APP_ICON", "📧")

    # --- Device ---
    DEVICE: str = os.getenv("DEVICE", "auto")  # "auto" | "cpu" | "cuda"


settings = Settings()
