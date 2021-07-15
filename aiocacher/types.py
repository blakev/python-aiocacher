#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# >>
#   async-redis-cache, 2021
#   LiveViewTech
# <<

from typing import (
    Any,
    Dict,
    Tuple,
    Callable,
    Protocol,
)


class Callback(Protocol):

    def __call__(self, *args, **kwargs) -> Any:
        ...


KeyBuildFn = Callable[[Callable, Tuple[Any, ...], Dict[str, Any]], str]
