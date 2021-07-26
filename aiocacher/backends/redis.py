#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

import asyncio
from asyncio import AbstractEventLoop
from functools import wraps
from typing import (
    Dict,
    Callable,
    Optional,
    cast,
)

from aioredis import Redis, create_redis_pool
from aioredis.pool import ConnectionsPool
from toolz.itertoolz import partition_all

from aiocacher.backends import BaseBackend

__all__ = [
    'RedisBackend',
]


def connection(func: Callable):
    """Returns a fresh Redis connection to do operations on."""

    @wraps(func)
    async def wrapped(
        self,
        *args,
        _conn: Optional[Redis] = None,
        **kwargs,
    ):
        # if we don't have an active connection already open
        #  then we need to get one, run the command, return the
        # result, and close the connection.
        if _conn is None:
            pool = await self.get_pool()
            with await pool as _conn:
                _conn = cast(Redis, _conn)
                return await func(self, *args, _conn=_conn, **kwargs)
        # .. otherwise we can run the command but wait for its
        #  wrapper, further up the call stack, to clean up the connection.
        _conn = cast(Redis, _conn)
        return await func(self, *args, _conn=_conn, **kwargs)

    return wrapped


class RedisBackend(BaseBackend):

    ENCODING = 'latin-1'

    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        pool_minsize: int = 2,
        pool_maxsize: int = 10,
        connect_timeout: Optional[float] = None,
        loop: Optional[AbstractEventLoop] = None,
    ):
        super().__init__(loop=loop)

        self._host = host
        self._port = port
        self._db = max(0, db)
        self._password = password
        self._minsize = pool_minsize
        self._maxsize = pool_maxsize
        self._conn_timeout = max(0.1, connect_timeout) if connect_timeout else None

        self._pool: Optional[ConnectionsPool] = None
        self._pool_lock = asyncio.Lock()

    async def setup(self, loop: AbstractEventLoop, **kwargs) -> None:
        """Allow a deferred setup until after the event loop is running."""
        await self.close()
        self.logger.debug('updating event loop')
        self._loop = loop

    async def get_pool(self) -> ConnectionsPool:
        async with self._pool_lock:
            if self._pool and not self._pool.closed:
                return self._pool

            kwargs = {
                'db': self._db,
                'minsize': self._minsize,
                'maxsize': self._maxsize,
                'password': self._password,
                'timeout': self._conn_timeout,
            }

            self._pool = await create_redis_pool(
                (self._host, self._port),
                **kwargs,
            )

            return self._pool

    async def close(self) -> None:
        if self._pool is None:
            return
        self._pool.close()
        await self._pool.wait_closed()

    @connection
    async def get(
        self,
        key: str,
        _conn: Redis,
    ) -> bytes:
        return await _conn.get(key)

    @connection
    async def set(
        self,
        key: str,
        value: bytes,
        ttl: Optional[float],
        _conn: Redis,
    ) -> bool:
        if ttl:
            return await _conn.setex(key, ttl, value)
        return await _conn.set(key, value)

    @connection
    async def replace(
        self,
        key: str,
        value: bytes,
        ttl: Optional[float],
        _conn: Redis,
    ) -> bytes:
        if ttl:
            pipe = _conn.multi_exec()
            res = pipe.getset(key, value)
            _ = pipe.expire(key, ttl)
            await pipe.execute()
            return await res
        return await _conn.getset(key, value)

    @connection
    async def setmany(
        self,
        keys_vals: Dict[str, bytes],
        ttl: Optional[float],
        _conn: Redis,
    ) -> int:
        for chunk in partition_all(100, keys_vals.items()):
            await _conn.mset(chunk)
            pipe = _conn.multi_exec()
            for k, _ in chunk:
                pipe.expire(k, ttl)
            await pipe.execute()
        return len(keys_vals)

    @connection
    async def expire(
        self,
        key: str,
        ttl: float,
        _conn: Redis,
    ) -> bool:
        return await _conn.expire(key, ttl)

    @connection
    async def delete(self, key: str, _conn: Redis) -> bool:
        return await _conn.delete(key)

    @connection
    async def clear(self, _conn: Redis) -> None:
        await _conn.flushdb(async_op=True)
