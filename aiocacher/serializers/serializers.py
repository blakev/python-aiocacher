#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

import pickle
from dataclasses import asdict, _is_dataclass_instance
from typing import Any, Dict

try:
    import ujson as json

except ImportError:
    import json

__all__ = [
    'BaseSerializer',
    'JsonSerializer',
    'PickleSerializer',
    'DillSerializer',
]


class BaseSerializer:

    __slots__ = ('encoding',)

    DEFAULT_ENCODING = 'latin-1'

    def __init__(self, encoding: str = DEFAULT_ENCODING):
        self.encoding = encoding or self.DEFAULT_ENCODING


class JsonSerializer(BaseSerializer):

    def __init__(
        self,
        encoding: str = BaseSerializer.DEFAULT_ENCODING,
        dump_kwargs: Dict[str, Any] = None,
        load_kwargs: Dict[str, Any] = None,
    ):
        super().__init__(encoding=encoding)
        self._dump_kwargs = dump_kwargs or dict()
        self._load_kwargs = load_kwargs or dict()

    def dumps(self, value: Any) -> bytes:
        ret = json.dumps(value, **self._dump_kwargs)
        if isinstance(ret, str):
            ret = ret.encode(self.encoding)
        return ret

    def loads(self, value: bytes) -> Any:
        return json.loads(value, **self._load_kwargs)


class PickleSerializer(BaseSerializer):

    def dumps(self, value: Any) -> bytes:
        ret = pickle.dumps(value)
        return ret

    def loads(self, value: bytes) -> Any:
        if value is None:
            return None
        return pickle.loads(value)


try:
    import dill

    class DillSerializer(BaseSerializer):

        def dumps(self, value: Any) -> bytes:
            ret = dill.dumps(value, byref=True)
            return ret

        def loads(self, value: bytes) -> Any:
            if value is None:
                return None
            return dill.loads(value)

except ImportError:
    # fallback
    DillSerializer = PickleSerializer
