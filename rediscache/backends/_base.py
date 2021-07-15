#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

from asyncio import AbstractEventLoop
from typing import (
    Any,
    Dict,
    Optional,
    Protocol,
)


__all__ = [
    'BackendT',
]


class BackendT(Protocol):

    ENCODING: str
    loop: Optional[AbstractEventLoop] = None

    async def close(self) -> None:
        ...

    async def get(self, key: str, _conn: Any):
        ...

    async def set(self, key: str, value: bytes, ttl: Optional[float], _conn: Any):
        ...

    async def replace(self, key: str, value: bytes, ttl: Optional[float], _conn: Any):
        ...

    async def setmany(self, keys_vals: Dict[str, bytes], ttl: Optional[float], _conn: Any):
        ...

    async def expire(self, key: str, ttl: float, _conn: Any):
        ...

    async def delete(self, key: str, _conn: Any):
        ...

    async def clear(self, _conn: Any):
        ...
