#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

"""cache.py

This is the main documentation for cache.py
"""

import asyncio
from time import monotonic
from asyncio import AbstractEventLoop
from logging import getLogger
from functools import wraps
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TypeVar,
)

from aiocacher.types import KeyBuildFn, TimeT
from aiocacher.utils import trim_key, default_key_builder, convert_ttl
from aiocacher.plugins import PluginT
from aiocacher.backends import BackendT
from aiocacher.serializers import SerializerT, DillSerializer

UNSET = object()
MISSING = object()
GLOBAL_TTL = object()
NO_CACHE = object()
T = TypeVar('T')


def timeout(func):
    """Enforces the global timeout from the cache instance."""

    @wraps(func)
    async def wrapped(self, *args, **kwargs):
        fut = func(self, *args, **kwargs)
        return await asyncio.wait_for(
            fut,
            timeout=self.global_timeout,
        )

    return wrapped


def locked(func):
    """Locks the Cache interface to perform only one SET-like operation at a time."""

    @wraps(func)
    async def wrapped(self, *args, **kwargs):
        async with self.lock:
            return await func(self, *args, **kwargs)

    return wrapped


def logged(func):
    """Logs the operation and how long it took to complete."""

    @wraps(func)
    async def wrapped(self, *args, **kwargs):
        start = monotonic()
        try:
            ret = await func(self, *args, **kwargs)
        except Exception as e:
            self.logger.exception(e)
            raise e
        else:
            self.logger.debug(
                '%s %s (took=%0.4f)',
                func.__name__.upper(),
                ret,
                monotonic() - start,
            )
            return ret

    return wrapped


class FnCache:

    def __init__(
        self,
        cache: 'Cache',
        key: Optional[str],
        ttl: Optional[TimeT],
        key_builder: Optional[KeyBuildFn],
        namespace: Optional[str],
        as_last_arg: bool = False,
        wait_for_write: bool = True,
        use_plugins: bool = True,
        omit_self: bool = True,
        cache_none: bool = True,
    ):
        if key_builder and not callable(key_builder):
            raise RuntimeError('key_builder must be callable')

        self._key = key
        self._ttl = ttl
        self._key_builder = key_builder
        self._namespace = namespace
        self._as_last_arg = as_last_arg
        self._wait_for_write = wait_for_write
        self._use_plugins = use_plugins
        self.cache = cache
        self._called = False
        self._omit_self = omit_self
        self._cache_none = cache_none

    @property
    def use_plugins(self) -> bool:
        if not self.cache.plugins:
            return False
        return self._use_plugins

    def __call__(self, func):

        if not asyncio.iscoroutinefunction(func):
            raise RuntimeError('caching only works on coroutine functions')

        # noinspection PyProtectedMember
        @wraps(func)
        async def wrapped(*args, **kwargs):
            if not self._called and self.use_plugins:
                await self.cache._before_first_call()
                self._called = True

            if self.use_plugins:
                await self.cache._before_call()

            res = await self.decorator(func, *args, **kwargs)

            if self.use_plugins:
                res = await self.cache._after_call(res)

            return res

        return wrapped

    def get_cache_key(self, func, args, kwargs) -> str:
        k = None

        if self._key:
            k = self._key

        elif self._key_builder:
            if self._omit_self and args:
                # we don't want to pass `self`, the first instance parameter of `func`
                #  to the key builder; default __repr__ will include memory location
                # which will taint our cache key builder with a non-static value.
                k = self._key_builder(func, args[1:], kwargs)
            else:
                # .. this is probably caching a staticmethod
                k = self._key_builder(func, args, kwargs)

        elif not args and not kwargs:
            k = f'{func.__module__ or ""}_{func.__qualname__}'

        if k:
            return trim_key(k)

        return default_key_builder(func, args, kwargs)

    # noinspection PyProtectedMember
    async def decorator(self, fn, *args, **kwargs) -> Any:
        key = self.get_cache_key(fn, args, kwargs)
        key = self.cache.build_key(key, namespace=self._namespace)

        # look for the value in the cache
        value = await self.cache.get(key, default=MISSING)

        if value is not MISSING:
            if self.use_plugins:
                await self.cache._on_cache_hit(key)
            return value

        else:
            if self.use_plugins:
                await self.cache._on_cache_miss(key)

        if self._as_last_arg:
            fut = fn(*args, self.cache, **kwargs)
        else:
            fut = fn(*args, **kwargs)

        result = await fut

        if result is not NO_CACHE:
            w_fut = self.cache.set(key, result, ttl=self._ttl)

            if self._wait_for_write:
                await w_fut
            else:
                asyncio.ensure_future(w_fut, loop=self.cache.loop)

        return result


class Cache:

    # yapf: disable
    def __init__(
        self,
        backend:        Optional[BackendT] = None,
        namespace:      str = None,
        serializer:     SerializerT = None,
        plugins:        Optional[List[PluginT]] = None,
        global_timeout: TimeT = 5,
        global_ttl:     Optional[TimeT] = None,
        key_builder:    Optional[KeyBuildFn] = None,
    ):
        # yapf: enable
        self._backend = backend

        ns = f'.{namespace}' if namespace else ''
        self.logger = getLogger(f'{__file__}.{self.__class__.__name__}{ns}')
        self.lock = asyncio.Lock()

        self._namespace = namespace
        self._serializer = serializer or DillSerializer()
        self._plugins = plugins or list()
        self._g_timeout = max(1, convert_ttl(global_timeout))
        self._g_ttl = max(1, convert_ttl(global_ttl)) if global_ttl else None
        self._key_builder = key_builder or default_key_builder

    @property
    def loop(self) -> AbstractEventLoop:
        return self._backend.loop

    @property
    def global_timeout(self) -> float:
        return self._g_timeout

    @property
    def plugins(self) -> List[PluginT]:
        return self._plugins

    def set_backend(self, backend: BackendT) -> None:
        self._backend = backend
        self.lock = asyncio.Lock(loop=self._backend.loop)

    def add_plugin(self, plugin: PluginT):
        self.logger.debug(f'adding {plugin}')
        self._plugins.append(plugin)

    async def close(self) -> None:
        self.logger.debug('shutting down')
        await self._on_teardown()
        await self._backend.close()

    def _get_ttl(self, ttl: Optional[TimeT]) -> Optional[int]:
        if ttl is GLOBAL_TTL:
            return self._g_ttl
        return convert_ttl(ttl)

    def build_key(self, key: str, namespace: Optional[str] = None) -> str:
        if namespace is not None:
            k = f'{namespace}:{key}'
        elif self._namespace:
            k = f'{self._namespace}:{key}'
        else:
            k = key
        return trim_key(k)

    def cached(
        self,
        key: Optional[str] = None,
        ttl: Optional[TimeT] = None,
        namespace: Optional[str] = None,
        key_builder: Optional[KeyBuildFn] = None,
        as_last_arg: bool = False,
        wait_for_write: bool = True,
        use_plugins: bool = True,
        omit_self: bool = True,
    ) -> FnCache:
        return FnCache(
            cache=self,  # backref
            key=key,
            ttl=ttl,
            namespace=namespace,
            key_builder=key_builder or self._key_builder,
            as_last_arg=as_last_arg,
            wait_for_write=wait_for_write,
            use_plugins=use_plugins,
            omit_self=omit_self,
        )

    @logged
    @timeout
    async def get(
        self,
        key: str,
        default=UNSET,
    ):
        key = self.build_key(key)
        val = await self._backend.get(key)
        val = self._serializer.loads(val)

        # handle None-like sentinel value for cached None values
        if val is not None:
            return val

        if default is UNSET:
            return None

        return default

    @logged
    @timeout
    @locked
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[TimeT] = GLOBAL_TTL,
    ) -> Any:
        key = self.build_key(key)
        val = self._serializer.dumps(value)
        ttl = self._get_ttl(ttl)
        res = await self._backend.set(key, val, ttl=ttl)
        return res

    @logged
    @timeout
    @locked
    async def setmany(
        self,
        keys_vals: Dict[str, Any],
        ttl: Optional[TimeT] = GLOBAL_TTL,
    ):
        # yapf: disable
        keys_vals = {
            self.build_key(k): self._serializer.dumps(v)
            for k, v in keys_vals.items()
        }
        # yapf: enable
        ttl = self._get_ttl(ttl)
        res = await self._backend.setmany(keys_vals, ttl=ttl)
        return res

    @logged
    @timeout
    @locked
    async def replace(
        self,
        key: str,
        value: Any,
        ttl: Optional[TimeT] = GLOBAL_TTL,
    ) -> Any:
        key = self.build_key(key)
        val = self._serializer.dumps(value)
        ttl = self._get_ttl(ttl)
        res = await self._backend.replace(key, val, ttl=ttl)
        res = self._serializer.loads(res)
        return res

    @logged
    @timeout
    async def expire(
        self,
        key: str,
        ttl: TimeT,
    ) -> Any:
        key = self.build_key(key)
        ttl = convert_ttl(ttl)
        res = await self._backend.expire(key, ttl)
        return res

    @logged
    @timeout
    @locked
    async def delete(self, key: str) -> bool:
        key = self.build_key(key)
        res = await self._backend.delete(key)
        return res

    @logged
    @timeout
    @locked
    async def purge(self) -> None:
        await self._backend.purge()

    @logged
    @timeout
    @locked
    async def clear_namespace(self, namespace: str) -> int:
        return await self._backend.clear_namespace(self._namespace, namespace)

    # plugin helpers

    async def _before_first_call(self) -> None:
        for plugin in self.plugins:
            await plugin.before_first_call()

    async def _on_cache_hit(self, key: str) -> None:
        for plugin in self.plugins:
            await plugin.on_cache_hit(key)

    async def _on_cache_miss(self, key: str) -> None:
        for plugin in self.plugins:
            await plugin.on_cache_miss(key)

    async def _before_call(self) -> None:
        for plugin in self.plugins:
            await plugin.before_call()

    async def _after_call(self, result: T) -> T:
        for plugin in self.plugins:
            result = await plugin.after_call(result)
        return result

    async def _on_teardown(self) -> None:
        for plugin in self.plugins:
            await plugin.on_teardown()
