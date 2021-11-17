#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

import random
from dataclasses import dataclass
from typing import Optional

import pytest

from aiocacher.serializers import DillSerializer, JsonSerializer, PickleSerializer


@dataclass(unsafe_hash=True)
class Stats:
    a: Optional[int]
    b: Optional[list]
    c: Optional[dict]

    @classmethod
    def gen(cls) -> 'Stats':
        x = random.choice([None, cls(a=0, b=[], c={})])
        a = random.choice([None, 1])
        b = random.choice([None, [x]])
        c = random.choice([None, {'x': x}])
        return cls(a=a, b=b, c=c)


@pytest.mark.parametrize('serializer', [
    PickleSerializer(),
    DillSerializer(),
    JsonSerializer(),
])
@pytest.mark.parametrize('ins', [
    1,
    0x01,
    0b01,
    'string',
    123.123,
    dict(a=1, b=2),
    [1, None, True, False, 'string'],
    {'a': ['b', {'c': None}]},
])
def test_serializer(serializer, ins):
    x = serializer.dumps(ins)
    assert serializer.loads(x) == ins, x


@pytest.mark.parametrize('serializer', [
    PickleSerializer(),
    DillSerializer(),
])
@pytest.mark.parametrize('ins', [Stats.gen() for _ in range(10)])
def test_binary_serializers_dataclass(serializer, ins):
    x = serializer.dumps(ins)
    assert serializer.loads(x) == ins, x
