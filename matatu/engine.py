from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .types import (
    Card,
    Suit,
    Rank,
    Action,
    ActionType,
    same_rank,
    same_suit,
    card_points,
)


def generate_deck() -> List[Card]:
    deck: List[Card] = []
    for suit in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        for rank in [
            Rank.ACE,
            Rank.TWO,
            Rank.THREE,
            Rank.FOUR,
            Rank.FIVE,
            Rank.SIX,
            Rank.SEVEN,
            Rank.EIGHT,
            Rank.NINE,
            Rank.TEN,
            Rank.JACK,
            Rank.QUEEN,
            Rank.KING,
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
    awaiting_declare: Optional[int] = (
        None  # which player must declare after playing Ace
    )
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
    # If a declaration is pending, no card play is legal until suit is declared
    if state.awaiting_declare is not None:
        return False
    top = state.top_discard()
    # A cannot be played on a 2 if there's still a pending draw
    if state.pending_draw > 0 and top.rank is Rank.TWO and card.rank is Rank.ACE:
        return False
    # If an Ace suit was declared previously, match that suit unless using rank match
    effective_suit = (
        state.declared_suit if state.declared_suit is not None else top.suit
    )

    if same_rank(card, top):
        return True
    if card.rank is Rank.ACE:
        return True  # A is wild (suit will be declared on action)
    return card.suit == effective_suit


def legal_plays(state: GameState, player_idx: int) -> List[Card]:
    if state.winner is not None:
        return []
    # If this player must declare due to a previously played Ace, no plays are legal
    if state.awaiting_declare == player_idx:
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
        legal = [
            c for c in legal if not (c.rank is Rank.SEVEN and c.suit is state.cut_suit)
        ]

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
            # Two-step: show Ace on top first; require a separate DECLARE action
            state.awaiting_declare = state.current_player
            # Turn does not advance until declaration
            return state
        elif card.rank is Rank.SEVEN and card.suit is state.cut_suit:
            # Playing 7 of cut suit automatically triggers cut
            # Check if player can cut (total points <= 25)
            total = sum(card_points(c.rank) for c in player.hand)
            if total <= 25:
                # Compute scores; lowest points wins
                other = state.players[(state.current_player + 1) % 2]
                a = total
                b = sum(card_points(c.rank) for c in other.hand)
                state.winner = (
                    state.current_player if a < b else (state.current_player + 1) % 2
                )
                return state
            else:
                # Cannot cut due to high points, continue normal turn
                state.current_player = (state.current_player + 1) % 2
        else:
            state.current_player = (state.current_player + 1) % 2

        # Win check
        # Only check for winner if this wasn't an Ace play (which requires declaration)
        if len(player.hand) == 0 and card.rank is not Rank.ACE:
            state.winner = state.current_player ^ 1  # previous player
        return state

    if action.type is ActionType.DRAW:
        # Cannot draw if awaiting declaration
        if state.awaiting_declare is not None:
            raise ValueError("Must declare suit before other actions")
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
        if state.awaiting_declare is not None:
            raise ValueError("Must declare suit before passing")
        state.current_player = (state.current_player + 1) % 2
        return state

    if action.type is ActionType.CUT:
        if state.awaiting_declare is not None:
            raise ValueError("Must declare suit before cutting")
        # Valid only if player has 7 of cut suit and total points <= 25
        total = sum(card_points(c.rank) for c in player.hand)
        # Locate the cutting card (7 of cut suit)
        cut_card: Optional[Card] = None
        for c in player.hand:
            if c.rank is Rank.SEVEN and c.suit is state.cut_suit:
                cut_card = c
                break
        if cut_card is None or total > 25:
            raise ValueError("Invalid cut")
        # Place the cutting card on the discard pile so it's visible on top
        player.hand.remove(cut_card)
        state.discard.append(cut_card)
        # Compute scores; lowest points wins
        other = state.players[(state.current_player + 1) % 2]
        a = total - card_points(
            cut_card.rank
        )  # player's remaining hand points after placing the cut card
        b = sum(card_points(c.rank) for c in other.hand)
        state.winner = state.current_player if a < b else (state.current_player + 1) % 2
        return state
    if action.type is ActionType.DECLARE:
        # Only valid if awaiting declaration for current player
        if state.awaiting_declare != state.current_player:
            raise ValueError("No declaration pending")
        if action.declared_suit is None:
            raise ValueError("Declared suit required")
        state.declared_suit = action.declared_suit
        state.awaiting_declare = None
        # After declaring, check if this was the last card
        if len(player.hand) == 0:
            state.winner = state.current_player  # current player wins with Ace
        else:
            # If not the last card, end the turn (Ace does not grant extra turn)
            state.current_player = (state.current_player + 1) % 2
        return state

    raise ValueError("Unknown action")
