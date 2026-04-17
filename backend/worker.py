import json
import time
from pathlib import Path
from supabase import create_client
from massive_client import MassiveClient
from telegram_client import TelegramClient

CONFIG_PATH = Path('config.json')
config = json.loads(CONFIG_PATH.read_text())

supabase = create_client(config['supabase']['url'], config['supabase']['service_role_key'])
telegram = TelegramClient(config['telegram']['bot_token'], config['telegram']['chat_id'])
massive = MassiveClient(CONFIG_PATH)

def evaluate_setup(symbol, snap):
    if snap['price'] > snap['vwap'] and snap['vwap'] >= snap['ema20']:
        return {
            'ticker': symbol,
            'alert_type': 'vwap_ema_ready',
            'priority': 'ready',
            'headline': f'{symbol} ready',
            'message': f"{symbol}: price above VWAP and EMA stack aligned.",
            'context': snap,
            'setup_family': 'VWAP+EMA',
            'setup_state': 'ready',
            'score': 0.82
        }
    return None

def store_signal(signal):
    supabase.table('alerts').insert({
        'ticker': signal['ticker'],
        'alert_type': signal['alert_type'],
        'priority': signal['priority'],
        'headline': signal['headline'],
        'message': signal['message'],
        'context': signal['context']
    }).execute()
    supabase.table('signal_snapshots').insert({
        'ticker': signal['ticker'],
        'setup_family': signal['setup_family'],
        'setup_state': signal['setup_state'],
        'score': signal['score'],
        'payload': signal['context']
    }).execute()

def main():
    print("🚀 Money Penny Worker Starting...")
    print(f"📡 Initializing Massive REST API...")
    
    # Initialize Massive client
    massive.connect()
    
    print("✅ Ready to pull live market data")
    
    seen = set()
    poll_count = 0
    
    print(f"⏱️  Polling interval: {config['system']['poll_interval_seconds']}s")
    print("📊 Monitoring symbols: " + ', '.join(config['massive']['symbols']))
    print()
    
    while True:
        try:
            poll_count += 1
            print(f"🔄 Poll #{poll_count}: Fetching live quotes...")
            
            # Get live data from Massive REST API
            snapshots = massive.get_snapshot()
            
            if snapshots:
                for symbol, snap in snapshots.items():
                    signal = evaluate_setup(symbol, snap)
                    if signal:
                        key = (signal['ticker'], signal['alert_type'], signal['priority'])
                        if key not in seen:
                            print(f"  📢 SIGNAL: {signal['headline']} (Price: ${snap['price']:.2f}, Score: {signal['score']})")
                            store_signal(signal)
                            telegram.send(f"{signal['headline']}\n{signal['message']}\nPrice: ${snap['price']:.2f}")
                            seen.add(key)
                
                print(f"  ✓ Checked {len(snapshots)} symbols\n")
            else:
                print("  ⚠️  No data returned\n")
            
            time.sleep(config['system']['poll_interval_seconds'])
            
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            time.sleep(config['system']['poll_interval_seconds'])

if __name__ == '__main__':
    main()
