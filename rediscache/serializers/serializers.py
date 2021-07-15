#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

from typing import Any

import dill


__all__ = [
    'BaseSerializer',
    'DillSerializer',
]


class BaseSerializer:

    DEFAULT_ENCODING = 'latin-1'

    def __init__(self, encoding: str = DEFAULT_ENCODING):
        self.encoding = encoding or self.DEFAULT_ENCODING


class DillSerializer(BaseSerializer):

    def dumps(self, value: Any) -> bytes:
        ret = dill.dumps(value, byref=True)
        return ret

    def loads(self, value: bytes) -> Any:
        if value is None:
            return None
        return dill.loads(value)

