import json
from pathlib import Path
from massive import RESTClient
from datetime import datetime, timedelta
import threading
import time
import math

class MassiveClient:
    def __init__(self, config_path='config.json'):
        self.config = json.loads(Path(config_path).read_text())
        self.api_key = self.config['massive']['api_key']
        self.symbols = self.config['massive']['symbols']
        self.data = {}
        self.connected = False
        self.client = None

    def connect(self):
        """Connect to Massive REST API using official client"""
        try:
            # Create REST client
            self.client = RESTClient(api_key=self.api_key)
            
            print(f"✓ Massive REST client initialized")
            print(f"✓ Monitoring: {', '.join(self.symbols)}")
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"✗ Connection error: {e}")
            self.connected = False
            return False

    def get_snapshot(self):
        """Get live snapshot of all symbols from Massive REST API"""
        if not self.connected or not self.client:
            print(f"  ⚠️  Not connected - using mock data")
            return self.mock_snapshot()
        
        snapshot = {}
        live_count = 0
        
        # Get today's date for aggregates
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        for symbol in self.symbols:
            try:
                # Get last trade (current price)
                trade = self.client.get_last_trade(symbol)
                price = float(trade.price) if trade and hasattr(trade, 'price') else 0
                
                if price <= 0:
                    continue
                
                # Get last quote (bid/ask)
                quote = self.client.get_last_quote(symbol)
                bid = float(quote.bid_price) if quote and hasattr(quote, 'bid_price') else 0
                ask = float(quote.ask_price) if quote and hasattr(quote, 'ask_price') else 0
                
                # Get today's minute aggregates to calculate VWAP
                vwap = price * 0.999  # Fallback: slightly below price
                ema20 = price  # Fallback
                
                try:
                    # Fetch minute aggregates for today
                    aggs = list(self.client.list_aggs(
                        ticker=symbol,
                        multiplier=1,
                        timespan="minute",
                        from_=str(today),
                        to=str(today),
                        limit=300
                    ))
                    
                    if aggs:
                        # Calculate VWAP from aggregates: sum(high+low+close)/3 * volume / total_volume
                        total_volume = 0
                        weighted_price = 0
                        
                        for agg in aggs:
                            if hasattr(agg, 'volume') and hasattr(agg, 'close'):
                                vol = float(agg.volume)
                                # Use close price weighted by volume
                                close = float(agg.close)
                                weighted_price += close * vol
                                total_volume += vol
                        
                        if total_volume > 0:
                            vwap = weighted_price / total_volume
                        
                        # Use last close as EMA20 approximation
                        if aggs and hasattr(aggs[-1], 'close'):
                            ema20 = float(aggs[-1].close)
                except Exception as e:
                    pass  # Use fallback values
                
                snapshot[symbol] = {
                    'price': price,
                    'vwap': vwap if vwap > 0 else price * 0.999,
                    'ema20': ema20,
                    'volume': float(trade.size) if hasattr(trade, 'size') else 0,
                    'bid': bid,
                    'ask': ask,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'massive_rest'
                }
                live_count += 1
                
            except Exception as e:
                print(f"  ⚠️  {symbol}: fetch error — {e}")
                continue

        if live_count > 0:
            print(f"  ✓ Fetched {live_count}/{len(self.symbols)} live quotes from Massive REST API")
            return snapshot
        else:
            print(f"  ⚠️  No live data - using mock data")
            return self.mock_snapshot()

    def get_session_levels(self, symbol: str) -> dict:
        """Fetch previous day OHLC and key S/R levels from last 5 days."""
        if not self.connected or not self.client:
            return self._mock_session_levels(symbol)
        try:
            today = datetime.now().date()
            aggs = list(self.client.list_aggs(
                ticker=symbol,
                multiplier=1,
                timespan='day',
                from_=str(today - timedelta(days=12)),
                to=str(today - timedelta(days=1)),
                limit=10
            ))
            if not aggs:
                return self._mock_session_levels(symbol)

            aggs = sorted(aggs, key=lambda x: getattr(x, 'timestamp', 0))
            prev = aggs[-1]

            # Collect significant highs/lows from last 5 days
            raw_levels = []
            for a in aggs[-5:]:
                raw_levels.append(float(a.high))
                raw_levels.append(float(a.low))

            # Deduplicate levels within 0.3% of each other
            raw_levels = sorted(raw_levels)
            deduped = []
            for lvl in raw_levels:
                if not deduped or abs(lvl - deduped[-1]) / deduped[-1] > 0.003:
                    deduped.append(round(lvl, 2))

            return {
                'prev_day_high':  round(float(prev.high), 2),
                'prev_day_low':   round(float(prev.low), 2),
                'prev_day_close': round(float(prev.close), 2),
                'prev_day_open':  round(float(prev.open), 2),
                'sr_levels':      deduped,
                'source': 'live',
            }
        except Exception as e:
            print(f'  ⚠️  {symbol}: session levels error — {e}')
            return self._mock_session_levels(symbol)

    def _mock_session_levels(self, symbol: str) -> dict:
        mock_bases = {
            'SPY':588,'QQQ':640,'IWM':198,'AAPL':195,'AMZN':199,
            'META':677,'MSFT':421,'NVDA':198,'TSLA':388,'GOOGL':337,
        }
        b = mock_bases.get(symbol, 300)
        return {
            'prev_day_high':  round(b * 1.008, 2),
            'prev_day_low':   round(b * 0.992, 2),
            'prev_day_close': round(b * 1.001, 2),
            'prev_day_open':  round(b * 0.998, 2),
            'sr_levels': [
                round(b * 0.985, 2), round(b * 0.992, 2),
                round(b * 1.000, 2), round(b * 1.008, 2), round(b * 1.015, 2),
            ],
            'source': 'mock',
        }

    def mock_snapshot(self):
        """Fallback mock data — all 10 symbols covered"""
        ts = datetime.now().isoformat()
        return {
            'SPY':   {'price': 588.20, 'vwap': 587.80, 'ema20': 587.00, 'volume': 185000000, 'bid': 588.15, 'ask': 588.25, 'timestamp': ts, 'source': 'mock'},
            'QQQ':   {'price': 640.47, 'vwap': 639.50, 'ema20': 638.00, 'volume': 125000000, 'bid': 640.40, 'ask': 640.55, 'timestamp': ts, 'source': 'mock'},
            'IWM':   {'price': 198.50, 'vwap': 197.80, 'ema20': 197.00, 'volume': 95000000,  'bid': 198.45, 'ask': 198.55, 'timestamp': ts, 'source': 'mock'},
            'AAPL':  {'price': 195.30, 'vwap': 194.80, 'ema20': 194.00, 'volume': 78000000,  'bid': 195.25, 'ask': 195.35, 'timestamp': ts, 'source': 'mock'},
            'AMZN':  {'price': 198.60, 'vwap': 197.90, 'ema20': 197.20, 'volume': 52000000,  'bid': 198.55, 'ask': 198.65, 'timestamp': ts, 'source': 'mock'},
            'META':  {'price': 562.40, 'vwap': 561.00, 'ema20': 560.00, 'volume': 18000000,  'bid': 562.35, 'ask': 562.45, 'timestamp': ts, 'source': 'mock'},
            'MSFT':  {'price': 420.75, 'vwap': 420.00, 'ema20': 419.00, 'volume': 32000000,  'bid': 420.70, 'ask': 420.80, 'timestamp': ts, 'source': 'mock'},
            'NVDA':  {'price': 125.50, 'vwap': 124.80, 'ema20': 124.00, 'volume': 142000000, 'bid': 125.45, 'ask': 125.55, 'timestamp': ts, 'source': 'mock'},
            'TSLA':  {'price': 248.30, 'vwap': 247.50, 'ema20': 246.80, 'volume': 95000000,  'bid': 248.25, 'ask': 248.35, 'timestamp': ts, 'source': 'mock'},
            'GOOGL': {'price': 172.80, 'vwap': 172.10, 'ema20': 171.50, 'volume': 28000000,  'bid': 172.75, 'ask': 172.85, 'timestamp': ts, 'source': 'mock'},
        }
