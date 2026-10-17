"""主键与时间：UUIDv7（按时间有序）和 ISO 8601 字符串。"""

import os
import threading
import time
from datetime import datetime, timezone

_lock = threading.Lock()
_last_ms = 0
_seq = 0


def new_id() -> str:
    """UUIDv7：48 位毫秒时间戳 + 12 位同毫秒序号 + 62 位随机数。

    同一毫秒内的序号递增，保证同一进程生成的 ID 严格有序，导出时按主键排序结果稳定。
    """
    global _last_ms, _seq
    with _lock:
        ms = int(time.time() * 1000)
        if ms <= _last_ms:
            ms = _last_ms
            _seq += 1
            if _seq > 0xFFF:
                ms += 1
                _seq = 0
        else:
            _seq = 0
        _last_ms = ms
        seq = _seq
    rand = int.from_bytes(os.urandom(8), "big") & ((1 << 62) - 1)
    value = (ms << 80) | (0x7 << 76) | (seq << 64) | (0b10 << 62) | rand
    h = f"{value:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_str() -> str:
    return datetime.now().astimezone().date().isoformat()
