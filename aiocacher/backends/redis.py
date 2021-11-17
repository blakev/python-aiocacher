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
)

import aioredis
from aioredis import Redis
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
            _conn = await self.get_pool()
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
        pool_maxsize: int = 10,
        connect_timeout: Optional[float] = None,
        client_name: Optional[str] = None,
        loop: Optional[AbstractEventLoop] = None,
    ):
        super().__init__(loop=loop)

        self._host = host
        self._port = port
        self._db = max(0, db)
        self._password = password
        self._maxsize = pool_maxsize
        self._conn_timeout = max(0.1, connect_timeout) if connect_timeout else None
        self._client_name = client_name

        self._conn: Optional[Redis] = None
        self._conn_lock = asyncio.Lock()

    async def setup(self, loop: AbstractEventLoop, **kwargs) -> None:
        """Allow a deferred setup until after the event loop is running."""
        await self.close()
        self.logger.debug('updating event loop')
        self._loop = loop

    async def get_pool(self) -> Redis:
        async with self._conn_lock:
            if self._conn and self._conn.connection is not None:
                return self._conn
            kw = {
                'db': self._db,
                'max_connections': self._maxsize,
                'password': self._password,
                'socket_timeout': self._conn_timeout,
                'retry_on_timeout': True,
                'health_check_interval': 2,
                'client_name': self._client_name,
            }
            self._conn = aioredis.from_url(f'redis://{self._host}:{self._port}', **kw)
            return self._conn

    async def close(self) -> None:
        if self._conn is None:
            return
        await self._conn.close()

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
        ttl: Optional[int],
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
        ttl: Optional[int],
        _conn: Redis,
    ) -> bytes:
        if ttl:
            async with _conn.pipeline(transaction=True) as pipe:
                res, _ = await (pipe.getset(key, value).expire(key, ttl).execute())
                return res
        return await _conn.getset(key, value)

    @connection
    async def setmany(
        self,
        keys_vals: Dict[str, bytes],
        ttl: Optional[int],
        _conn: Redis,
    ) -> int:
        for chunk in partition_all(100, keys_vals.items()):
            await _conn.mset(chunk)
            async with _conn.pipeline(transaction=True) as pipe:
                for k, _ in chunk:
                    pipe = pipe.expire(k, ttl)
                await pipe.execute()
        return len(keys_vals)

    @connection
    async def expire(
        self,
        key: str,
        ttl: int,
        _conn: Redis,
    ) -> bool:
        return await _conn.expire(key, ttl)

    @connection
    async def delete(self, key: str, _conn: Redis) -> bool:
        return await _conn.delete(key)

    @connection
    async def purge(self, _conn: Redis) -> None:
        await _conn.flushdb()

    @connection
    async def clear_namespace(
        self,
        global_namespace: str,
        namespace: str,
        _conn: Redis,
    ) -> int:
        count = 0
        cursor = b'0'
        namespace = f'{global_namespace}:{namespace}:'
        while cursor:
            cursor, keys = await _conn.scan(cursor, match=f'{namespace}*')
            if keys:
                count += len(keys)
                key, *keys = keys
                await _conn.delete(key, *keys)
        return count
