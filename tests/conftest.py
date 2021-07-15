#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

import random
import string

import pytest

from rediscache.cache import Cache
from rediscache.backends.redis import RedisBackend


CHARS = string.ascii_letters + string.digits


@pytest.fixture(scope='function')
@pytest.mark.asyncio
async def redis_backend(event_loop):
    o = RedisBackend(
        port=16379,
        db=4,
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


@pytest.fixture(scope='function')
def random_string(length: int = 16):
    return ''.join(random.choice(CHARS) for _ in range(length))