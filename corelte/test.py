
import inspect
# from reading import Reading
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass
class Position:
    name: str
    lon: float = 0.0
    lat: float = 0.0

@dataclass
class PlayingCard:
    rank: str
    suit: str

RANKS = '2 3 4 5 6 7 8 9 10 J Q K A'.split()
SUITS = '♣ ♢ ♡ ♠'.split()

def make_french_deck():
    return [PlayingCard(r, s) for s in SUITS for r in RANKS]

@dataclass
class Deck:
    cards: List[PlayingCard] = field(default_factory = make_french_deck)


def main():
    #inspect(getmembers(mydataclass, inspect.isfunction))

    #print(Position('Genève', lon=6, lat=42))

    D = Deck()
    print(D)


if __name__ == "__main__":
    main()


