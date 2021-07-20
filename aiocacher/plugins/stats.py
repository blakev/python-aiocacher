#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, TypeVar

T = TypeVar('T')

__all__ = [
    'CacheStats',
    'StatsPlugin',
]


@dataclass(frozen=False, unsafe_hash=True)
class CacheStats:
    first_call: float = -1.0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_types: Counter = field(default_factory=Counter)

    @property
    def hit_ratio(self) -> float:
        return float(self.cache_hits) / float(self.cache_hits + self.cache_misses)

    @property
    def top_types(self) -> Dict[str, int]:
        counts = dict(self.cache_types.most_common(5))
        return {str(k): v for k, v in counts.items()}


class StatsPlugin:

    __slots__ = ('stats',)

    def __init__(self):
        self.stats = CacheStats()

    async def before_first_call(self):
        self.stats.first_call = time.monotonic()

    async def on_cache_hit(self, key: str):
        self.stats.cache_hits += 1

    async def on_cache_miss(self, key: str):
        self.stats.cache_misses += 1

    async def before_call(self):
        ...

    async def after_call(self, result: T) -> T:
        self.stats.cache_types[type(result)] += 1
        return result

    async def on_teardown(self):
        ...
