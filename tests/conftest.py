#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

import os
import asyncio
import random
import string

import pytest

from aiocacher.cache import Cache
from aiocacher.backends.redis import RedisBackend


CHARS = string.ascii_letters + string.digits
REDIS_DB = int(os.getenv('REDIS_TEST_DB', '4'))


@pytest.fixture(scope='session')
def redis_port() -> int:
    return 16379


@pytest.fixture(scope='function')
@pytest.mark.asyncio
async def redis_backend(event_loop, redis_port):
    o = RedisBackend(
        port=redis_port,
        db=REDIS_DB,
        pool_minsize=1,
        pool_maxsize=3,
        loop=event_loop,
    )
    yield o
    await o.close()


@pytest.fixture(scope='function')
@pytest.mark.asyncio
async def cache(redis_backend):
    o = Cache(
        redis_backend,
        namespace='unittests',
        global_timeout=3.0,
    )
    yield o
    await o.close()


@pytest.fixture(scope='function')
def random_string(length: int = 16):
    return ''.join(random.choice(CHARS) for _ in range(length))


@pytest.fixture(scope="session", autouse=True)
def cleanup(request, redis_port):
    """Cleanup a testing directory once we are finished."""
    def clear_cache():
        loop = asyncio.get_event_loop()
        backend = RedisBackend(port=redis_port, db=REDIS_DB, loop=loop)
        loop.run_until_complete(backend.clear())
        loop.run_until_complete(backend.close())
        loop.close()
    request.addfinalizer(clear_cache)
