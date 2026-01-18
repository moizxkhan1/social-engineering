from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _get_optional_int(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return None
    return int(raw)


def _get_optional_bool(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return None
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data.sqlite3")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-nano")

    # Reddit (can be configured later)
    reddit_client_id: str | None = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret: str | None = os.getenv("REDDIT_CLIENT_SECRET")
    reddit_username: str | None = os.getenv("REDDIT_USERNAME")
    reddit_password: str | None = os.getenv("REDDIT_PASSWORD")
    reddit_user_agent: str = os.getenv("REDDIT_USER_AGENT", "SocialIntelEngine/0.1")
    reddit_min_interval_s: float = _get_float("REDDIT_MIN_INTERVAL_S", 1.0)

    # Proxy settings
    proxy_enabled: bool = _get_bool("PROXY_ENABLED", False)
    proxy_list_url: str | None = os.getenv("PROXY_LIST_URL")
    proxy_refresh_interval_s: float = _get_float("PROXY_REFRESH_INTERVAL_S", 300.0)
    proxy_default_scheme: str = os.getenv("PROXY_DEFAULT_SCHEME", "socks5")
    proxy_pool_size: int = _get_int("PROXY_POOL_SIZE", 20)
    proxy_cache_path: str = os.getenv("PROXY_CACHE_PATH", "proxy_cache.json")
    proxy_cache_enabled: bool = _get_bool("PROXY_CACHE_ENABLED", True)

    # Proxifly (optional proxy source; server-side only)
    proxifly_api_key: str | None = os.getenv("PROXIFLY_API_KEY")
    proxifly_protocol: str = os.getenv("PROXIFLY_PROTOCOL", "socks5")
    proxifly_anonymity: str | None = os.getenv("PROXIFLY_ANONYMITY")
    proxifly_country: str | None = os.getenv("PROXIFLY_COUNTRY")
    proxifly_https: bool | None = _get_optional_bool("PROXIFLY_HTTPS")
    proxifly_speed_ms: int | None = _get_optional_int("PROXIFLY_SPEED_MS")
    proxifly_max_retries: int = _get_int("PROXIFLY_MAX_RETRIES", 3)
    proxifly_min_backoff_s: float = _get_float("PROXIFLY_MIN_BACKOFF_S", 1.0)
    proxifly_max_backoff_s: float = _get_float("PROXIFLY_MAX_BACKOFF_S", 30.0)
    proxifly_rate_limit_cooldown_s: float = _get_float("PROXIFLY_RATE_LIMIT_COOLDOWN_S", 60.0)
    # Avoid blocking startup forever when rate-limited.
    proxifly_max_wait_s: float = _get_float("PROXIFLY_MAX_WAIT_S", 5.0)

    # Browser-based scraping (Playwright)
    browser_enabled: bool = _get_bool("BROWSER_ENABLED", True)
    browser_headless: bool = _get_bool("BROWSER_HEADLESS", True)
    browser_timeout_ms: int = _get_int("BROWSER_TIMEOUT_MS", 30000)

    confidence_threshold: float = _get_float("CONFIDENCE_THRESHOLD", 0.7)
    max_discovery_pages: int = _get_int("MAX_DISCOVERY_PAGES", 5)
    max_posts_per_subreddit: int = _get_int("MAX_POSTS_PER_SUBREDDIT", 50)
    max_comments_per_post: int = _get_int("MAX_COMMENTS_PER_POST", 10)
    max_discovered_subreddits: int = _get_int("MAX_DISCOVERED_SUBREDDITS", 50)
    max_llm_sources: int = _get_int("MAX_LLM_SOURCES", 40)
    llm_batch_size: int = _get_int("LLM_BATCH_SIZE", 5)
    max_source_chars: int = _get_int("MAX_SOURCE_CHARS", 2000)


settings = Settings()
