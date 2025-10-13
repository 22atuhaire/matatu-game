from __future__ import annotations
import random
from typing import Optional, List

from .types import Card, Suit, Rank, Action, ActionType, card_points
from .engine import GameState, legal_plays


def choose_suit_by_majority(hand: List[Card]) -> Suit:
    counts = {s: 0 for s in (Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES)}
    for c in hand:
        counts[c.suit] += 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def cpu_choose_action(state: GameState, rng: random.Random) -> Action:
    idx = state.current_player
    # If CPU must declare after playing Ace, declare majority suit now
    if getattr(state, 'awaiting_declare', None) == idx:
        suit = choose_suit_by_majority(state.players[idx].hand)
        return Action(ActionType.DECLARE, declared_suit=suit)
    plays = legal_plays(state, idx)

    # Check if CPU can cut (has 7 of cut suit and total points <= 25)
    total_points = sum(card_points(c.rank) for c in state.players[idx].hand)
    has_cut_seven = any((c.rank is Rank.SEVEN and c.suit is state.cut_suit) for c in state.players[idx].hand)
    
    if has_cut_seven and total_points <= 25:
        return Action(ActionType.CUT)

    if not plays:
        return Action(ActionType.DRAW)

    # Respond to penalties with 2 if available
    twos = [c for c in plays if c.rank is Rank.TWO]
    if state.pending_draw > 0 and twos:
        return Action(ActionType.PLAY, card=twos[0])

    # Prefer specials: 2, 8, J, A (but not 7 of cut suit)
    specials_order = [Rank.TWO, Rank.EIGHT, Rank.JACK, Rank.ACE]
    for r in specials_order:
        for c in plays:
            if c.rank is r:
                # Never play 7 of cut suit - it should be used for cutting
                if c.rank is Rank.SEVEN and c.suit is state.cut_suit:
                    continue
                if c.rank is Rank.ACE:
                    # Play the Ace first; we'll declare on next action
                    return Action(ActionType.PLAY, card=c)
                return Action(ActionType.PLAY, card=c)

    # Otherwise play any legal card (bias to high ranks to reduce points)
    plays_sorted = sorted(plays, key=lambda c: (c.rank.value))
    return Action(ActionType.PLAY, card=plays_sorted[-1])
