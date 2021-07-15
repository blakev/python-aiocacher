#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

import pytest

from aiocacher.serializers import DillSerializer


@pytest.fixture(scope='function')
def serializer() -> DillSerializer:
    return DillSerializer()


@pytest.mark.parametrize('ins', [
    1,
    0x01,
    0b01,
    'string',
    123.123,
    dict(a=1, b=2),
])
def test_serializer(serializer: DillSerializer, ins):
    assert serializer.loads(serializer.dumps(ins)) == ins, ins
