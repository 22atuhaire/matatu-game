from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple


class Suit(str, Enum):
    CLUBS = "C"
    DIAMONDS = "D"
    HEARTS = "H"
    SPADES = "S"


class Rank(str, Enum):
    ACE = "A"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"


RANK_ORDER = [
    Rank.ACE, Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX,
    Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING
]


@dataclass(frozen=True)
class Card:
    suit: Suit
    rank: Rank

    def __str__(self) -> str:
        return f"{self.rank.value}{self.suit.value}"


def card_points(rank: Rank) -> int:
    if rank in (Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX, Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.TEN):
        return int(rank.value)
    if rank is Rank.JACK:
        return 11
    if rank is Rank.QUEEN:
        return 12
    if rank is Rank.KING:
        return 13
    if rank is Rank.ACE:
        return 15
    if rank is Rank.TWO:
        return 20
    raise ValueError("Unsupported rank")


class ActionType(Enum):
    PLAY = auto()
    DRAW = auto()
    PASS = auto()
    CUT = auto()


@dataclass
class Action:
    type: ActionType
    card: Optional[Card] = None
    declared_suit: Optional[Suit] = None  # for Ace plays


def same_suit(a: Card, b: Card) -> bool:
    return a.suit == b.suit


def same_rank(a: Card, b: Card) -> bool:
    return a.rank == b.rank
