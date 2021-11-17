#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

import random
import asyncio
from dataclasses import dataclass

import pytest

from aiocacher.cache import UNSET, Cache


# All test coroutines will be treated as marked.
from aiocacher.plugins.stats import StatsPlugin

pytestmark = pytest.mark.asyncio


@dataclass(unsafe_hash=True)
class Stats:
    count: int


async def test_missing(cache: Cache):
    assert await cache.get('hi') is None


@pytest.mark.parametrize('ins', [
    None,
    1,
    True,
    'hello, there',
    Stats(0),
])
async def test_set(cache: Cache, random_string, ins):
    key = random_string
    assert await cache.get(key, None) is None
    assert await cache.set(key, ins, ttl=1)
    out = await cache.get(key)
    assert out == ins
    await asyncio.sleep(1.1)
    assert await cache.get(key) is None


@pytest.mark.parametrize('ins', [
    (1, 2),
    (True, False),
    (Stats(1), Stats(5)),
    ('blake', 'vandemerwe'),
])
async def test_replace(cache: Cache, random_string, ins):
    a, b = ins
    await cache.set(random_string, a)
    c = await cache.replace(random_string, b)
    assert a == c
    assert await cache.get(random_string) == b
    d = await cache.replace(random_string, b, ttl=1)
    assert b == d
    await asyncio.sleep(1.1)
    assert await cache.get(random_string) is None


@pytest.mark.parametrize('ins', [
    True,
    False,
    None,
    'hello',
])
async def test_expire(cache: Cache, random_string, ins):
    await cache.set(random_string, ins)
    await cache.expire(random_string, 1)
    assert await cache.get(random_string, UNSET) == ins
    await asyncio.sleep(1.1)
    missing = object()
    assert await cache.get(random_string, missing) is missing


async def test_invalid_decorator(cache: Cache):

    with pytest.raises(RuntimeError):
        @cache.cached()
        def not_coroutine():
            return True

        not_coroutine()


@pytest.mark.parametrize('plugin', [
    None,
    StatsPlugin,
])
async def test_decorator(cache: Cache, random_string, plugin):

    if plugin is not None:
        plugin = plugin()
        cache.add_plugin(plugin)

    @cache.cached(namespace=random_string, ttl=1)
    async def func():
        return random.randint(0, 10)

    x = await func()
    for _ in range(100):
        assert await func() == x

    await asyncio.sleep(1)

    if plugin:
        assert plugin.stats.cache_misses == 1
        assert plugin.stats.cache_hits > 0
        assert str(int) in plugin.stats.top_types
        assert len(plugin.stats.top_types) == 1


async def test_clear_namespace(cache: Cache):

    @cache.cached(ttl=1, namespace='inside', omit_self=False)
    async def func(val: str):
        return True if val else False

    @cache.cached(ttl=1, namespace='outside', omit_self=False)
    async def other(val: str):
        return False if val else True

    assert await func('a')
    assert await func('b')
    assert await cache.clear_namespace('outside') == 0
    assert await cache.clear_namespace('inside') == 2
    assert await other('')
    assert await cache.clear_namespace('outside') == 1

