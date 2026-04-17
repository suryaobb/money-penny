#!/usr/bin/env python3
"""
Money Penny Phase 2 Worker
Real-time VWAP+EMA signal detection with state management
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict
from supabase import create_client
from massive_client import MassiveClient
from telegram_client import TelegramClient
from signal_engine import SignalEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

CONFIG_PATH = Path('config.json')
config = json.loads(CONFIG_PATH.read_text())

supabase = create_client(config['supabase']['url'], config['supabase']['service_role_key'])
telegram = TelegramClient(config['telegram']['bot_token'], config['telegram']['chat_id'])
massive = MassiveClient(CONFIG_PATH)
signal_engine = SignalEngine(lookback_candles=20)

# In-memory candle history (per symbol)
candle_history = defaultdict(list)
active_setups = defaultdict(dict)  # {ticker: {setup_id: setup_state}}
cooldown_ends = defaultdict(dict)  # {ticker: {setup_id: datetime}}

# Configuration
ENABLED_SYMBOLS = ['SPY', 'QQQ']  # Only real signals for these
ALL_SYMBOLS = config['massive']['symbols']
POLL_INTERVAL = config['system']['poll_interval_seconds']
MAX_CANDLES_HISTORY = 60  # Keep 60 minutes of 1-min candles


def init_system():
    """Initialize system state in Supabase"""
    try:
        supabase.table('system_state').upsert({
            'key': 'last_polling_time',
            'value': {'timestamp': datetime.now().isoformat()}
        }).execute()
        
        supabase.table('system_state').upsert({
            'key': 'worker_status',
            'value': {'status': 'RUNNING', 'started_at': datetime.now().isoformat()}
        }).execute()
        
        logger.info("System state initialized")
    except Exception as e:
        logger.error(f"Failed to init system state: {e}")


def fetch_live_data():
    """Fetch live data from Massive"""
    try:
        snapshots = massive.get_snapshot()
        if snapshots:
            logger.debug(f"Fetched {len(snapshots)} live quotes")
            return snapshots
    except Exception as e:
        logger.error(f"Error fetching live data: {e}")
    
    return {}


def process_snapshot_to_candle(symbol: str, snap: Dict):
    """
    Convert snapshot to candle format.
    Each snapshot becomes a candle point.
    """
    price = snap.get('price', 0)
    vwap = snap.get('vwap', 0)
    ema20 = snap.get('ema20', 0)
    volume = snap.get('volume', 0)
    
    candle = {
        'time': datetime.now(),
        'vwap': vwap,
        'ema20': ema20,
        'volume': volume,
        'close': price
    }
    
    candle_history[symbol].append(candle)
    
    if len(candle_history[symbol]) > MAX_CANDLES_HISTORY:
        candle_history[symbol] = candle_history[symbol][-MAX_CANDLES_HISTORY:]
    
    return candle


def check_cooldown(symbol: str, setup_id: str) -> bool:
    """Check if setup is still in cooldown"""
    if symbol in cooldown_ends and setup_id in cooldown_ends[symbol]:
        end_time = cooldown_ends[symbol][setup_id]
        if datetime.now() < end_time:
            return True
        else:
            del cooldown_ends[symbol][setup_id]
    
    return False


def send_alert(signal: Dict, alert_type: str, priority: str):
    """Send alert to Supabase and Telegram"""
    ticker = signal['ticker']
    setup_state = signal['setup_state']
    reason = signal.get('reason', 'No reason provided')
    score = signal.get('setup_score', 0)
    
    # Format headline based on state
    if setup_state == 'READY':
        headline = f"🟢 {ticker} READY"
    elif setup_state == 'WATCH':
        headline = f"🟡 {ticker} WATCH"
    elif setup_state == 'TRIGGER':
        headline = f"🔴 {ticker} TRIGGER"
    elif setup_state == 'INVALIDATED':
        headline = f"⛔ {ticker} INVALIDATED"
    elif setup_state == 'COOLDOWN':
        headline = f"❄️ {ticker} COOLDOWN"
    else:
        headline = f"{ticker} {setup_state}"
    
    message = f"{signal['setup_family']}\nScore: {score:.2f}\n{reason}"
    
    try:
        # Store in Supabase
        supabase.table('alerts').insert({
            'ticker': ticker,
            'alert_type': alert_type,
            'priority': priority,
            'headline': headline,
            'message': message,
            'context': signal
        }).execute()
        
        # Send Telegram
        telegram.send(f"{headline}\n{message}")
        
        logger.info(f"Alert sent: {headline}")
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")


def store_price_snapshot(symbol: str, snap: Dict):
    """Write latest price for every symbol so dashboard can display live data."""
    try:
        supabase.table('signal_snapshots').insert({
            'ticker': symbol,
            'setup_family': 'PRICE',
            'setup_state': 'LIVE',
            'score': 0,
            'payload': {
                'price':  snap.get('price'),
                'vwap':   snap.get('vwap'),
                'ema20':  snap.get('ema20'),
                'volume': snap.get('volume'),
                'bid':    snap.get('bid'),
                'ask':    snap.get('ask'),
            }
        }).execute()
    except Exception as e:
        logger.error(f"Failed to store price snapshot for {symbol}: {e}")


def evaluate_signals(symbol: str, snap: Dict):
    """
    Evaluate VWAP+EMA signals for a symbol.
    """
    
    # Skip if not in enabled list
    if symbol not in ENABLED_SYMBOLS:
        return
    
    # Check cooldown
    if symbol in cooldown_ends:
        for setup_id in list(cooldown_ends[symbol].keys()):
            if check_cooldown(symbol, setup_id):
                logger.debug(f"{symbol}: Still in cooldown")
                return  # Still in cooldown
    
    # Process snapshot to candle
    process_snapshot_to_candle(symbol, snap)
    
    # Need at least 2 candles to evaluate
    if len(candle_history[symbol]) < 2:
        logger.info(f"{symbol}: Candles: {len(candle_history[symbol])}/2 (ready after next poll)")
        return
    
    # Run signal engine
    logger.info(f"{symbol}: Running signal engine with {len(candle_history[symbol])} candles...")
    signal = signal_engine.evaluate_candle_stream(symbol, candle_history[symbol], snap)
    
    if not signal:
        logger.info(f"{symbol}: No signal from engine")
        return
    
    # Handle signal
    setup_state = signal.get('setup_state')
    
    if setup_state == 'WATCH':
        logger.info(f"{symbol}: WATCH signal detected")
        send_alert(signal, 'watch', 'info')
        
        # Store setup
        setup_id = f"{symbol}_{datetime.now().timestamp()}"
        active_setups[symbol][setup_id] = signal
    
    elif setup_state == 'READY':
        logger.info(f"{symbol}: READY signal detected")
        send_alert(signal, 'ready', 'ready')
        
        # Store setup
        setup_id = f"{symbol}_{datetime.now().timestamp()}"
        active_setups[symbol][setup_id] = signal
        
        # Set 5-minute cooldown
        cooldown_ends[symbol][setup_id] = datetime.now() + timedelta(minutes=5)
    
    elif setup_state == 'INVALIDATED':
        logger.warning(f"{symbol}: Setup INVALIDATED")
        send_alert(signal, 'invalidation', 'info')
        
        # Clear active setup
        setup_id = list(active_setups.get(symbol, {}).keys())[0] if active_setups[symbol] else None
        if setup_id:
            del active_setups[symbol][setup_id]


def main():
    logger.info("=" * 60)
    logger.info("🚀 Money Penny Phase 2 Worker Starting")
    logger.info("=" * 60)
    logger.info(f"📊 Monitoring: {', '.join(ALL_SYMBOLS)}")
    logger.info(f"🎯 Real signals enabled for: {', '.join(ENABLED_SYMBOLS)}")
    logger.info(f"⏱️  Poll interval: {POLL_INTERVAL}s")
    logger.info("")
    
    # Initialize
    massive.connect()
    init_system()
    
    poll_count = 0
    
    try:
        while True:
            poll_count += 1
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Fetch live data
            snapshots = fetch_live_data()
            
            if snapshots:
                logger.info(f"[Poll #{poll_count}] Evaluating {len(snapshots)} symbols...")
                
                for symbol, snap in snapshots.items():
                    try:
                        store_price_snapshot(symbol, snap)
                        if symbol in ENABLED_SYMBOLS:
                            logger.info(f"Evaluating {symbol}...")
                        evaluate_signals(symbol, snap)
                    except Exception as e:
                        logger.error(f"Error evaluating {symbol}: {e}")
            else:
                logger.warning(f"[Poll #{poll_count}] No data received")
            
            # Update system state
            try:
                supabase.table('system_state').upsert({
                    'key': 'last_polling_time',
                    'value': {'timestamp': datetime.now().isoformat(), 'poll_count': poll_count}
                }).execute()
            except:
                pass
            
            time.sleep(POLL_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("\n🛑 Worker stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()
