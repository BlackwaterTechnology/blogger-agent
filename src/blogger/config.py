import tomllib
from pathlib import Path
from loguru import logger

# Use the project root to find blogger.toml
CONFIG_PATH = Path(__file__).parent.parent.parent / "blogger.toml"

def load_config():
    if not CONFIG_PATH.exists():
        logger.debug(f"Config file not found at {CONFIG_PATH}")
        return {}
    try:
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {CONFIG_PATH}: {e}")
        return {}

def get_wechat_collections(content_type="article", account="default"):
    config = load_config()
    try:
        acct_config = config.get("platforms", {}).get("wechat", {}).get("accounts", {}).get(account, {})
        key = f"{content_type}_collections"
        return acct_config.get(key, [])
    except Exception as e:
        logger.warning(f"Error reading wechat collections config: {e}")
        return []

def get_all_wechat_collections(account="default"):
    """Returns a combined list of all collections for a WeChat account."""
    config = load_config()
    try:
        acct_config = config.get("platforms", {}).get("wechat", {}).get("accounts", {}).get(account, {})
        return acct_config.get("article_collections", []) + acct_config.get("video_collections", [])
    except Exception as e:
        logger.warning(f"Error reading all wechat collections: {e}")
        return []
