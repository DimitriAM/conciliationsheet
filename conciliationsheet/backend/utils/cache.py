import time
from functools import wraps
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            expires, value = self._cache[key]
            if time.time() < expires:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = (time.time() + self._ttl, value)

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()


_cache = TTLCache()


def cached(ttl: int = 300):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = f"{f.__name__}:{args}:{sorted(kwargs.items())}"
            result = _cache.get(key)
            if result is not None:
                return result
            result = f(*args, **kwargs)
            _cache.set(key, result)
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern: Optional[str] = None) -> None:
    if pattern is None:
        _cache.clear()
    else:
        keys_to_delete = [k for k in _cache._cache if pattern in k]
        for k in keys_to_delete:
            _cache.delete(k)
