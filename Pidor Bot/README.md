# Pidor Bot

Telegram chat bots for group chats. Players join the game, pick a display name, and run a “pidor of the day” draw. Scores live per chat.

This is a Telegram port of the old VK-style pidor bot: same joke, same daily lottery, plus an extended bot that will grow into extra games.

## Two versions

Both bots can sit in the same chat. They share one SQLite database, but **scores and cooldowns are separate**.

### Classic

The original loop, close to the VK bot:

- `/join` and pick a name
- `/choose_pidor_cl` — random player of the day (10 hour cooldown per chat)
- `/leaderboard_cl` — classic score table

### Extended

Same core loop today (`/choose_pidor_ex`, `/leaderboard_ex`), with its own score column.

This is the bot that will grow: player vs player, casino-style games, betting against the bot, extra events. Classic stays simple on purpose.

## Setup

Python 3.14+. From the workspace root (`Telegram bots`), install with `uv`:

```bash
uv sync
```

Create `Pidor Bot/.env` with BotFather tokens:

```
PIDOR_BOT_TOKEN=...
PIDOR_BOT_EXTENDED_TOKEN=...
```

Each version is a separate Telegram bot (two tokens, two `@usernames`). Add both to the chat if you want classic and extended side by side.

## Run

From `Pidor Bot/`:

```bash
# classic bot (VK-style daily draw)
python main_classic.py

# extended bot (separate score; extra games go here)
python main_extended.py

# both bots in one process (same as Heroku)
python main_both.py
```

Run classic and extended in two terminals if you want them as separate processes. Local SQLite is at `db/pidor.db`; logs go to `db/bot.log`.

## Heroku

One app, one `web` dyno, both bots in `main_both.py`. Procfile lives in the git root (`Telegram bots/`). Heroku reads `pyproject.toml` + `uv.lock` (no `requirements.txt`).

SQLite on Heroku is wiped on every dyno restart. Attach Postgres and Heroku will set `DATABASE_URL`. Locally, leave `DATABASE_URL` unset to keep using `db/pidor.db`.

Config vars: `PIDOR_BOT_TOKEN`, `PIDOR_BOT_EXTENDED_TOKEN`. `DATABASE_URL` comes from the Postgres addon.

## Commands

Shared by both bots:

| Command | What it does |
| --- | --- |
| `/start` | Intro + which bot this is |
| `/commands` | Command list |
| `/join` | Join this chat’s game (bot asks for a display name) |
| `/rename` | Admin only: rename a player |
| `/username_account` | Player card (optional name / `@username` / user id) |
| `/set_birthday` | Save birthday as `DD.MM.YYYY` |

Classic only: `/choose_pidor_cl`, `/leaderboard_cl`  
Extended only: `/choose_pidor_ex`, `/leaderboard_ex`

## Data

- `.env` — tokens, never commit
- `db/pidor.db` — local SQLite (participants and per-bot chat state), never commit
- Heroku Postgres — same data when `DATABASE_URL` is set
- `config.py` — `ADMIN_IDS`, cooldowns, Russian player-facing copy

## Roadmap (extended)

Ideas already in play, not built yet:

- Lucky day (everyone loses N score)
- Birthday bonus
- Bot as bookmaker
- PvP bets between players
- Bot “gets bored” if it was offline too long
- Fairer stats via expected value
- 21 / blackjack
- Fun facts, weather
- Optional LLM for chat
