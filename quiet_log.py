"""限流終端輸出，避免高頻路徑刷屏。"""

from __future__ import annotations

import threading
import time
from typing import Dict

_lock = threading.Lock()
_last_ts: Dict[str, float] = {}


def _interval_sec() -> float:
    try:
        import config

        return max(30.0, float(getattr(config, "SERVER_QUIET_LOG_SEC", 300.0)))
    except Exception:
        return 300.0


def log_throttled(key: str, message: str, interval_sec: float | None = None) -> None:
    """同一 key 在 interval 內只 print 一次。"""
    iv = _interval_sec() if interval_sec is None else max(5.0, float(interval_sec))
    now = time.time()
    with _lock:
        if now - _last_ts.get(key, 0.0) < iv:
            return
        _last_ts[key] = now
    print(message)
