# Testing

Run: `.venv/bin/python -m pytest tests` (needs the repo's dependencies, e.g. `discord`).

Discord is never connected. `tests/fakes.py` stubs it; the game engine, rules and save
files run for real in a temp folder. Tests never touch `config.json` or real games.

## Which fixture to use (`tests/conftest.py`)

| Fixture | Use it for |
|---|---|
| `make_game(dict)` | One rule in isolation: hand-write the gamestate, call the helper directly. |
| `start_game(n)` + `press` | A real set-up game, driven by clicking buttons through `ButtonListener`. For flows across handlers or rounds. |
| `games_dir` | Tests that create games themselves (`GameInit`). |
| `no_random([...])` | Pin dice rolls. `start_game` already seeds the other randomness. |
| `run(coro)` | Run an async handler and flush its background tasks. |

## Click-through example

```python
def test_pass(start_game, press):
    game, channel = start_game()                      # 2 players, blue (id 1) on turn
    press(channel, 1, "FCIDblue_passForRound")        # same path as a real click
    assert reload(game).gamestate["players"]["1"]["passed"]
    assert "Build" in " ".join(filter(None, buttons(channel).values()))  # what the bot offered next
```

Always `reload(game)` after a press: the press works on its own copy of the game.

## Adding tests

- One file per area (`test_<module>_<topic>.py`). Plain functions; a class per rule group is fine when a file covers several (as in the alliance tests).
- Shared fakes and helpers go in `fakes.py` (`players`, `board_tile`, `POS`, `player_helper`, `offered_ids`, ...),
  fixtures in `conftest.py`. Keep a helper local until a second file needs it.
- A fake missing a Discord method (a `KeyError` or `AttributeError` on `interaction.*`)
  is a one-line fix in `fakes.py`, not a reason to skip the test.
- A fake only records calls; it can't catch real Discord problems (permissions,
  rate limits, message limits, the 3-second timeout).
