#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

import asyncio
from logging import getLogger
from asyncio import AbstractEventLoop
from typing import (
    Any,
    Dict,
    Optional,
    Protocol,
    TypeVar,
)

T = TypeVar('T')

__all__ = [
    'BackendT',
    'BaseBackend',
]


class BackendT(Protocol):

    ENCODING: str

    @property
    def loop(self) -> AbstractEventLoop:
        raise NotImplementedError

    async def close(self) -> None:
        ...

    async def get(self, key: str, _conn: Any) -> T:
        ...

    async def set(self, key: str, value: T, ttl: Optional[float], _conn: Any) -> bool:
        ...

    async def replace(self, key: str, value: T, ttl: Optional[float], _conn: Any) -> T:
        ...

    async def setmany(self, keys_vals: Dict[str, T], ttl: Optional[float], _conn: Any) -> int:
        ...

    async def expire(self, key: str, ttl: float, _conn: Any) -> bool:
        ...

    async def delete(self, key: str, _conn: Any) -> bool:
        ...

    async def clear(self, _conn: Any) -> None:
        ...


class BaseBackend:

    def __init__(self, loop: Optional[AbstractEventLoop] = None):
        self._loop = loop or asyncio.get_event_loop()
        self.logger = getLogger(f'aiocacher.backends.{self.__class__.__name__}')

    @property
    def loop(self) -> AbstractEventLoop:
        return self._loop

