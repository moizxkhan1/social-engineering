from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
from httpx_socks import SyncProxyTransport

from .proxy import get_random_user_agent

if TYPE_CHECKING:
    from .proxy import ProxyManager


class RedditConfigError(RuntimeError):
    pass


class RedditAuthError(RuntimeError):
    pass


class RedditRequestError(RuntimeError):
    pass


@dataclass(frozen=True)
class RedditToken:
    access_token: str
    token_type: str
    expires_at_epoch_s: float

    def is_expired(self) -> bool:
        # Refresh slightly early to avoid edge-of-expiry failures.
        return time.time() >= (self.expires_at_epoch_s - 15)


class RedditClient:
    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        username: str | None = None,
        password: str | None = None,
        user_agent: str,
        timeout_s: float = 30.0,
        min_interval_s: float = 0.0,
        proxy_manager: ProxyManager | None = None,
    ) -> None:
        if not user_agent:
            raise RedditConfigError("Missing Reddit user agent")

        self._client_id = client_id or ""
        self._client_secret = client_secret or ""
        self._username = username or ""
        self._password = password or ""
        self._user_agent = user_agent
        self._timeout_s = timeout_s
        self._min_interval_s = max(min_interval_s, 0.0)
        self._last_request_s = 0.0
        self._proxy_manager = proxy_manager

        self._use_oauth = all(
            [
                bool(self._client_id),
                bool(self._client_secret),
                bool(self._username),
                bool(self._password),
            ]
        )

        self._token: RedditToken | None = None
        # Only create default client if no proxy manager (proxied requests use per-request clients)
        self._http = httpx.Client(timeout=timeout_s) if not proxy_manager else None

    def close(self) -> None:
        if self._http is not None:
            self._http.close()

    def _get_http_client(self, proxy_url: str | None = None) -> httpx.Client:
        """Get an HTTP client, optionally configured with a SOCKS proxy."""
        if proxy_url:
            if proxy_url.startswith(("socks4://", "socks5://")):
                transport = SyncProxyTransport.from_url(proxy_url)
                return httpx.Client(transport=transport, timeout=self._timeout_s)
            # httpx supports HTTP/HTTPS proxies directly.
            return httpx.Client(proxy=proxy_url, timeout=self._timeout_s)
        if self._http is not None:
            return self._http
        return httpx.Client(timeout=self._timeout_s)

    def _auth_headers(self, proxy_url: str | None = None) -> dict[str, str]:
        # Use random user agent when going through proxy for better anonymity
        user_agent = get_random_user_agent() if proxy_url else self._user_agent

        if not self._use_oauth:
            return {"User-Agent": user_agent, "Accept": "application/json"}
        token = self._get_token(proxy_url)
        return {"Authorization": f"Bearer {token.access_token}", "User-Agent": user_agent}

    def _get_token(self, proxy_url: str | None = None) -> RedditToken:
        if not self._use_oauth:
            raise RedditConfigError("OAuth credentials not configured")

        if self._token is not None and not self._token.is_expired():
            return self._token

        url = "https://www.reddit.com/api/v1/access_token"
        # Use random user agent when going through proxy
        user_agent = get_random_user_agent() if proxy_url else self._user_agent
        headers = {"User-Agent": user_agent}
        data = {
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
        }

        client = self._get_http_client(proxy_url)
        try:
            resp = client.post(
                url,
                auth=(self._client_id, self._client_secret),
                headers=headers,
                data=data,
            )
        finally:
            # Close client if it was created for proxy
            if proxy_url:
                client.close()

        if resp.status_code != 200:
            raise RedditAuthError(
                f"Token exchange failed: {resp.status_code} {resp.text}"
            )

        payload = resp.json()
        access_token = payload.get("access_token")
        token_type = payload.get("token_type", "bearer")
        expires_in = payload.get("expires_in", 3600)

        if not access_token:
            raise RedditAuthError(f"Token response missing access_token: {payload}")

        self._token = RedditToken(
            access_token=access_token,
            token_type=token_type,
            expires_at_epoch_s=time.time() + float(expires_in),
        )
        return self._token

    def _maybe_sleep_for_rate_limit(self, resp: httpx.Response) -> None:
        remaining = resp.headers.get("X-Ratelimit-Remaining")
        reset_s = resp.headers.get("X-Ratelimit-Reset")
        if remaining is None or reset_s is None:
            return

        try:
            remaining_val = float(remaining)
            reset_val = float(reset_s)
        except ValueError:
            return

        # Simple approach: if close to limit, wait until reset.
        if remaining_val < 5 and reset_val > 0:
            time.sleep(min(reset_val, 60.0))

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        if not path.startswith("/"):
            path = "/" + path
        bases = (
            ["https://oauth.reddit.com"]
            if self._use_oauth
            else ["https://www.reddit.com", "https://old.reddit.com"]
        )

        request_params = dict(params or {})
        request_params.setdefault("raw_json", 1)

        def _do_request(proxy_url: str | None, url: str) -> httpx.Response:
            headers = self._auth_headers(proxy_url)

            if self._min_interval_s > 0:
                elapsed = time.time() - self._last_request_s
                sleep_for = self._min_interval_s - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)

            client = self._get_http_client(proxy_url)
            try:
                resp = client.request(
                    method, url, headers=headers, params=request_params, data=data
                )
                self._last_request_s = time.time()

                if resp.status_code == 401 and self._use_oauth:
                    # Token expired/invalid; refresh once.
                    self._token = None
                    headers = self._auth_headers(proxy_url)
                    resp = client.request(
                        method, url, headers=headers, params=request_params, data=data
                    )

                if resp.status_code in (429, 503):
                    time.sleep(2.0)

                self._maybe_sleep_for_rate_limit(resp)
                return resp
            finally:
                if proxy_url:
                    client.close()

        # If proxies are flaky or blocked, rotate a few times then fall back to direct.
        max_proxy_attempts = 5
        last_exc: Exception | None = None
        if self._proxy_manager:
            for base in bases:
                url = f"{base}{path}"
                for _ in range(max_proxy_attempts):
                    proxy_url = self._proxy_manager.get_next_proxy()
                    if not proxy_url:
                        break
                    try:
                        resp = _do_request(proxy_url, url)
                        # Treat "blocked" responses as proxy failures and rotate.
                        if resp.status_code == 403:
                            self._proxy_manager.report_failure(proxy_url)
                            continue
                        # Rotate on transient overload as well.
                        if resp.status_code in (429, 503):
                            continue
                        return resp
                    except Exception as exc:
                        last_exc = exc
                        # Remove this proxy from the current pool and try the next one.
                        self._proxy_manager.report_failure(proxy_url)
                        continue

        try:
            # Direct attempt (no proxy). Try both hosts when not using OAuth.
            for base in bases:
                url = f"{base}{path}"
                resp = _do_request(None, url)
                if resp.status_code == 403 and not self._use_oauth:
                    continue
                return resp
            return resp
        except Exception as exc:
            # Preserve the proxy exception context if proxy attempts happened.
            raise last_exc or exc

    def get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        resp = self.request("GET", path, params=params)
        if resp.status_code != 200:
            raise RedditRequestError(
                f"Reddit GET {path} failed: {resp.status_code} {resp.text}"
            )
        return resp.json()

    def search_posts(
        self,
        *,
        query: str,
        sort: str = "relevance",
        time_filter: str = "month",
        limit: int = 100,
        after: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"q": query, "sort": sort, "t": time_filter, "limit": limit}
        if after:
            params["after"] = after
        path = "/search" if self._use_oauth else "/search.json"
        return self.get_json(path, params=params)  # type: ignore[return-value]

    def subreddit_about(self, subreddit: str) -> dict[str, Any]:
        path = f"/r/{subreddit}/about" if self._use_oauth else f"/r/{subreddit}/about.json"
        return self.get_json(path)  # type: ignore[return-value]

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
        params: dict[str, Any] = {
            "q": query,
            "restrict_sr": True,
            "sort": sort,
            "t": time_filter,
            "limit": limit,
        }
        if after:
            params["after"] = after
        path = (
            f"/r/{subreddit}/search" if self._use_oauth else f"/r/{subreddit}/search.json"
        )
        return self.get_json(path, params=params)  # type: ignore[return-value]

    def subreddit_posts(
        self,
        *,
        subreddit: str,
        sort: str = "top",
        time_filter: str = "month",
        limit: int = 100,
        after: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if sort == "top":
            params["t"] = time_filter
        if after:
            params["after"] = after
        path = (
            f"/r/{subreddit}/{sort}"
            if self._use_oauth
            else f"/r/{subreddit}/{sort}.json"
        )
        return self.get_json(path, params=params)  # type: ignore[return-value]

    def comments(
        self,
        *,
        post_id: str,
        limit: int = 50,
        depth: int = 3,
        sort: str = "top",
    ) -> list[Any]:
        params: dict[str, Any] = {"limit": limit, "depth": depth, "sort": sort}
        path = f"/comments/{post_id}" if self._use_oauth else f"/comments/{post_id}.json"
        return self.get_json(path, params=params)  # type: ignore[return-value]
