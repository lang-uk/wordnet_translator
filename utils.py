"""
Utility functions for the translator.
"""

from typing import Iterable, Tuple, TypeVar
import itertools

T = TypeVar("T")


def sliding_window(iterable: Iterable[T], n: int = 2) -> Iterable[Tuple[T, ...]]:
    """
    Returns a sliding window (of width n) over data from the iterable
    Args:
        iterable: iterable to slide over
        n: width of the window
    Returns:
        iterator over tuples of length n
    """
    iterables = itertools.tee(iterable, n)

    for iterable, num_skipped in zip(iterables, itertools.count()):
        for _ in range(num_skipped):
            next(iterable, None)

    return zip(*iterables)


class Singleton(type):
    """
    A simple singleton implementation
    """
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
