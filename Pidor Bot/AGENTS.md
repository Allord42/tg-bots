# AGENTS.md

Context file for a new agent in **Pidor Bot**. Read this before changing code. User-facing bot text is Russian and meme-toned. Code, comments, commits, and docs are English.

## What this project is

Telegram group-chat game. Players `/join`, pick a display name, then run a random “pidor of the day” draw. Port of the old VK bot.

Two processes, two BotFather tokens, one SQLite file:

| Kind | Entry | Token env | Choose / board | Score column |
| --- | --- | --- | --- | --- |
| classic | `main_classic.py` | `PIDOR_BOT_TOKEN` | `/choose_pidor_cl`, `/leaderboard_cl` | `pidor_score` |
| extended | `main_extended.py` | `PIDOR_BOT_EXTENDED_TOKEN` | `/choose_pidor_ex`, `/leaderboard_ex` | `extended_score` |

Classic stays the VK-style daily lottery. Extended is where PvP, casino, betting, extra events go. **Do not dump new mini-games into classic.**

Both bots may run in the same chat. Scores and choose-cooldowns are isolated by `bot_kind`. Shared player list (name, birthday, join time) is one row per `(chat_id, user_id)`.

## Repo layout

Git root is the parent folder `Telegram bots`. This bot lives in `Pidor Bot/`.

```
Pidor Bot/
  main_classic.py      # asyncio.run classic
  main_extended.py     # asyncio.run extended
  config.py            # paths, tokens, ADMIN_IDS, Russian copy, command names
  .env                 # secrets, gitignored
  db/pidor.db          # runtime SQLite, gitignored
  db/bot.log           # runtime log, gitignored
  classic/handlers.py  # thin: make_game_router("classic")
  extended/handlers.py # thin: make_game_router("extended")
  shared/
    runner.py          # logging, polling, wiring
    handlers.py        # /start /join /rename /commands /username_account /set_birthday
    game.py            # choose + leaderboard factory
    database.py        # aiosqlite + migrations
    memory.py          # in-memory cache loaded from DB
    middleware.py      # reload memory from DB on every message
    states.py          # FSM groups
    text_utils.py      # parse/format/validate/log helpers
```

## How it runs

```bash
cd "Pidor Bot"
python main_classic.py
python main_extended.py
```

`shared/runner.py` builds Bot + Dispatcher, injects `bot_kind` into dispatcher data, mounts `shared_router` then the game router, `init_db()`, `load_memory_from_db()`, sets the Telegram command menu, polls.

Tokens missing → log + `SystemExit(1)`.

## Architecture rules

1. **One shared SQLite** at `config.DB_PATH` (`db/pidor.db`). WAL mode. Schema version in `schema_meta`; add a new key to `MIGRATIONS` in `shared/database.py` and bump `SCHEMA_VERSION`. Never edit an already-applied migration.
2. **Memory is not the source of truth.** `ReloadMemoryMiddleware` reloads `players` / `last_choose_at` / `last_chosen_pidor` from SQLite on every message so classic and extended stay in sync. If you write a new field, persist it in `database.py` and load it in `load_all_participants` / `load_chat_state`.
3. **New game features go in `extended/`**, not in `shared/game.py`, unless the mechanic truly belongs to both bots (join, rename, birthday). Classic game router must stay choose + leaderboard.
4. **Command names** come from `config.choose_pidor_command` / `leaderboard_command` (`cl` / `ex` suffix). Do not hardcode `/choose_pidor` without a suffix.
5. **Admins** are Telegram `user_id`s in `config.ADMIN_IDS`. Only they can `/rename`. Do not invent a DB admin flag as the check; `is_admin` in `text_utils` uses that list. The `is_admin` column on participants is stored at join time from the same list.
6. **Sentinels, not Optional.** Missing name query → `""`. Missing user id → `0`. Missing birthday → `0`. Do not use `Optional[...]`, `X | None`, or `from __future__ import annotations`.
7. **DRY.** Shared copy lives in `config.py`. Shared parse/format lives in `text_utils.py`. If you are about to duplicate a handler, stop and put it in `shared/`.
8. **No docstrings.** Types on every function, including `__init__`. Multi-line signatures:

```python
def function_name(
    param1: str,
    param2: int,
) -> float:
```

9. **Naming:** `snake_case` functions/vars/modules, `CamelCase` classes, `CAPSLOCK` constants and config keys.
10. **Ask before coding** if the request is ambiguous. Do not invent product behavior for casino/PvP until the user confirms the rules.

## Current game behavior (implemented)

- Join: FSM asks display name, unique per chat (case-insensitive), max 32 chars, cannot start with `/`.
- Choose: random member of that chat, +1 to that bot’s score, +1 choose-start for the caller if they already joined, 10 hour cooldown per `(chat_id, bot_kind)`, then the staged Russian phrases with `SLEEP_TIME` between them.
- Leaderboard: sort that bot’s score descending.
- Birthday stored as packed int `YYYYMMDD`.
- `/username_account` with no arg = self; with arg = name, `@username`, or numeric user id.

## Planned (not implemented)

Keep these on extended unless the user says otherwise:

- Lucky day (everyone loses N score)
- Birthday bonus
- Bot as bookmaker
- PvP bets
- “Bored” behavior after long downtime
- Fairer stats via expected value
- Game of 21
- Fun facts, weather
- Optional LLM in chat

## Do not

- Commit `.env`, `db/pidor.db`, logs, `__pycache__`.
- Rewrite Russian player-facing strings to English or “clean” the meme tone unless asked.
- Share classic and extended score columns.
- Put exploit/PoC work, tokens, or real user dumps in the repo.
- Add comments that only repeat the code. No docstrings.
- Change `ADMIN_IDS` or tokens unless the user asks.

## Coding loop

English only in agent replies. If instructions conflict or this file is wrong, propose an update to `AGENTS.md` and wait for confirmation before editing it.
