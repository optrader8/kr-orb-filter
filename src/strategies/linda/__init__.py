"""Linda Raschke trading strategies implementation."""

from .holy_grail import HolyGrailStrategy
from .turtle_soup import TurtleSoupStrategy
from .anti_swing import AntiSwingStrategy

__all__ = [
    'HolyGrailStrategy',
    'TurtleSoupStrategy',
    'AntiSwingStrategy',
]