import time
import structlog

log = structlog.get_logger()

# Simple per-model circuit breaker: in-memory, no Redis for Phase 1
# State: failures dict + open_until dict

_fail_counts: dict[str, int] = {}
_open_until: dict[str, float] = {}
FAIL_MAX = 3
RESET_TIMEOUT = 300  # 5 min


def is_open(model: str) -> bool:
    until = _open_until.get(model)
    if until and time.monotonic() < until:
        return True
    if until and time.monotonic() >= until:
        # half-open → allow one trial, reset
        _open_until.pop(model, None)
        _fail_counts.pop(model, None)
        log.info("breaker half-open allow trial", model=model)
    return False


def record_success(model: str) -> None:
    _fail_counts.pop(model, None)
    _open_until.pop(model, None)


def record_failure(model: str) -> None:
    cnt = _fail_counts.get(model, 0) + 1
    _fail_counts[model] = cnt
    if cnt >= FAIL_MAX:
        _open_until[model] = time.monotonic() + RESET_TIMEOUT
        log.warning("breaker opened", model=model, failures=cnt, reset_in=RESET_TIMEOUT)
    else:
        log.info("breaker failure count", model=model, failures=cnt)


def reset_all() -> None:
    _fail_counts.clear()
    _open_until.clear()
