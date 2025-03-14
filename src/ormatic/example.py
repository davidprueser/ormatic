from dataclasses import dataclass
from enum import Enum

from typing_extensions import List, Optional


@dataclass
class Position:
    x: float
    y: float
    z: float


@dataclass
class Orientation:
    x: float
    y: float
    z: float
    w: Optional[float]


@dataclass
class Pose:
    position: Position
    orientation: Orientation


@dataclass
class Positions:
    positions: List[Position]
    # some_strings: List[str] array are postgresql only :(

@dataclass
class Position4D(Position):
    w: float


class ValueEnum(int, Enum):
    A = 1
    B = 2
    C = 3

@dataclass
class EnumContainer:
    value: ValueEnum