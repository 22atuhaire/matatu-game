from __future__ import annotations
import random
from typing import Optional

# Allow running as a script: python matatu/cli.py
try:
    from .engine import deal_new_game, GameState, apply_action, legal_plays  # type: ignore
    from .types import Action, ActionType, Suit, Card, Rank  # type: ignore
    from .cpu import cpu_choose_action  # type: ignore
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from matatu.engine import deal_new_game, GameState, apply_action, legal_plays  # type: ignore
    from matatu.types import Action, ActionType, Suit, Card, Rank  # type: ignore
    from matatu.cpu import cpu_choose_action  # type: ignore


def print_state(state: GameState) -> None:
    top = state.top_discard()
    print(f"Top: {top}  | Cut suit: {state.cut_suit.value}  | Pending draw: {state.pending_draw}  | Declared suit: {state.declared_suit.value if state.declared_suit else '-'}")


def hand_str(cards) -> str:
    return " ".join(str(c) for c in cards)


def parse_card(token: str) -> Optional[Card]:
    token = token.strip().upper()
    if len(token) < 2:
        return None
    suit_map = {"C": Suit.CLUBS, "D": Suit.DIAMONDS, "H": Suit.HEARTS, "S": Suit.SPADES}
    # ranks can be 10
    if token[:-1] == "10":
        rank = Rank.TEN
        suit = suit_map.get(token[-1])
        if suit is None:
            return None
        return Card(suit, rank)
    rank_map = {
        "A": Rank.ACE, "2": Rank.TWO, "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
        "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE, "J": Rank.JACK,
        "Q": Rank.QUEEN, "K": Rank.KING,
    }
    rank = rank_map.get(token[0])
    suit = suit_map.get(token[1]) if len(token) >= 2 else None
    if rank is None or suit is None:
        return None
    return Card(suit, rank)


def choose_suit_interactive() -> Suit:
    while True:
        s = input("Choose suit [C/D/H/S]: ").strip().upper()
        if s in ("C", "D", "H", "S"):
            return {"C": Suit.CLUBS, "D": Suit.DIAMONDS, "H": Suit.HEARTS, "S": Suit.SPADES}[s]


def player_turn(state: GameState) -> GameState:
    plays = legal_plays(state, 0)
    print_state(state)
    print(f"Your hand: {hand_str(state.players[0].hand)}")
    if state.pending_draw > 0 and not plays:
        print(f"You must draw {state.pending_draw}.")
    if not plays:
        input("Press Enter to draw...")
        return apply_action(state, Action(ActionType.DRAW))

    print(f"Legal plays: {hand_str(plays)}  | Enter card (e.g., 8H), or 'draw', or 'cut'")
    while True:
        cmd = input("> ").strip().lower()
        if cmd == "draw":
            return apply_action(state, Action(ActionType.DRAW))
        if cmd == "cut":
            try:
                return apply_action(state, Action(ActionType.CUT))
            except Exception as e:
                print(f"Invalid cut: {e}")
                continue
        card = parse_card(cmd.upper())
        if card and card in state.players[0].hand and card in plays:
            if card.rank is Rank.ACE:
                suit = choose_suit_interactive()
                return apply_action(state, Action(ActionType.PLAY, card=card, declared_suit=suit))
            # Enforce cannot end on 8 or J
            if len(state.players[0].hand) == 1 and card.rank in (Rank.EIGHT, Rank.JACK):
                print("Cannot finish on 8 or J. Choose another card.")
                continue
            return apply_action(state, Action(ActionType.PLAY, card=card))
        print("Invalid input. Try again.")


def cpu_turn(state: GameState, rng: random.Random) -> GameState:
    action = cpu_choose_action(state, rng)
    # Enforce cannot finish on 8 or J
    if action.type is ActionType.PLAY and len(state.players[1].hand) == 1 and action.card and action.card.rank in (Rank.EIGHT, Rank.JACK):
        # Fallback: draw instead
        action = Action(ActionType.DRAW)
    return apply_action(state, action)


def main() -> None:
    rng = random.Random()
    balance = 1000
    stake = 50
    print("Matatu (Casino) - 1vCPU. Type Ctrl+C to quit.")
    print(f"Starting balance: {balance}. Default stake per hand: {stake}.")

    while True:
        try:
            print("\n--- New Hand ---")
            print(f"Stake: {stake} | Balance: {balance}")
            state = deal_new_game(rng)
            # Simple turn loop
            while state.winner is None:
                if state.current_player == 0:
                    state = player_turn(state)
                else:
                    state = cpu_turn(state, rng)
            # Payout
            if state.winner == 0:
                balance += stake
                print(f"You win! +{stake}. Balance: {balance}")
            else:
                balance -= stake
                print(f"CPU wins. -{stake}. Balance: {balance}")

            # Adjust stake or continue
            cmd = input("Enter 's <amount>' to set stake, or Enter to continue: ").strip()
            if cmd.startswith("s "):
                try:
                    stake = max(1, int(cmd.split()[1]))
                except Exception:
                    print("Invalid amount; keeping previous stake.")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
