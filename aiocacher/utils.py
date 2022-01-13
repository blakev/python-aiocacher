#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

import threading
from datetime import timedelta
from hashlib import sha1
from typing import Optional

import math
from toolz.functoolz import is_arity, has_keywords

from aiocacher.types import TimeT

__all__ = [
    'MAX_KEYLEN',
    'default_key_builder',
    'trim_key',
    'convert_ttl',
]

MAX_KEYLEN = 80


def default_key_builder(func, args, kwargs) -> str:
    """Converts keys passed to a single function into a SHA1 checksum for caching."""
    try:
        has_kwargs = has_keywords(func) is not False
        is_unary = is_arity(1, func)
    except TypeError:  # pragma: no cover
        has_kwargs = True
        is_unary = False

    f_name = func.__qualname__

    if not args and not has_kwargs:
        k = f_name, threading.get_ident()

    elif is_unary and args:
        k = f_name, str(args[0])

    elif has_kwargs:
        k = f_name, args or None, frozenset(kwargs.items() if kwargs else [])

    else:
        k = f_name, args

    return trim_key(sha1(''.join(map(str, k)).encode('utf-8')).hexdigest())


def convert_ttl(val: TimeT) -> Optional[int]:
    """Allow different input values that represent Time to reduce to an integer.

    >>> convert_ttl(0)
    0
    >>> convert_ttl(-1)
    0
    >>> convert_ttl(1.1)
    2
    >>> convert_ttl(timedelta(minutes=1))
    60
    """
    if isinstance(val, timedelta):
        val = val.total_seconds()
    if isinstance(val, float):
        val = math.ceil(val)
    val = max(0, int(val))
    return val


def trim_key(key: str) -> str:
    """Fixes a string to a fixed length defined as a constant ``MAX_KEYLEN``.

    >>> trim_key('')
    ''
    >>> trim_key('abc')
    'abc'
    """
    return str(key)[:MAX_KEYLEN]