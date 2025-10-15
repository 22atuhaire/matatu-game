# AI Agent Instructions for Matatu Game

## Project Overview
This is a Python implementation of Matatu (Casino variant), a card game. The project is structured as a desktop application with both CLI and GUI interfaces.

## Core Architecture

### Key Components
- `engine.py`: Core game logic and state management
- `types.py`: Data structures and enums for cards, actions, etc.
- `gui.py`: Tkinter-based UI implementation
- `cpu.py`: CPU player strategy implementation
- `cli.py`: Command-line interface

### Game State Management
- Game state is immutable - all state changes return new `GameState` objects
- State includes: players, cards, current player, pending actions, etc.
- Example in `engine.py`:
```python
def apply_action(state: GameState, action: Action) -> GameState:
    # Returns new state, doesn't modify existing
```

### Key Game Rules
1. Special cards:
   - `TWO`: Forces next player to draw 2 cards
   - `EIGHT`: Grants extra turn (cannot be final card)
   - `JACK`: Grants extra turn (cannot be final card) 
   - `ACE`: Wild card requiring suit declaration
   - `SEVEN` of cut suit: Enables cutting if total points ≤ 25

2. Winning conditions:
   - Empty hand (except can't finish with 8 or J)
   - Cutting with 7 of cut suit when points ≤ 25

## Development Workflows

### Running the Game
- GUI: `python matatu/gui.py`
- CLI: `python -m matatu.cli` 

### Project Structure Conventions
- All game logic in pure functions
- State changes only through `apply_action()`
- GUI/CLI layers should not contain game rules

## Common Tasks

### Adding New Card Rules
1. Add rank/type in `types.py`
2. Add points value in `card_points()`
3. Implement effects in `apply_action()`
4. Update CPU strategy in `cpu.py`

### Modifying Game Rules
- Core rules in `engine.py:apply_action()`
- Legal moves logic in `engine.py:legal_plays()`
- UI enforcement in `gui.py:on_play()` and `cpu_step()`

## Known Patterns
- Two-step actions (e.g., Ace play + declare suit)
- Extra turn management for 8/J
- Points calculation for cut validation
- CPU strategy preferences for special cards

## Testing
Use `assert` statements to validate state transitions and game rules