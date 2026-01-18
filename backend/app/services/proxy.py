from __future__ import annotations

import random
import re
import threading
import time
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from ..utils.logging import get_logger

logger = get_logger("sie.proxy")


# Realistic user agents for Reddit browsing
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


def get_random_user_agent() -> str:
    """Return a random realistic user agent string."""
    return random.choice(USER_AGENTS)


class ProxyManager:
    """
    Manages SOCKS5 proxy rotation with auto-refresh from a remote URL.

    Features:
    - Fetch proxy list from remote URL
    - Round-robin rotation
    - Background refresh at configurable interval
    - Thread-safe operations
    """

    def __init__(
        self,
        proxy_url: str | None = None,
        refresh_interval_s: float = 300.0,
        timeout_s: float = 30.0,
        default_scheme: str = "socks5",
        cache_path: str | None = None,
        cache_enabled: bool = True,
        proxifly_api_key: str | None = None,
        proxifly_protocol: str = "socks5",
        proxifly_anonymity: str | None = None,
        proxifly_country: str | None = None,
        proxifly_https: bool | None = None,
        proxifly_speed_ms: int | None = None,
        pool_size: int = 20,
        proxifly_max_retries: int = 3,
        proxifly_min_backoff_s: float = 1.0,
        proxifly_max_backoff_s: float = 30.0,
        proxifly_rate_limit_cooldown_s: float = 60.0,
        proxifly_max_wait_s: float = 5.0,
    ) -> None:
        self._proxy_url = proxy_url
        self._refresh_interval_s = refresh_interval_s
        self._timeout_s = timeout_s
        self._default_scheme = (default_scheme or "socks5").strip().lower()

        self._cache_enabled = bool(cache_enabled)
        self._cache_path = (
            Path(cache_path).expanduser() if cache_path else None
        )

        self._proxifly_api_key = proxifly_api_key
        self._proxifly_protocol = (proxifly_protocol or "socks5").strip().lower()
        self._proxifly_anonymity = proxifly_anonymity
        self._proxifly_country = proxifly_country
        self._proxifly_https = proxifly_https
        self._proxifly_speed_ms = proxifly_speed_ms
        self._pool_size = max(1, min(int(pool_size or 1), 20))
        self._proxifly_max_retries = max(0, int(proxifly_max_retries or 0))
        self._proxifly_min_backoff_s = max(float(proxifly_min_backoff_s or 0.0), 0.0)
        self._proxifly_max_backoff_s = max(float(proxifly_max_backoff_s or 0.0), 0.0)
        self._proxifly_rate_limit_cooldown_s = max(
            float(proxifly_rate_limit_cooldown_s or 0.0), 0.0
        )
        self._proxifly_max_wait_s = max(float(proxifly_max_wait_s or 0.0), 0.0)
        self._proxifly_next_allowed_epoch_s: float = 0.0

        self._proxies: list[str] = []
        self._index = 0
        self._lock = threading.Lock()

        self._stop_event = threading.Event()
        self._refresh_thread: threading.Thread | None = None

        # Load cache first (so we can still operate under provider rate limits).
        self._load_cache()

        # Initial fetch
        self._fetch_proxies()

    def _load_cache(self) -> None:
        if not self._cache_enabled or self._cache_path is None:
            return
        try:
            if not self._cache_path.exists():
                return
            raw = self._cache_path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            proxies = payload.get("proxies") if isinstance(payload, dict) else None
            if not isinstance(proxies, list) or not proxies:
                return
            loaded: list[str] = []
            for val in proxies:
                if isinstance(val, str) and val.strip():
                    loaded.append(val.strip())
            if not loaded:
                return
            with self._lock:
                self._proxies = loaded
                self._index = 0
            logger.info("Loaded %d proxies from cache", len(loaded))
        except Exception as e:
            logger.warning("Failed to load proxy cache: %s", str(e))

    def _write_cache(self, proxies: list[str]) -> None:
        if not self._cache_enabled or self._cache_path is None:
            return
        if not proxies:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._cache_path.with_suffix(self._cache_path.suffix + ".tmp")
            tmp.write_text(
                json.dumps({"fetched_at": time.time(), "proxies": proxies}, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self._cache_path)
        except Exception as e:
            logger.warning("Failed to write proxy cache: %s", str(e))

    @property
    def proxy_count(self) -> int:
        with self._lock:
            return len(self._proxies)

    def get_next_proxy(self) -> str | None:
        """
        Returns the next proxy in round-robin order.
        Returns None if no proxies are available.
        """
        with self._lock:
            if not self._proxies:
                return None
            proxy = self._proxies[self._index % len(self._proxies)]
            self._index += 1
            return proxy

    def report_failure(self, proxy_url: str) -> None:
        """
        Best-effort: remove a failing proxy from the current pool.
        The next refresh may re-add it; this is intended to protect the current run.
        """
        if not proxy_url:
            return
        with self._lock:
            if not self._proxies:
                return
            try:
                self._proxies.remove(proxy_url)
                if self._index >= len(self._proxies):
                    self._index = 0
                logger.info("Removed failing proxy (remaining: %d)", len(self._proxies))
            except ValueError:
                return

    def start_refresh_loop(self) -> None:
        """Start the background refresh thread."""
        if self._refresh_thread is not None and self._refresh_thread.is_alive():
            return

        self._stop_event.clear()
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True,
            name="proxy-refresh",
        )
        self._refresh_thread.start()
        logger.info(
            "Proxy refresh loop started (interval: %.0fs)", self._refresh_interval_s
        )

    def stop(self) -> None:
        """Stop the background refresh thread."""
        self._stop_event.set()
        if self._refresh_thread is not None:
            self._refresh_thread.join(timeout=5.0)
            self._refresh_thread = None
        logger.info("Proxy refresh loop stopped")

    def _refresh_loop(self) -> None:
        """Background loop that refreshes the proxy list periodically."""
        while not self._stop_event.is_set():
            # Wait for the refresh interval (or until stop is signaled)
            if self._stop_event.wait(timeout=self._refresh_interval_s):
                break
            self._fetch_proxies()

    def _parse_proxy_line(self, line: str) -> str | None:
        """
        Parse a proxy line into a URL with a scheme.

        Supports formats:
        - socks5://user:pass@host:port (already formatted)
        - socks4://host:port
        - http://host:port
        - https://host:port
        - host:port:user:pass (common provider format; uses default scheme)
        - host:port (uses default scheme)
        """
        line = line.strip()
        if not line:
            return None

        # Already in URL format
        if line.startswith(("socks5://", "socks4://", "http://", "https://")):
            return line

        parts = line.split(":")

        if len(parts) == 2:
            # host:port
            host, port = parts
            return f"{self._default_scheme}://{host}:{port}"

        elif len(parts) == 4:
            # host:port:user:pass
            host, port, user, password = parts
            return f"{self._default_scheme}://{user}:{password}@{host}:{port}"

        elif len(parts) == 3:
            # Could be host:port:user (incomplete) - skip
            return None

        return None

    def _extract_host_ports(self, text: str) -> list[str]:
        """
        Extract `ip:port` patterns from arbitrary text (e.g. HTML tables).
        This is a best-effort fallback when the source isn't a clean newline list.
        """
        # Keep it simple; validate later via _parse_proxy_line().
        return re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b", text)

    def _fetch_proxies_from_proxifly(self) -> list[str]:
        if not self._proxifly_api_key:
            return []

        now = time.time()
        if now < self._proxifly_next_allowed_epoch_s:
            raise RuntimeError(
                f"Proxifly rate limited; next allowed in "
                f"{int(self._proxifly_next_allowed_epoch_s - now)}s"
            )

        payload: dict[str, object] = {
            "apiKey": self._proxifly_api_key,
            "protocol": self._proxifly_protocol,
            "format": "json",
            "quantity": self._pool_size,
        }
        if self._proxifly_anonymity:
            payload["anonymity"] = self._proxifly_anonymity
        if self._proxifly_country:
            payload["country"] = self._proxifly_country
        if self._proxifly_https is not None:
            payload["https"] = self._proxifly_https
        if self._proxifly_speed_ms is not None:
            payload["speed"] = self._proxifly_speed_ms

        url = "https://api.proxifly.dev/proxy"
        attempt = 0
        max_retries = max(0, int(self._proxifly_max_retries or 0))

        while True:
            with httpx.Client(timeout=self._timeout_s) as client:
                resp = client.post(url, json=payload)

            # Rate limiting: set a cooldown and STOP spamming the API.
            if resp.status_code == 429:
                retry_after_raw = resp.headers.get("Retry-After")
                retry_after_s: float | None = None
                if retry_after_raw:
                    try:
                        retry_after_s = float(retry_after_raw)
                    except ValueError:
                        retry_after_s = None

                cooldown_s = retry_after_s
                if cooldown_s is None:
                    cooldown_s = self._proxifly_rate_limit_cooldown_s
                cooldown_s = max(float(cooldown_s), 0.0)

                self._proxifly_next_allowed_epoch_s = time.time() + cooldown_s
                logger.warning(
                    "Proxifly rate limited (HTTP 429). retry_after=%s next_allowed_in=%.0fs body=%s",
                    retry_after_raw,
                    cooldown_s,
                    (resp.text or "")[:200].replace("\n", " "),
                )

                # Only retry if the wait is short enough AND we have retries left.
                if attempt >= max_retries:
                    raise RuntimeError(
                        f"Proxifly rate limited (HTTP 429); retry after ~{int(cooldown_s)}s"
                    )
                if cooldown_s <= self._proxifly_max_wait_s and cooldown_s > 0:
                    time.sleep(cooldown_s)
                    attempt += 1
                    continue

                raise RuntimeError(
                    f"Proxifly rate limited (HTTP 429); retry after ~{int(cooldown_s)}s"
                )

            # Transient upstream issues.
            if resp.status_code in (500, 502, 503, 504):
                if attempt >= max_retries:
                    resp.raise_for_status()
                sleep_for = min(
                    max(self._proxifly_min_backoff_s, 0.0),
                    self._proxifly_max_wait_s,
                )
                if sleep_for > 0:
                    time.sleep(sleep_for)
                attempt += 1
                continue

            resp.raise_for_status()
            break

        data = resp.json()
        items: list[object]
        if isinstance(data, list):
            items = data
        else:
            items = [data]

        proxies: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            raw = item.get("proxy")
            if isinstance(raw, str) and raw.strip():
                proxies.append(raw.strip())
                continue
            ip = item.get("ip")
            port = item.get("port")
            if isinstance(ip, str) and isinstance(port, int):
                proxies.append(f"{self._proxifly_protocol}://{ip}:{port}")

        return proxies

    def _fetch_proxies(self) -> None:
        """Fetch proxy list from the remote URL."""
        try:
            lines: list[str] = []
            fetched_any = False

            # Prefer Proxifly if configured, fall back to URL source.
            if self._proxifly_api_key:
                try:
                    lines = self._fetch_proxies_from_proxifly()
                    fetched_any = True
                except httpx.HTTPStatusError as e:
                    logger.warning(
                        "Failed to fetch Proxifly proxies (HTTP %d): %s",
                        e.response.status_code,
                        str(e),
                    )
                except httpx.RequestError as e:
                    logger.warning("Failed to fetch Proxifly proxies: %s", str(e))
                except RuntimeError as e:
                    # Internal rate-limit guard (no network call).
                    logger.warning("Failed to fetch Proxifly proxies: %s", str(e))

            # If Proxifly is configured, don't fall back to remote list URLs (often unreliable)
            # but do allow local sources like inline/file to supplement.
            allow_fallback = bool(self._proxy_url) and (
                not self._proxifly_api_key
                or (self._proxy_url or "").startswith(("inline:", "file:"))
            )

            if not lines and allow_fallback and self._proxy_url:
                raw_text = ""

                # Allow local / inline sources so a remote "list URL" isn't required.
                if self._proxy_url.startswith("inline:"):
                    raw_text = self._proxy_url.removeprefix("inline:").strip()
                    fetched_any = True
                elif self._proxy_url.startswith("file:"):
                    parsed = urlparse(self._proxy_url)
                    file_path = unquote(parsed.path or "")
                    # Handle Windows file URLs like file:///C:/path/to/file.txt
                    if file_path.startswith("/") and len(file_path) >= 4 and file_path[2] == ":":
                        file_path = file_path[1:]
                    raw_text = Path(file_path).read_text(encoding="utf-8")
                    fetched_any = True
                else:
                    with httpx.Client(timeout=self._timeout_s) as client:
                        resp = client.get(self._proxy_url)
                        resp.raise_for_status()
                    raw_text = resp.text or ""
                    fetched_any = True

                # First try clean newline lists, then fallback to ip:port extraction.
                lines = [line for line in raw_text.strip().split("\n") if line.strip()]
                if not lines:
                    lines = self._extract_host_ports(raw_text)

            # If we didn't successfully fetch from any source, keep the existing pool.
            if not fetched_any:
                return

            # Parse each line and convert to socks5:// format
            valid_proxies = []
            for line in lines:
                parsed = self._parse_proxy_line(line)
                if parsed:
                    valid_proxies.append(parsed)

            with self._lock:
                old_count = len(self._proxies)
                # If fetch succeeded but parsing produced nothing, keep the old pool.
                if not valid_proxies and old_count > 0:
                    logger.warning(
                        "Proxy refresh returned 0 usable proxies; keeping existing pool (%d)",
                        old_count,
                    )
                    return
                self._proxies = valid_proxies
                # Reset index if list changed significantly
                if self._index >= len(self._proxies):
                    self._index = 0

            if valid_proxies:
                self._write_cache(valid_proxies)

            logger.info(
                "Proxy list refreshed: %d proxies (was %d)",
                len(valid_proxies),
                old_count,
            )

        except httpx.HTTPStatusError as e:
            logger.warning(
                "Failed to fetch proxy list (HTTP %d): %s",
                e.response.status_code,
                str(e),
            )
        except httpx.RequestError as e:
            logger.warning("Failed to fetch proxy list: %s", str(e))
        except Exception as e:
            logger.exception("Unexpected error fetching proxy list: %s", str(e))

    def force_refresh(self) -> None:
        """Force an immediate refresh of the proxy list."""
        self._fetch_proxies()
