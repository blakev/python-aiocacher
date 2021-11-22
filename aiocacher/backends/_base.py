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

    async def setup(self, loop: AbstractEventLoop, **kwargs) -> None:
        ...

    async def close(self) -> None:
        ...

    async def get(self, key: str, _conn: Any) -> T:
        ...

    async def set(self, key: str, value: T, ttl: Optional[int], _conn: Any) -> bool:
        ...

    async def replace(self, key: str, value: T, ttl: Optional[int], _conn: Any) -> T:
        ...

    async def setmany(self, keys_vals: Dict[str, T], ttl: Optional[int], _conn: Any) -> int:
        ...

    async def expire(self, key: str, ttl: int, _conn: Any) -> bool:
        ...

    async def delete(self, key: str, _conn: Any) -> bool:
        ...

    async def purge(self, _conn: Any) -> None:
        ...

    async def clear_namespace(self, global_namespace: str, namespace: str, _conn: Any) -> int:
        ...


class BaseBackend:

    def __init__(self, loop: Optional[AbstractEventLoop] = None):
        self._loop = loop or asyncio.get_event_loop()
        self.logger = getLogger(f'aiocacher.backends.{self.__class__.__name__}')

    @property
    def loop(self) -> AbstractEventLoop:
        return self._loop




