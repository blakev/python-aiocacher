#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<


from aiocacher.utils import *


def test_chunk():
    assert list(chunks(range(5), 3)) == [(0, 1, 2), (3, 4)]
