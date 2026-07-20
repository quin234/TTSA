"""Shared decorators for the TTSA project."""
import functools
import re

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


def get_client_ip(request):
    """Return the originating IP address, respecting reverse proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _parse_rate(rate):
    """Parse a rate string like '5/m' into (limit, seconds)."""
    match = re.match(r'^(\d+)\s*/\s*(\w+)$', rate)
    if not match:
        raise ValueError(f"Invalid rate '{rate}'. Expected format: 'N/<unit>'.")
    limit = int(match.group(1))
    unit = match.group(2).lower()
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
    }
    if unit not in multipliers:
        raise ValueError(f"Invalid rate unit '{unit}'. Use s/m/h/d.")
    return limit, limit * multipliers[unit]


def rate_limit(rate='10/m', key_func=None, block=True):
    """
    Lightweight rate-limiting decorator backed by Django's cache.

    `key_func(request)` should return a string used to build the cache key.
    Defaults to the client IP address. Disabled when DEBUG is True unless
    explicitly enabled.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if settings.DEBUG and not getattr(settings, 'RATE_LIMIT_IN_DEBUG', False):
                return view_func(request, *args, **kwargs)

            key = key_func(request) if key_func else get_client_ip(request)
            limit, seconds = _parse_rate(rate)
            cache_key = f"ratelimit:{view_func.__module__}.{view_func.__name__}:{key}"

            try:
                current = cache.incr(cache_key)
            except ValueError:
                cache.set(cache_key, 1, timeout=seconds)
                current = 1

            if current > limit:
                if block:
                    return JsonResponse(
                        {'success': False, 'error': 'Too many requests. Please slow down.'},
                        status=429,
                    )
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
