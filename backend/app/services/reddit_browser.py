from __future__ import annotations

import json
import time
from typing import Any

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth

from ..utils.logging import get_logger
from .proxy import get_random_user_agent

# Initialize stealth configuration
_stealth = Stealth()

logger = get_logger("sie.reddit_browser")


class BrowserRedditClient:
    """
    Reddit client using Playwright for browser-based scraping.

    Uses old.reddit.com JSON endpoints which are simpler to parse
    and less likely to be blocked than the main site.
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        timeout_ms: int = 30000,
        min_interval_s: float = 1.0,
        proxy: str | None = None,
    ) -> None:
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._min_interval_s = max(min_interval_s, 0.5)  # At least 0.5s between requests
        self._proxy = proxy
        self._last_request_s = 0.0

        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def _ensure_browser(self) -> Page:
        """Initialize browser if not already running."""
        if self._page is not None:
            return self._page

        self._playwright = sync_playwright().start()

        # Browser launch options
        launch_options: dict[str, Any] = {
            "headless": self._headless,
        }

        # Add proxy if configured
        if self._proxy:
            launch_options["proxy"] = {"server": self._proxy}

        self._browser = self._playwright.chromium.launch(**launch_options)

        # Create context with realistic viewport and user agent
        self._context = self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=get_random_user_agent(),
            locale="en-US",
            timezone_id="America/New_York",
        )

        self._page = self._context.new_page()
        self._page.set_default_timeout(self._timeout_ms)

        # Apply stealth to avoid detection
        _stealth.apply_stealth_sync(self._page)

        logger.info("Browser initialized (headless=%s, proxy=%s)", self._headless, bool(self._proxy))
        return self._page

    def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._page:
            self._page.close()
            self._page = None
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        logger.info("Browser closed")

    def _rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
        if self._min_interval_s > 0:
            elapsed = time.time() - self._last_request_s
            sleep_for = self._min_interval_s - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    def _fetch_json(self, url: str) -> dict[str, Any] | list[Any]:
        """Fetch JSON from a URL using the browser."""
        page = self._ensure_browser()
        self._rate_limit()

        logger.debug("Fetching: %s", url)

        try:
            response = page.goto(url, wait_until="networkidle")
            self._last_request_s = time.time()

            if response is None:
                raise RuntimeError(f"No response from {url}")

            if response.status == 403:
                raise RuntimeError(f"Blocked (403) fetching {url}")

            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status} fetching {url}")

            # Get the page content and parse as JSON
            content = page.content()

            # old.reddit.com returns JSON wrapped in HTML <pre> tags
            # Extract JSON from the page
            try:
                # Try to get raw text content from <pre> tag
                pre_element = page.query_selector("pre")
                if pre_element:
                    json_text = pre_element.inner_text()
                else:
                    # Fallback: try body text
                    json_text = page.inner_text("body")

                return json.loads(json_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, the page might have anti-bot content
                logger.warning("Failed to parse JSON from %s", url)
                raise RuntimeError(f"Invalid JSON response from {url}")

        except Exception as e:
            logger.error("Browser fetch failed: %s", str(e))
            raise

    def search_posts(
        self,
        *,
        query: str,
        sort: str = "relevance",
        time_filter: str = "month",
        limit: int = 100,
        after: str | None = None,
    ) -> dict[str, Any]:
        """Search Reddit posts."""
        params = f"q={query}&sort={sort}&t={time_filter}&limit={limit}&raw_json=1"
        if after:
            params += f"&after={after}"
        url = f"https://old.reddit.com/search.json?{params}"
        return self._fetch_json(url)  # type: ignore[return-value]

    def subreddit_about(self, subreddit: str) -> dict[str, Any]:
        """Get subreddit metadata."""
        url = f"https://old.reddit.com/r/{subreddit}/about.json?raw_json=1"
        return self._fetch_json(url)  # type: ignore[return-value]

    def subreddit_search_posts(
        self,
        *,
        subreddit: str,
        query: str,
        sort: str = "top",
        time_filter: str = "month",
        limit: int = 100,
        after: str | None = None,
    ) -> dict[str, Any]:
        """Search posts within a subreddit."""
        params = f"q={query}&restrict_sr=true&sort={sort}&t={time_filter}&limit={limit}&raw_json=1"
        if after:
            params += f"&after={after}"
        url = f"https://old.reddit.com/r/{subreddit}/search.json?{params}"
        return self._fetch_json(url)  # type: ignore[return-value]

    def subreddit_posts(
        self,
        *,
        subreddit: str,
        sort: str = "top",
        time_filter: str = "month",
        limit: int = 100,
        after: str | None = None,
    ) -> dict[str, Any]:
        """Get posts from a subreddit."""
        params = f"limit={limit}&raw_json=1"
        if sort == "top":
            params += f"&t={time_filter}"
        if after:
            params += f"&after={after}"
        url = f"https://old.reddit.com/r/{subreddit}/{sort}.json?{params}"
        return self._fetch_json(url)  # type: ignore[return-value]

    def comments(
        self,
        *,
        post_id: str,
        limit: int = 50,
        depth: int = 3,
        sort: str = "top",
    ) -> list[Any]:
        """Get comments for a post."""
        # Remove t3_ prefix if present
        if post_id.startswith("t3_"):
            post_id = post_id[3:]
        params = f"limit={limit}&depth={depth}&sort={sort}&raw_json=1"
        url = f"https://old.reddit.com/comments/{post_id}.json?{params}"
        return self._fetch_json(url)  # type: ignore[return-value]


class HybridRedditClient:
    """
    Hybrid client that tries browser-based scraping first,
    then falls back to httpx-based client if browser fails.
    """

    def __init__(
        self,
        *,
        # Browser options
        use_browser: bool = True,
        headless: bool = True,
        browser_timeout_ms: int = 30000,
        # Shared options
        min_interval_s: float = 1.0,
        proxy: str | None = None,
        # httpx fallback options (passed to RedditClient)
        client_id: str | None = None,
        client_secret: str | None = None,
        username: str | None = None,
        password: str | None = None,
        user_agent: str = "SocialIntelEngine/0.1",
        proxy_manager: Any = None,
    ) -> None:
        self._use_browser = use_browser
        self._browser_client: BrowserRedditClient | None = None
        self._httpx_client = None

        # Store config for lazy initialization
        self._browser_config = {
            "headless": headless,
            "timeout_ms": browser_timeout_ms,
            "min_interval_s": min_interval_s,
            "proxy": proxy,
        }
        self._httpx_config = {
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
            "user_agent": user_agent,
            "min_interval_s": min_interval_s,
            "proxy_manager": proxy_manager,
        }

        self._browser_failed = False

    def _get_browser_client(self) -> BrowserRedditClient | None:
        """Lazily initialize browser client."""
        if not self._use_browser or self._browser_failed:
            return None
        if self._browser_client is None:
            try:
                self._browser_client = BrowserRedditClient(**self._browser_config)
            except Exception as e:
                logger.warning("Failed to initialize browser: %s", str(e))
                self._browser_failed = True
                return None
        return self._browser_client

    def _get_httpx_client(self):
        """Lazily initialize httpx client."""
        if self._httpx_client is None:
            from .reddit import RedditClient
            self._httpx_client = RedditClient(**self._httpx_config)
        return self._httpx_client

    def close(self) -> None:
        """Close all clients."""
        if self._browser_client:
            self._browser_client.close()
            self._browser_client = None
        if self._httpx_client:
            self._httpx_client.close()
            self._httpx_client = None

    def _call_with_fallback(self, method_name: str, **kwargs) -> Any:
        """Try browser first, fall back to httpx."""
        browser = self._get_browser_client()

        if browser and not self._browser_failed:
            try:
                method = getattr(browser, method_name)
                result = method(**kwargs)
                logger.debug("Browser request succeeded: %s", method_name)
                return result
            except Exception as e:
                logger.warning("Browser request failed (%s), falling back to httpx: %s", method_name, str(e))

        # Fallback to httpx
        httpx_client = self._get_httpx_client()
        method = getattr(httpx_client, method_name)
        return method(**kwargs)

    def search_posts(self, **kwargs) -> dict[str, Any]:
        return self._call_with_fallback("search_posts", **kwargs)

    def subreddit_about(self, subreddit: str) -> dict[str, Any]:
        return self._call_with_fallback("subreddit_about", subreddit=subreddit)

    def subreddit_search_posts(self, **kwargs) -> dict[str, Any]:
        return self._call_with_fallback("subreddit_search_posts", **kwargs)

    def subreddit_posts(self, **kwargs) -> dict[str, Any]:
        return self._call_with_fallback("subreddit_posts", **kwargs)

    def comments(self, **kwargs) -> list[Any]:
        return self._call_with_fallback("comments", **kwargs)
