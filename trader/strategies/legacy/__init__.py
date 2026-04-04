"""Legacy strategy implementations."""

from trader.strategies.legacy.v6_pyramid import V6PyramidStrategy
from trader.strategies.legacy.v53_sop import V53SopStrategy
from trader.strategies.legacy.v7_structure import V7StructureStrategy

__all__ = [
    'V6PyramidStrategy',
    'V53SopStrategy',
    'V7StructureStrategy',
]
