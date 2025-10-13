from __future__ import annotations
import random
import tkinter as tk
from tkinter import messagebox

# Allow running as a script: python matatu/gui.py
try:
    from .engine import deal_new_game, apply_action, legal_plays  # type: ignore
    from .types import Action, ActionType, Suit, Card, Rank  # type: ignore
    from .cpu import cpu_choose_action  # type: ignore
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from matatu.engine import deal_new_game, apply_action, legal_plays  # type: ignore
    from matatu.types import Action, ActionType, Suit, Card, Rank  # type: ignore
    from matatu.cpu import cpu_choose_action  # type: ignore


class MatatuGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Matatu - 1vCPU")
        self.rng = random.Random()
        self.balance = 1000
        self.stake = 50
        self.state = deal_new_game(self.rng)

        # Frames
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(padx=8, pady=8, fill=tk.X)

        self.center_frame = tk.Frame(root)
        self.center_frame.pack(padx=8, pady=8)

        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.pack(padx=8, pady=8)

        # Top info
        self.info_var = tk.StringVar()
        self.info_label = tk.Label(self.top_frame, textvariable=self.info_var)
        self.info_label.pack(side=tk.LEFT)

        self.balance_var = tk.StringVar()
        self.balance_label = tk.Label(self.top_frame, textvariable=self.balance_var)
        self.balance_label.pack(side=tk.RIGHT)

        # Center controls
        self.top_card_var = tk.StringVar()
        self.top_card_label = tk.Label(self.center_frame, textvariable=self.top_card_var, font=("Arial", 16))
        self.top_card_label.grid(row=0, column=0, padx=6)

        self.draw_btn = tk.Button(self.center_frame, text="Draw", command=self.on_draw)
        self.draw_btn.grid(row=0, column=1, padx=6)

        self.cut_btn = tk.Button(self.center_frame, text="Cut", command=self.on_cut)
        self.cut_btn.grid(row=0, column=2, padx=6)

        self.declare_btn = tk.Button(self.center_frame, text="Declare Suit", command=self.on_declare)
        self.declare_btn.grid(row=0, column=3, padx=6)

        # Suit selection for Ace
        self.suit_var = tk.StringVar(value="C")
        suit_frame = tk.Frame(self.center_frame)
        suit_frame.grid(row=1, column=0, columnspan=3)
        for s, label in [("C", "Clubs"), ("D", "Diamonds"), ("H", "Hearts"), ("S", "Spades")]:
            tk.Radiobutton(suit_frame, text=label, value=s, variable=self.suit_var).pack(side=tk.LEFT)

        # Player hand buttons
        self.hand_frame = tk.Frame(self.bottom_frame)
        self.hand_frame.pack()

        self.refresh_ui()

    def refresh_ui(self) -> None:
        top = self.state.top_discard()
        declared = self.state.declared_suit.value if self.state.declared_suit else "-"
        self.top_card_var.set(f"Top: {top} | Cut: {self.state.cut_suit.value} | Pending: {self.state.pending_draw} | Declared: {declared}")
        self.balance_var.set(f"Balance: {self.balance} | Stake: {self.stake}")

        # Update info
        if self.state.winner is not None:
            winner_text = "You" if self.state.winner == 0 else "CPU"
            self.info_var.set(f"Winner: {winner_text}")
        else:
            turn = "Your" if self.state.current_player == 0 else "CPU"
            self.info_var.set(f"{turn} turn")

        # Rebuild hand buttons
        for w in list(self.hand_frame.children.values()):
            w.destroy()
        legal = set(legal_plays(self.state, 0))
        for i, card in enumerate(self.state.players[0].hand):
            state = tk.NORMAL if card in legal else tk.DISABLED
            btn = tk.Button(self.hand_frame, text=str(card), state=state, command=lambda c=card: self.on_play(c))
            btn.grid(row=0, column=i, padx=4, pady=4)

        # Enable/disable draw/cut/declare
        awaiting_you = getattr(self.state, 'awaiting_declare', None) == 0
        self.declare_btn.config(state=tk.NORMAL if (self.state.winner is None and awaiting_you) else tk.DISABLED)
        self.draw_btn.config(state=tk.NORMAL if (self.state.winner is None and not awaiting_you) else tk.DISABLED)
        self.cut_btn.config(state=tk.NORMAL if (self.state.winner is None and not awaiting_you) else tk.DISABLED)

        # If CPU turn, schedule action
        if self.state.winner is None and self.state.current_player == 1:
            self.root.after(600, self.cpu_step)

    def on_play(self, card: Card) -> None:
        if self.state.winner is not None or self.state.current_player != 0:
            return
        # Enforce cannot finish on 8 or J
        if len(self.state.players[0].hand) == 1 and card.rank in (Rank.EIGHT, Rank.JACK):
            messagebox.showinfo("Rule", "Cannot finish on 8 or J")
            return
        if card.rank is Rank.ACE:
            # Play Ace first; user will press Declare to choose suit
            self.state = apply_action(self.state, Action(ActionType.PLAY, card=card))
        else:
            self.state = apply_action(self.state, Action(ActionType.PLAY, card=card))
        self.post_turn_check()

    def on_declare(self) -> None:
        if self.state.winner is not None or self.state.current_player != 0:
            return
        if getattr(self.state, 'awaiting_declare', None) != 0:
            return
        suit_map = {"C": Suit.CLUBS, "D": Suit.DIAMONDS, "H": Suit.HEARTS, "S": Suit.SPADES}
        declared = suit_map[self.suit_var.get()]
        self.state = apply_action(self.state, Action(ActionType.DECLARE, declared_suit=declared))
        self.post_turn_check()

    def on_draw(self) -> None:
        if self.state.winner is not None or self.state.current_player != 0:
            return
        self.state = apply_action(self.state, Action(ActionType.DRAW))
        self.post_turn_check()

    def on_cut(self) -> None:
        if self.state.winner is not None or self.state.current_player != 0:
            return
        try:
            self.state = apply_action(self.state, Action(ActionType.CUT))
        except Exception as e:
            messagebox.showinfo("Invalid cut", str(e))
            return
        # Show the cutting card on top briefly before ending the hand
        self.refresh_ui()
        self.root.after(800, self.end_hand)

    def cpu_step(self) -> None:
        if self.state.winner is not None or self.state.current_player != 1:
            return
        action = cpu_choose_action(self.state, self.rng)
        # Enforce cannot finish on 8 or J
        if action.type is ActionType.PLAY and len(self.state.players[1].hand) == 1 and action.card and action.card.rank in (Rank.EIGHT, Rank.JACK):
            action = Action(ActionType.DRAW)
        self.state = apply_action(self.state, action)
        self.post_turn_check()

    def post_turn_check(self) -> None:
        # Check winner and payout
        if self.state.winner is not None:
            # Ensure the top cutting card is visible before ending
            self.refresh_ui()
            self.root.after(800, self.end_hand)
        else:
            self.refresh_ui()

    def end_hand(self) -> None:
        if self.state.winner == 0:
            self.balance += self.stake
            messagebox.showinfo("Result", f"You win! +{self.stake}")
        else:
            self.balance -= self.stake
            messagebox.showinfo("Result", f"CPU wins. -{self.stake}")
        # Start next hand
        self.state = deal_new_game(self.rng)
        self.refresh_ui()


def main() -> None:
    root = tk.Tk()
    app = MatatuGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
