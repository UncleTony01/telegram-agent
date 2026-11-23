import time
import warnings

import requests

from config import BOT_TOKEN, TELEGRAM_API_IPS
from utils.logger import get_logger

logger = get_logger(__name__)

BASE_HOST = "api.telegram.org"
TOKEN = BOT_TOKEN if BOT_TOKEN and BOT_TOKEN != "YOUR_BOT_TOKEN" else "TESTTOKEN"
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 40
MAX_RETRIES = 2
BACKOFF_SECONDS = (1, 2)

session = requests.Session()
session.headers.update({"User-Agent": "telegram-agent/1.0"})


def _build_urls(endpoint):
    urls = [f"https://{BASE_HOST}/bot{TOKEN}{endpoint}"]
    if TELEGRAM_API_IPS:
        for ip in TELEGRAM_API_IPS:
            urls.append(f"https://{ip}/bot{TOKEN}{endpoint}")
    return urls


def _request(method, endpoint, **kwargs):
    last_error = None
    request_timeout = kwargs.pop("timeout", (CONNECT_TIMEOUT, READ_TIMEOUT))

    for attempt in range(MAX_RETRIES):
        for index, url in enumerate(_build_urls(endpoint)):
            request_kwargs = dict(kwargs)
            headers = dict(request_kwargs.pop("headers", {}) or {})

            if not url.startswith(f"https://{BASE_HOST}"):
                headers.setdefault("Host", BASE_HOST)
                request_kwargs["verify"] = False
                warnings.filterwarnings("ignore", message="Unverified HTTPS request")

            try:
                logger.info("Telegram request attempt %s for %s", attempt + 1, url)
                response = session.request(method, url, timeout=request_timeout, headers=headers, **request_kwargs)
                if response.ok:
                    logger.info("Telegram request succeeded for %s", url)
                    return response

                if response.status_code in {408, 429, 500, 502, 503, 504} and index < len(_build_urls(endpoint)) - 1:
                    logger.warning("Telegram endpoint %s returned %s; trying fallback", url, response.status_code)
                    continue

                return response
            except requests.RequestException as exc:
                last_error = exc
                logger.warning("Telegram request failed for %s: %s", url, exc)

        if attempt < MAX_RETRIES - 1:
            sleep_seconds = BACKOFF_SECONDS[attempt]
            logger.warning("Telegram request failed; retrying in %s second(s)", sleep_seconds)
            time.sleep(sleep_seconds)

    if last_error is not None:
        raise last_error

    raise requests.RequestException("Telegram request failed")


def send_message(chat_id, text, parse_mode=None, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text[:4000]}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
        payload["disable_web_page_preview"] = True
    response = _request("POST", "/sendMessage", json=payload)
    if parse_mode and response is not None and getattr(response, "status_code", 200) == 400:
        # Formatting was rejected (e.g. bad HTML): resend as plain text so the user still gets it.
        logger.warning("Telegram rejected %s formatting; resending as plain text", parse_mode)
        import html as _html
        import re as _re

        plain = _html.unescape(_re.sub(r"<[^>]+>", "", text))
        _request("POST", "/sendMessage", json={"chat_id": chat_id, "text": plain[:4000]})
    return response


def get_updates(offset=None):
    params = {"timeout": 30}

    if offset is not None:
        params["offset"] = offset

    response = _request("GET", "/getUpdates", params=params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
    return response.json()


def send_photo(chat_id, photo_bytes, caption=None, parse_mode=None, reply_markup=None):
    """Send a PNG with an optional caption (Telegram allows up to 1024 characters)."""
    import json as _json

    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption[:1024]
    if parse_mode:
        data["parse_mode"] = parse_mode
    if reply_markup:
        data["reply_markup"] = _json.dumps(reply_markup)
    try:
        return _request("post", "/sendPhoto", data=data,
                        files={"photo": ("post.png", photo_bytes, "image/png")})
    except Exception as e:
        logger.error("send_photo failed: %s", e)
        return None
