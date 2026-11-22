"""Heartbeat and watchdog: so Uncle Tony never fails silently.

- On start-up it sends "back online", so you know when the VM or service restarted.
- Once a day (HEARTBEAT_HOUR, VM local time) it sends a short "I'm alive" check-in.
  If that message doesn't arrive, something is wrong with the bot or the VM.
- A watchdog thread checks that the market scanner and Telegram polling are still
  working. If either stalls it sends one warning, and one "recovered" message when
  it comes back. No repeated spam.
- /status shows the same health report on demand.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import config
from utils.logger import get_logger

logger = get_logger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / ".heartbeat_state.json"
CHECK_EVERY_SECONDS = 300  # watchdog interval (5 minutes)
POLL_STALE_SECONDS = 10 * 60  # Telegram polling silent this long = problem

_started_at = time.time()
_last_poll_ok = time.time()
_poll_failures = 0
_problems: Dict[str, str] = {}  # problem key -> description, for problems already warned about
_lock = threading.Lock()
_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None


# ------------------------ Recording ---------------------------------------
def record_poll_ok() -> None:
    """Called by bot.py after every successful Telegram poll."""
    global _last_poll_ok, _poll_failures
    with _lock:
        _last_poll_ok = time.time()
        _poll_failures = 0


def record_poll_error() -> None:
    global _poll_failures
    with _lock:
        _poll_failures += 1


# ------------------------ Helpers -----------------------------------------
def _ago(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 90:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 90:
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    if hours < 48:
        return f"{hours}h {minutes}m"
    return f"{hours // 24}d {hours % 24}h"


def _send(text: str) -> None:
    chat_id = getattr(config, "CHAT_ID", None)
    if not chat_id:
        logger.info("Heartbeat (no CHAT_ID): %s", text)
        return
    try:
        from services.telegram_service import send_message

        send_message(chat_id, text)
    except Exception as e:  # never let a failed send crash the watchdog
        logger.warning("Heartbeat send failed: %s", e)


def _read_state() -> Dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _write_state(state: Dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state))
    except Exception as e:
        logger.warning("Could not save heartbeat state: %s", e)


def _scanner_info() -> Optional[Dict]:
    """Return {'last_scan_ts', 'interval', 'symbols'} or None if the scanner is off."""
    if not getattr(config, "SCANNER_ENABLED", False):
        return None
    try:
        from services import auto_scanner

        return {
            "last_scan_ts": auto_scanner._last_scan.get("ts", 0.0),
            "interval": auto_scanner.SCAN_EVERY_SECONDS,
            "symbols": len(auto_scanner.WATCHLIST),
        }
    except Exception:
        return None


# ------------------------ Checks ------------------------------------------
def find_problems(now: Optional[float] = None) -> Dict[str, str]:
    """Return current problems as {key: description}. Empty dict means healthy."""
    now = now or time.time()
    problems: Dict[str, str] = {}

    info = _scanner_info()
    if info is not None:
        last = info["last_scan_ts"]
        # Allow two full cycles plus a margin before calling it stalled.
        limit = 2 * info["interval"] + 300
        reference = last if last else _started_at
        if now - reference > limit:
            what = f"last scan {_ago(now - last)} ago" if last else "no scan has finished since start-up"
            problems["scanner"] = f"Market scanner looks stuck ({what})."

    with _lock:
        poll_age = now - _last_poll_ok
    if poll_age > POLL_STALE_SECONDS:
        problems["polling"] = f"Telegram polling has failed for {_ago(poll_age)}."

    return problems


def status_text(now: Optional[float] = None) -> str:
    now = now or time.time()
    lines: List[str] = []
    problems = find_problems(now)
    lines.append("🟢 Uncle Tony: all systems OK" if not problems else "🟠 Uncle Tony: needs attention")
    lines.append("")
    lines.append(f"Uptime: {_ago(now - _started_at)}")

    info = _scanner_info()
    if info is None:
        lines.append("Scanner: off")
    elif info["last_scan_ts"]:
        lines.append(f"Last market scan: {_ago(now - info['last_scan_ts'])} ago ({info['symbols']} coins)")
    else:
        lines.append("Last market scan: none yet")

    with _lock:
        lines.append(f"Telegram: last poll {_ago(now - _last_poll_ok)} ago")

    for description in problems.values():
        lines.append(f"⚠️ {description}")
    return "\n".join(lines)


def check_once(now: Optional[float] = None) -> List[str]:
    """Run the watchdog once. Returns the messages it sent (for tests)."""
    sent: List[str] = []
    current = find_problems(now)

    with _lock:
        new = {k: v for k, v in current.items() if k not in _problems}
        recovered = [k for k in list(_problems) if k not in current]
        for k in recovered:
            _problems.pop(k)
        _problems.update(new)

    for description in new.values():
        msg = f"⚠️ Uncle Tony warning\n\n{description}\nI'll tell you when it recovers. Check: journalctl --user -u uncle-tony -n 50"
        _send(msg)
        sent.append(msg)
    for key in recovered:
        msg = f"✅ Recovered: the {'market scanner' if key == 'scanner' else 'Telegram connection'} is working again."
        _send(msg)
        sent.append(msg)

    msg = maybe_send_daily(now)
    if msg:
        sent.append(msg)
    return sent


def maybe_send_daily(now: Optional[float] = None) -> Optional[str]:
    """Send the daily check-in once per day, at or after HEARTBEAT_HOUR."""
    moment = datetime.fromtimestamp(now or time.time())
    if moment.hour < getattr(config, "HEARTBEAT_HOUR", 7):
        return None
    today = moment.strftime("%Y-%m-%d")
    state = _read_state()
    if state.get("last_daily") == today:
        return None
    msg = "☀️ Daily check-in\n\n" + status_text(now)
    _send(msg)
    state["last_daily"] = today
    _write_state(state)
    return msg


# ------------------------ Lifecycle ---------------------------------------
def _run_loop() -> None:
    while not _stop_event.wait(CHECK_EVERY_SECONDS):
        try:
            check_once()
        except Exception as e:
            logger.error("Heartbeat check failed: %s", e)


def start_heartbeat() -> None:
    """Send the start-up message and start the watchdog thread (non-blocking)."""
    global _thread
    if _thread and _thread.is_alive():
        return
    _send("🟢 Uncle Tony is online.\nIf you didn't restart me, the VM or service restarted. Send /status any time.")
    _stop_event.clear()
    _thread = threading.Thread(target=_run_loop, daemon=True)
    _thread.start()
    logger.info("Heartbeat started")


def stop_heartbeat() -> None:
    _stop_event.set()


def handle_status_command(chat_id: str) -> None:
    from services.telegram_service import send_message

    send_message(chat_id, status_text())
