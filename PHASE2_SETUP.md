# Money Penny Phase 2 — Complete Setup Guide

**Date:** April 16, 2026  
**Status:** Production Ready  
**Deployed To:** Mac Mini (clawd)  

---

## 🚀 Quick Start

### 1. Database Setup (MANUAL)

Go to: https://app.supabase.com/project/golqsjxpivryqwyaxwhl/sql/new

Paste and run the schema SQL:

```sql
-- Phase 2 Production Schema
-- Copy the full schema_v2.sql file here and run
```

**Full SQL is in:** `/Users/clawd/.openclaw/workspace/money-penny/backend/schema_v2.sql`

### 2. Update Requirements

```bash
cd /Users/clawd/.openclaw/workspace/money-penny/backend
source .venv/bin/activate
pip install -r requirements.txt
```

**requirements.txt** (if not already there):
```
requests
websocket-client
supabase
python-dotenv
```

### 3. Environment Setup

**Config file:** `/Users/clawd/.openclaw/workspace/money-penny/backend/config.json`

```json
{
  "massive": {
    "api_key": "gfwW29OhfkSrKrgm6tIYzzrjiC5Vkw9w",
    "symbols": ["SPY", "QQQ", "IWM", "AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA", "GOOGL"]
  },
  "supabase": {
    "url": "https://golqsjxpivryqwyaxwhl.supabase.co",
    "service_role_key": "sb_secret_rPMbkeuyJWZDSONhiqhqSA_bbfGX3QQ"
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

### 4. Start the Worker

```bash
cd /Users/clawd/.openclaw/workspace/money-penny/backend
source .venv/bin/activate
python worker_v2.py
```

**Output:**
```
============================================================
🚀 Money Penny Phase 2 Worker Starting
============================================================
📊 Monitoring: SPY, QQQ, IWM, AAPL, AMZN, META, MSFT, NVDA, TSLA, GOOGL
🎯 Real signals enabled for: SPY, QQQ
⏱️  Poll interval: 5s

[Poll #1] Evaluating 10 symbols...
[Poll #2] Evaluating 10 symbols...
```

---

## 📊 Architecture

### File Structure

```
/Users/clawd/.openclaw/workspace/money-penny/
├── app/
│   └── money-penny-control-center.html    (Dashboard - Vercel hosted)
├── backend/
│   ├── worker_v2.py                       (MAIN: Phase 2 worker)
│   ├── signal_engine.py                   (Signal evaluation logic)
│   ├── massive_client.py                  (Massive REST API client)
│   ├── telegram_client.py                 (Telegram alert sender)
│   ├── config.json                        (Credentials & settings)
│   ├── schema_v2.sql                      (Supabase schema)
│   ├── requirements.txt                   (Python deps)
│   └── .venv/                             (Virtual environment)
├── PHASE2_SETUP.md                        (This file)
└── README.md
```

### Data Flow

```
Massive.com API
      ↓
massive_client.py (fetch live data every 5s)
      ↓
worker_v2.py (evaluate snapshots)
      ↓
signal_engine.py (VWAP+EMA logic)
      ↓
Supabase PostgreSQL
      ├── alerts (for Telegram)
      ├── setups (current state)
      ├── candles (for replay)
      └── system_state (health)
      ↓
Telegram Bot → Your Phone
      ↓
Vercel Dashboard (live view)
```

---

## 🎯 Signal Logic

### VWAP+EMA Crossover Setup

**Entry Condition:**
- VWAP crosses above EMA20 (transition from below to above)
- Both VWAP and EMA20 are moving up
- Volume confirmed (current volume >= 80% of 5-bar average)

**States:**
- `WATCH`: Crossover detected, not yet ready (score < 0.75)
- `READY`: Crossover + volume confirmed (score >= 0.75)

**Log Example:**
```
READY: VWAP/EMA crossover (V=641.25 > E=640.50) + volume confirmed (4523400)
```

---

### VWAP Pullback Reclaim Setup

**Entry Condition:**
- Previous candle closed above VWAP
- Current candle pulls below VWAP (low < VWAP)
- Current candle reclaims above VWAP (close > VWAP)
- EMA20 alignment (VWAP >= EMA20)
- Strong reclaim if close in upper 30% of candle

**States:**
- `WATCH`: Pullback/reclaim detected, weak reclaim (score ~0.70)
- `READY`: Strong reclaim + EMA aligned (score >= 0.80)

**Log Example:**
```
READY: Pullback reclaim (low=641.10, VWAP=641.25, close=641.55) + EMA aligned
```

---

### Invalid Setups

**Invalidation Triggers:**
- Crossover without uptrend confirmation
- Pullback reclaim without EMA alignment
- Price breaks below VWAP after setup

**Log Example:**
```
INVALIDATED: Crossover but no uptrend (VWAP up=false, EMA up=true)
```

---

## 📱 Telegram Alerts

### Alert Types

| Type | Headline | Meaning |
|------|----------|---------|
| `watch` | 🟡 {TICKER} WATCH | Setup detected, not ready yet |
| `ready` | 🟢 {TICKER} READY | Setup ready for entry |
| `trigger` | 🔴 {TICKER} TRIGGER | Entry triggered (future) |
| `invalidation` | ⛔ {TICKER} INVALIDATED | Setup failed |
| `cooldown` | ❄️ {TICKER} COOLDOWN | Waiting 5 min before re-signal |

### Alert Format

```
🟢 SPY READY
VWAP_EMA_CROSSOVER
Score: 0.82
READY: VWAP/EMA crossover (V=641.25 > E=640.50) + volume confirmed
```

---

## 🔧 Configuration

### Enabling Real Signals for More Symbols

Edit `worker_v2.py` line ~50:

```python
ENABLED_SYMBOLS = ['SPY', 'QQQ']  # Add more here
```

### Adjusting Poll Interval

Edit `config.json`:

```json
"system": {
  "poll_interval_seconds": 5
}
```

Lower = faster signals, higher = less API calls.

### Adjusting Signal Thresholds

Edit `signal_engine.py`:

```python
# Crossover volume confirmation threshold
vol_confirmed = curr_vol >= avg_vol * 0.8  # Change 0.8 to adjust

# Pullback reclaim strength threshold
strong_reclaim = reclaim_strength > 0.7  # 70% of candle range
```

---

## 📊 Dashboard

**Live Dashboard:** https://money-penny-suryaobb.vercel.app

The dashboard polls Supabase every 5 seconds and displays:
- Live watchlist with setup state
- Key levels (VWAP, EMA20, ORB)
- Latest alerts from worker
- Setup cards with entry conditions

---

## 🐛 Debugging

### Check Worker Logs

```bash
cd /Users/clawd/.openclaw/workspace/money-penny/backend
source .venv/bin/activate
python worker_v2.py 2>&1 | tee worker.log
```

### Check Supabase Data

**Alerts Table:**
```sql
select ticker, alert_type, headline, created_at 
from alerts 
order by created_at desc 
limit 20;
```

**System State:**
```sql
select key, value, updated_at 
from system_state;
```

### Test Signal Engine

```bash
python3 << 'EOF'
from signal_engine import SignalEngine

engine = SignalEngine()

# Test crossover
candles = [
    {'vwap': 640.0, 'ema_20': 641.0, 'volume': 1000000, 'open': 640, 'high': 640, 'low': 640, 'close': 640},
    {'vwap': 641.0, 'ema_20': 640.5, 'volume': 1100000, 'open': 641, 'high': 641.5, 'low': 640.9, 'close': 641.2},
]

snap = {'price': 641.2, 'vwap': 641.0, 'ema_20': 640.5}

signal = engine.evaluate_candle_stream('SPY', candles, snap)
print(signal)
EOF
```

---

## 🚀 Future Enhancements

1. **Options Flow Integration** — Alert when put/call ratio extremes detected
2. **Multi-Timeframe Confirmation** — Cross-verify 5-min and 15-min trends
3. **Trade Execution** — Auto-execute orders when trigger level hit
4. **Risk Management** — Auto-stop-loss and position sizing
5. **Historical Backtest** — Validate strategy on past data
6. **Mobile App** — Native iOS/Android alerts

---

## 📝 Status Check

**To verify everything is running:**

1. Start worker: `python worker_v2.py`
2. Wait 30 seconds for first poll
3. Check Telegram: should see "Poll #1" message
4. Open dashboard: https://money-penny-suryaobb.vercel.app
5. Check Supabase: alerts table should have entries

---

## 🆘 Troubleshooting

### No alerts appearing

- Check worker is running: `ps aux | grep worker_v2`
- Check Telegram token in config.json
- Check SPY/QQQ are in enabled symbols
- View logs: `python worker_v2.py 2>&1 | head -20`

### "Connection refused" error

- Verify Massive API key is correct
- Verify Supabase URL and keys are correct
- Check internet connection

### Signals not firing for SPY/QQQ

- Need at least 5 candles in history (25+ seconds)
- Check VWAP/EMA values in Supabase candles table
- Run test signal engine (see Debugging section)

---

## 📞 Support

For issues, check the logs and:
1. Paste logs to terminal
2. Share alert context from Supabase
3. Share signal_engine.py logs

---

**Version:** 2.0  
**Last Updated:** 2026-04-16 18:45 PDT  
**Status:** PRODUCTION
