# Money Penny Trading System — Handoff to Claude Code

**Date:** April 16, 2026  
**Status:** Backend working 100%. Dashboard auth broken.  
**Owner:** Surya (alxndtr)

---

## 🎯 EXECUTIVE SUMMARY

We built a **real-time trading alert system** that:
- ✅ Fetches live SPY/QQQ prices from Massive.com API
- ✅ Detects VWAP+EMA trading setups
- ✅ Sends Telegram alerts in real-time
- ✅ Stores all data in Supabase PostgreSQL
- ❌ Dashboard can't authenticate to Supabase (API key issue)

**What works RIGHT NOW:**
- Python worker runs on Mac mini, polls Massive API every 5 seconds
- Signal engine detects `Price > VWAP` condition
- Alerts fire and get stored in Supabase
- Telegram bot sends notifications to @alxndtr immediately

**What's broken:**
- Dashboard HTML can't read from Supabase (401 auth error)
- The Supabase anon/publishable key in the HTML doesn't work

---

## 📁 PROJECT STRUCTURE

```
/Users/clawd/.openclaw/workspace/money-penny/
├── backend/
│   ├── worker_v2.py .................. MAIN WORKER (running now)
│   ├── signal_engine.py .............. Signal logic (Price > VWAP)
│   ├── massive_client.py ............. REST API client for market data
│   ├── telegram_client.py ............ Sends alerts to Telegram
│   ├── config.json ................... Credentials (API keys, URLs)
│   ├── schema_v2.sql ................. Supabase schema (not used yet)
│   ├── requirements.txt .............. Python dependencies
│   └── .venv/ ....................... Python virtual environment
├── app/
│   └── money-penny-control-center.html Dashboard (Vercel deployed)
├── SETUP_INSTRUCTIONS.md ............ Setup guide
├── QUICK_START.txt .................. Quick reference
├── PHASE2_SETUP.md .................. Phase 2 docs
└── README.md ........................ Project overview
```

---

## 🔧 CURRENT STATE (DETAILED)

### WORKING: Backend Pipeline

**Massive API → Worker → Supabase → Telegram**

1. **Massive.com REST API** (`massive_client.py`)
   - Connected and fetching live SPY/QQQ prices
   - Uses official `massive` Python package
   - Returns: price, vwap, ema20, bid, ask, volume

2. **Signal Engine** (`signal_engine.py`)
   - Simple condition: `Price > VWAP`
   - Fires READY state when condition met + volume confirmed
   - Returns: setup_state (READY/WATCH), score (0.70-0.82), reason text

3. **Worker** (`worker_v2.py`)
   - Runs every 5 seconds (configurable in `config.json`)
   - Only real signals for SPY and QQQ (others monitored)
   - Polls Massive → evaluates signal engine → stores alert → sends Telegram

4. **Supabase Database**
   - Tables: `symbols`, `alerts`, `setups`, `system_state`
   - RLS disabled on alerts/signal_snapshots (public read)
   - All data stored, queryable, verified working

5. **Telegram**
   - Bot token: `8446378241:AAGPg5GNa7gi8YCMktVV99DhScY6DdP-7Bg`
   - Chat ID: `8073987618` (@alxndtr)
   - Alerts being sent successfully in real-time

### BROKEN: Dashboard Frontend

**GitHub repo:** `https://github.com/suryaobb/money-penny`  
**Vercel deployment:** `https://dashboard-222zrw04c-suryaocontact-3589s-projects.vercel.app`

**Problem:** Every fetch to Supabase returns **401 "Invalid API key"**

```
Error: Invalid API key
Hint: Double check your API key.
```

**Why:** The Supabase anon/publishable key in the HTML doesn't authenticate.

**The key in HTML:**
```javascript
const SUPABASE_ANON_KEY = 'sb_publishable_vXYHSU2AeV4ppOHo1vIozw_qtXJAcia';
```

**Attempted fixes:**
1. ❌ Disabled RLS on tables
2. ❌ Updated to correct publishable key
3. ❌ Granted explicit select permissions to anon role

**What we know:**
- Backend can read from Supabase (service role key works)
- The anon key exists in Supabase settings
- But dashboard can't authenticate with it
- This is a Supabase configuration issue, not code

---

## 🚀 WHAT NEEDS TO BE DONE

### Priority 1: Fix Dashboard Auth (30-60 min)
**Goal:** Get dashboard displaying live alerts

**Options:**
1. **Fix the RLS policy** — Make it actually work with anon key
   - Debug why public read policies don't let anon key access
   - Verify RLS is truly disabled
   - Check Supabase role permissions

2. **Use service role key instead** — (Not recommended for public dashboard)
   - Would work but exposes secret key to browser

3. **Build a backend gateway** — (Recommended long-term)
   - Tiny Node.js/Python server on Mac mini
   - Dashboard talks to gateway, gateway talks to Supabase
   - Gateway uses service role key securely
   - Would take 1-2 hours to build

4. **Switch to different auth** — (Overkill for this)
   - JWT tokens from backend
   - User auth flow
   - Probably not worth it

**Recommendation:** Option 3 (gateway) is cleanest. Option 1 if we can figure out RLS quickly.

### Priority 2: Improve Dashboard Display (optional, for aesthetics)
- Show live price updates in real-time
- Better alert feed formatting
- Live watchlist state
- Performance optimization

### Priority 3: Expand Signal Logic (after dashboard works)
- Add more symbols beyond SPY/QQQ
- Implement pullback reclaim logic (currently disabled)
- Add multi-timeframe confirmation
- Adjust score thresholds

---

## 📋 EXACT CREDENTIALS & CONFIG

**File:** `/Users/clawd/.openclaw/workspace/money-penny/backend/config.json`

```json
{
  "massive": {
    "api_key": "gfwW29OhfkSrKrgm6tIYzzrjiC5Vkw9w",
    "symbols": ["SPY", "QQQ", "IWM", "AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA", "GOOGL"]
  },
  "supabase": {
    "url": "https://golqsjxpivryqwyaxwhl.supabase.co",
    "service_role_key": "sb_secret_rPMbkeuyJWZDSONhiqhqSA_bbfGX3QQ",
    "anon_key": "sb_publishable_vXYHSU2AeV4ppOHo1vIozw_qtXJAcia"
  },
  "telegram": {
    "bot_token": "8446378241:AAGPg5GNa7gi8YCMktVV99DhScY6DdP-7Bg",
    "chat_id": "8073987618"
  },
  "system": {
    "poll_interval_seconds": 5
  }
}
```

**Supabase Project:**
- URL: `https://app.supabase.com/project/golqsjxpivryqwyaxwhl`
- Database: PostgreSQL
- Tables: `symbols`, `alerts`, `setups`, `system_state`, `signal_snapshots`

---

## 🎯 WHAT SURYA WANTS

1. **Dashboard showing live alerts** — Real-time display of SPY/QQQ signals
2. **No extra features yet** — Just fix auth, show alerts
3. **No order execution** — Alerts only (investigation mode)
4. **Works with current system** — Don't redesign, just extend
5. **Can hand back to Zara easily** — Well-structured code + handoff notes

---

## 📤 HOW TO HAND IT BACK TO ZARA

After Claude Code finishes:

1. **Create a summary file** called `/Users/clawd/.openclaw/workspace/money-penny/CLAUDE_CHANGES.md` with:
   - What was changed
   - What was fixed
   - How to deploy/run it
   - Any new files created

2. **Test it works:**
   - Dashboard loads without 401 errors
   - Shows live alert feed
   - Telegram still works
   - SPY/QQQ prices display correctly

3. **Package for Zara:**
   ```bash
   cd /Users/clawd/.openclaw/workspace/money-penny
   git add -A
   git commit -m "Dashboard fix: [describe what Claude fixed]"
   git push
   ```

4. **Send Zara a message:**
   - "Claude Code completed dashboard fix"
   - Link to CLAUDE_CHANGES.md
   - Link to the GitHub commit
   - Confirmation that system is 100% working

---

## 🔌 HOW TO RUN THE SYSTEM

**Start the backend worker:**
```bash
cd /Users/clawd/.openclaw/workspace/money-penny/backend
source .venv/bin/activate
python worker_v2.py
```

**View live dashboard:**
```
https://dashboard-222zrw04c-suryaocontact-3589s-projects.vercel.app
```

**Check alerts in Supabase:**
```
https://app.supabase.com/project/golqsjxpivryqwyaxwhl/editor/20
```

---

## 🐛 KEY ISSUES CLAUDE NEEDS TO KNOW

1. **Supabase RLS is a mess** — We tried disabling it but anon key still doesn't work
2. **The HTML is hosted on Vercel** — Changes need to be pushed to GitHub for auto-deploy
3. **Worker is running locally on Mac mini** — Don't touch that, it works
4. **Mock data in HTML is hardcoded** — Dashboard needs to fetch from Supabase instead
5. **JavaScript fetch calls are failing 401** — Every single one, authentication broken

---

## ✅ SUCCESS CRITERIA

Dashboard is done when:
- [ ] Loads without console errors
- [ ] Shows live SPY/QQQ prices from Supabase
- [ ] Displays latest alerts from Supabase
- [ ] Updates in real-time (5-second poll)
- [ ] No hardcoded mock data
- [ ] Supabase anon key authentication works

---

## 📞 CONTACT INFO

- **Surya (User):** @alxndtr, Telegram: 8073987618
- **Zara (Main Assistant):** Will integrate when handed back
- **GitHub repo:** `https://github.com/suryaobb/money-penny`
- **Live API:** Massive.com
- **Database:** Supabase PostgreSQL

---

## 📝 ADDITIONAL NOTES

- System has been running for ~2 hours
- All credentials are stored in `config.json` (not committed to GitHub)
- Worker logs to console (check with `ps aux | grep worker_v2`)
- Telegram notifications are working perfectly
- Only the dashboard display is broken

**This is a working, production-ready backend. Just need the frontend to display it.**

---

**Prepared by:** Zara  
**For:** Claude Code (Claude 3.5 Sonnet)  
**Time estimate:** 1-2 hours to fix dashboard  
**Difficulty:** Medium (Supabase auth debugging)
