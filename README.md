# Money Penny — Trading Alert System

## Status: SETUP IN PROGRESS

### What's Done ✅
- [x] Project directory created at `/Users/clawd/.openclaw/workspace/money-penny`
- [x] Python venv created and dependencies installed
- [x] Config file set up with API keys:
  - Massive API key configured
  - Supabase URL configured
  - Telegram bot credentials configured
- [x] Backend worker structure ready (`worker.py`, `massive_client.py`, `telegram_client.py`)
- [x] Frontend dashboard template ready (`app/money-penny-control-center.html`)

### What's Blocked ❌
- **Database tables** — Supabase tables not yet created (network issue during setup)
  - Tables needed: `symbols`, `session_levels`, `alerts`, `signal_snapshots`
  - Must be created manually in Supabase SQL editor
  - See `backend/schema.sql` for the DDL

###  Next Steps

1. **Create Supabase tables** (manual, one-time):
   - Go to https://app.supabase.com/project/golqsjxpivryqwyaxwhl/sql
   - Run each statement from `backend/schema.sql` separately in SQL editor
   - Verify tables appear in Table Editor

2. **Start the worker** (once tables exist):
   ```bash
   cd /Users/clawd/.openclaw/workspace/money-penny/backend
   source .venv/bin/activate
   python worker.py
   ```

3. **Test the dashboard**:
   - Open `app/money-penny-control-center.html` in browser
   - Should render (currently displays static template)

4. **Implement real data feeds**:
   - Replace `mock_snapshot()` in `massive_client.py` with live Massive WebSocket
   - Connect dashboard to live Supabase data via polling/subscriptions

## Architecture

- **Backend**: Python worker pulling market data, evaluating setups, storing alerts
- **Database**: Supabase PostgreSQL (symbols, session levels, alerts, signal snapshots)
- **Frontend**: HTML dashboard (receives alerts via Telegram, can be enhanced)
- **Alerts**: Telegram bot sends trading setup notifications

## Config File Location
`/Users/clawd/.openclaw/workspace/money-penny/backend/config.json`

(API keys and credentials stored securely)

## Trading Parameters
- **Universe**: SPY, QQQ, IWM, AAPL, AMZN, META, MSFT, NVDA, TSLA, GOOGL
- **Strategy**: VWAP + EMA momentum setups
- **Alert Types**: `ready`, `invalidated`, `watch`
- **Scoring**: 0-100 (>70 = GO signal)

---

**Created**: 2026-04-16  
**Setup by**: Zara (OpenClaw Assistant)
