import time
from typing import Any

import requests

from .config import MAX_RETRIES, RETRY_WAIT, USER_AGENT


def make_session(user_agent: str | None = None) -> requests.Session:
    """Create an HTTP session with default headers."""
    session = requests.Session()
    session.headers.update(
        {
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
    """Make an HTTP request with exponential/linear retries and error checking.

    Authentication/authorization failures (401 Unauthorized, 403 Forbidden) are never
    retried to prevent triggering NVR security lockouts / illegal login bans.
    """
    for attempt in range(1, max_retries + 1):
        try:
            if verbose:
                print(f"  Request attempt {attempt}/{max_retries}: {method.upper()} {url}")

            response = session.request(method, url, **kwargs)

            # Never retry on 401 Unauthorized or 403 Forbidden: fail immediately
            if response.status_code in (401, 403):
                status_desc = "401 Unauthorized" if response.status_code == 401 else "403 Forbidden"
                raise RuntimeError(f"NVR returned {status_desc}. Check username and password credentials.")

            response.raise_for_status()
            return response

        except (requests.RequestException, RuntimeError) as exc:
            # Do not retry client errors (400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found)
            is_client_error = (isinstance(exc, RuntimeError) and ("401 Unauthorized" in str(exc) or "403 Forbidden" in str(exc))) or (
                isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code in (400, 401, 403, 404)
            )
            if is_client_error:
                raise

            if verbose:
                print(f"  Request attempt {attempt}/{max_retries} failed: {exc}")

            if attempt == max_retries:
                raise

            if verbose:
                print(f"  Retrying in {retry_wait} seconds...")

            time.sleep(retry_wait)

    raise RuntimeError(f"HTTP request failed after {max_retries} attempts: {method} {url}")
