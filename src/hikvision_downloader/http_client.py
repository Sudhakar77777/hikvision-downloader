import time
from typing import Any

import requests

from .config import COOKIE, MAX_RETRIES, RETRY_WAIT, USER_AGENT


def make_session(cookie: str | None = None, user_agent: str | None = None) -> requests.Session:
    """Create an authenticated HTTP session using the Hikvision WebSession cookie."""
    auth_cookie = cookie or COOKIE

    if not auth_cookie:
        raise RuntimeError("HIKVISION_COOKIE is missing from .env configuration")

    session = requests.Session()
    session.headers.update(
        {
            "Cookie": auth_cookie,
            "User-Agent": user_agent or USER_AGENT,
        }
    )

    return session


def request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    *,
    max_retries: int = MAX_RETRIES,
    retry_wait: float = RETRY_WAIT,
    verbose: bool = False,
    **kwargs: Any,
) -> requests.Response:
    """Make an HTTP request with exponential/linear retries and error checking."""
    for attempt in range(1, max_retries + 1):
        try:
            if verbose:
                print(f"  Request attempt {attempt}/{max_retries}: {method.upper()} {url}")

            response = session.request(method, url, **kwargs)

            if response.status_code == 401:
                raise RuntimeError("NVR returned 401 Unauthorized. The WebSession cookie has probably expired.")

            response.raise_for_status()
            return response

        except (requests.RequestException, RuntimeError) as exc:
            if verbose:
                print(f"  Request attempt {attempt}/{max_retries} failed: {exc}")

            if attempt == max_retries:
                raise

            if verbose:
                print(f"  Retrying in {retry_wait} seconds...")

            time.sleep(retry_wait)

    raise RuntimeError(f"HTTP request failed after {max_retries} attempts: {method} {url}")
