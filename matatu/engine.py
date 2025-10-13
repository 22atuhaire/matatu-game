from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .types import Card, Suit, Rank, Action, ActionType, same_rank, same_suit, card_points


def generate_deck() -> List[Card]:
    deck: List[Card] = []
    for suit in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        for rank in [
            Rank.ACE, Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX,
            Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING
        ]:
            deck.append(Card(suit, rank))
    return deck


@dataclass
class PlayerState:
    hand: List[Card] = field(default_factory=list)


@dataclass
class GameState:
    stock: List[Card]
    discard: List[Card]
    players: List[PlayerState]
    current_player: int
    cut_suit: Suit
    pending_draw: int = 0  # accumulated from 2's
    declared_suit: Optional[Suit] = None  # from Ace
    winner: Optional[int] = None

    def top_discard(self) -> Card:
        return self.discard[-1]


def deal_new_game(rng: random.Random) -> GameState:
    deck = generate_deck()
    rng.shuffle(deck)

    # First card defines cut suit (kept under deck conceptually); next starts discard.
    cut_card = deck.pop(0)  # top of deck
    cut_suit = cut_card.suit

    # Start discard
    first_discard = deck.pop(0)

    # Two players: human (0) vs CPU (1)
    players = [PlayerState(), PlayerState()]
    for _ in range(7):
        for p in players:
            p.hand.append(deck.pop(0))

    state = GameState(
        stock=deck,
        discard=[first_discard],
        players=players,
        current_player=0,
        cut_suit=cut_suit,
    )
    return state


def is_play_legal(state: GameState, card: Card) -> bool:
    top = state.top_discard()
    # A cannot be played on a 2
    if top.rank is Rank.TWO and card.rank is Rank.ACE:
        return False
    # If an Ace suit was declared previously, match that suit unless using rank match
    effective_suit = state.declared_suit if state.declared_suit is not None else top.suit

    if same_rank(card, top):
        return True
    if card.rank is Rank.ACE:
        return True  # A is wild (suit will be declared on action)
    return card.suit == effective_suit


def legal_plays(state: GameState, player_idx: int) -> List[Card]:
    if state.winner is not None:
        return []
    hand = state.players[player_idx].hand
    # If pending draw from 2's, player may only defend with a TWO (stack), else must draw
    if state.pending_draw > 0:
        return [c for c in hand if c.rank is Rank.TWO]
    
    # Calculate total points to check if 7 of cut suit should be excluded
    total_points = sum(card_points(c.rank) for c in hand)
    
    legal = [c for c in hand if is_play_legal(state, c)]
    
    # If player has more than 25 points, exclude 7 of cut suit from legal plays
    if total_points > 25:
        legal = [c for c in legal if not (c.rank is Rank.SEVEN and c.suit is state.cut_suit)]
    
    return legal


def apply_action(state: GameState, action: Action) -> GameState:
    if state.winner is not None:
        return state

    player = state.players[state.current_player]

    if action.type is ActionType.PLAY:
        assert action.card is not None
        card = action.card
        # Remove from hand
        player.hand.remove(card)
        # Reset previous Ace declaration unless playing another Ace
        state.declared_suit = None
        # Place card
        state.discard.append(card)
        # Effects
        if card.rank is Rank.TWO:
            state.pending_draw += 2
            state.current_player = (state.current_player + 1) % 2
        elif card.rank is Rank.EIGHT:
            # Extra turn, cannot be final card enforced by caller/UI
            # current_player unchanged
            pass
        elif card.rank is Rank.JACK:
            # Extra turn, cannot be final card enforced by caller/UI
            pass
        elif card.rank is Rank.ACE:
            # Must have declared suit
            if action.declared_suit is None:
                raise ValueError("Ace requires declared_suit")
            state.declared_suit = action.declared_suit
            # Extra turn? Not specified; treat as normal turn end
            state.current_player = (state.current_player + 1) % 2
        elif card.rank is Rank.SEVEN and card.suit is state.cut_suit:
            # Playing 7 of cut suit automatically triggers cut
            # Check if player can cut (total points <= 25)
            total = sum(card_points(c.rank) for c in player.hand)
            if total <= 25:
                # Compute scores; lowest points wins
                other = state.players[(state.current_player + 1) % 2]
                a = total
                b = sum(card_points(c.rank) for c in other.hand)
                state.winner = state.current_player if a < b else (state.current_player + 1) % 2
                return state
            else:
                # Cannot cut due to high points, continue normal turn
                state.current_player = (state.current_player + 1) % 2
        else:
            state.current_player = (state.current_player + 1) % 2

        # Win check
        if len(player.hand) == 0:
            state.winner = state.current_player ^ 1  # previous player
        return state

    if action.type is ActionType.DRAW:
        # Draw pending if any, else 1
        to_draw = state.pending_draw if state.pending_draw > 0 else 1
        state.pending_draw = 0
        drawn: List[Card] = []
        for _ in range(to_draw):
            if not state.stock:
                # reshuffle discard except top
                top = state.discard.pop()
                tmp = state.discard
                random.shuffle(tmp)
                state.stock = tmp
                state.discard = [top]
            if not state.stock:  # still empty
                break
            drawn.append(state.stock.pop(0))
        state.players[state.current_player].hand.extend(drawn)
        # After drawing, player may play immediately if possible; UI/driver decides next
        state.current_player = (state.current_player + 1) % 2
        return state

    if action.type is ActionType.PASS:
        state.current_player = (state.current_player + 1) % 2
        return state

    if action.type is ActionType.CUT:
        # Valid only if player has 7 of cut suit and total points <= 25
        total = sum(card_points(c.rank) for c in player.hand)
        has_cut_seven = any((c.rank is Rank.SEVEN and c.suit is state.cut_suit) for c in player.hand)
        if not has_cut_seven or total > 25:
            raise ValueError("Invalid cut")
        # Compute scores; lowest points wins
        other = state.players[(state.current_player + 1) % 2]
        a = total
        b = sum(card_points(c.rank) for c in other.hand)
        state.winner = state.current_player if a < b else (state.current_player + 1) % 2
        return state

    raise ValueError("Unknown action")
