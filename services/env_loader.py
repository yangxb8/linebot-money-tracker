import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_loaded = False


def load_env() -> None:
    """Load variables from a `.env` file in the repo root if present."""
    global _loaded
    if _loaded:
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.debug('python-dotenv not installed; skipping .env load')
        _loaded = True
        return

    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.is_file():
        load_dotenv(env_path)
        logger.debug('Loaded environment from %s', env_path)

    _loaded = True


def require_env_vars(names: list[str]) -> list[str]:
    import os

    return [name for name in names if not os.getenv(name)]
