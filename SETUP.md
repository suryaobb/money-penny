# Money Penny Fast Start

This package is the fastest practical starting point for a live trading-assistant stack.

## Folder map

- `app/money-penny-control-center.html` — frontend dashboard shell
- `backend/schema.sql` — Supabase tables
- `backend/config.example.json` — config template
- `backend/worker.py` — starter worker loop
- `backend/massive_client.py` — Massive client stub
- `backend/telegram_client.py` — Telegram sender
- `backend/requirements.txt` — Python dependencies

## Fastest path to get it running

1. Create a Supabase project.
2. Run `backend/schema.sql` in the SQL editor.
3. Copy `backend/config.example.json` to `backend/config.json` and fill in Massive, Supabase, and Telegram credentials.
4. In Terminal:
   - `cd backend`
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
   - `python worker.py`
5. Open `app/money-penny-control-center.html` in a browser.

## What this starter does

- Gives you a clean dashboard UI immediately.
- Gives you a worker loop that can write alerts to Supabase.
- Gives you Telegram message plumbing.
- Gives you the correct project shape so your computer bot can continue the build fast.

## What to replace next

- Replace `mock_snapshot()` with real Massive WebSocket handling.
- Replace `evaluate_setup()` with your actual SPY/QQQ rules.
- Connect the dashboard to live Supabase data.
- Add more setup families, logging, and review tooling.
