#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

from typing import Protocol, TypeVar

T = TypeVar('T')

__all__ = [
    'PluginT',
]


class PluginT(Protocol):

    async def before_first_call(self):
        ...

    async def on_cache_hit(self, key: str):
        ...

    async def on_cache_miss(self, key: str):
        ...

    async def before_call(self):
        ...

    async def after_call(self, result: T) -> T:
        ...

    async def on_teardown(self):
        ...
