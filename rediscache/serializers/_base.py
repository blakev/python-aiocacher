#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

from typing import TypeVar, Protocol


VT = TypeVar('VT')  # ValueType
ST = TypeVar('ST')  # StoreType

__all__ = [
    'BaseSerializer',
]


class BaseSerializer(Protocol):

    def dumps(self, value: VT) -> ST:
        """Converts a value of type T to a binary representation that
        can be stored in Redis for caching."""
        raise NotImplementedError

    def loads(self, value: ST) -> VT:
        """Converts a binary representation of type T back to its oroginal format
        after being retrieved from the Redis cache."""
        raise NotImplementedError

