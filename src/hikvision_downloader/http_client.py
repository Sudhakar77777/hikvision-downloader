import time

import requests

from .config import COOKIE, MAX_RETRIES, RETRY_WAIT, USER_AGENT

# ============================================================
# HTTP
# ============================================================


def make_session():
    """Create an authenticated HTTP session using the Hikvision WebSession cookie."""

    if not COOKIE:
        raise RuntimeError("HIKVISION_COOKIE is missing from .env")

    session = requests.Session()

    session.headers.update(
        {
            "Cookie": COOKIE,
            "User-Agent": USER_AGENT,
        }
    )

    return session


def request_with_retry(session, method, url, *, verbose=False, **kwargs):
    """Make an HTTP request with retries."""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if verbose:
                print(f"  Request attempt {attempt}/{MAX_RETRIES}: {method.upper()} {url}")

            response = session.request(method, url, **kwargs)

            if response.status_code == 401:
                raise RuntimeError("NVR returned 401 Unauthorized. The WebSession cookie has probably expired.")

            response.raise_for_status()

            return response

        except (requests.RequestException, RuntimeError) as exc:
            if verbose:
                print(f"  Request attempt {attempt}/{MAX_RETRIES} failed: {exc}")

            if attempt == MAX_RETRIES:
                raise

            if verbose:
                print(f"  Retrying in {RETRY_WAIT} seconds...")

            time.sleep(RETRY_WAIT)
