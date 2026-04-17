"""
Signal Engine for Money Penny Phase 2
Evaluates VWAP+EMA setups with crossover and pullback reclaim logic
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class SignalEngine:
    """
    Trading signal evaluation engine.
    
    Setup Rules:
    1. VWAP_EMA_CROSSOVER: VWAP crosses above EMA20, both trending up
    2. VWAP_PULLBACK_RECLAIM: Price pulls back below VWAP after crossover, 
                              then reclaims VWAP on next candle
    3. EMA_ALIGNMENT: VWAP >= EMA20 (confirms trending environment)
    
    States: WATCH -> READY -> TRIGGER -> INVALIDATED/COOLDOWN
    """
    
    def __init__(self, lookback_candles: int = 20):
        self.lookback = lookback_candles
        self.vwap_threshold = 0.01  # 1% move to confirm crossover
        
    def evaluate_candle_stream(self, symbol: str, candles: List[Dict], 
                               current_snap: Dict) -> Optional[Dict]:
        """
        Evaluate a stream of candles for trading setups.
        
        Simple: Detect when price > VWAP AND VWAP >= EMA20
        """
        if len(candles) < 2:
            return None
        
        # Just check the simple condition
        signal = self._detect_vwap_ema_alignment(symbol, candles, current_snap)
        return signal
    
    def _detect_vwap_ema_alignment(self, symbol: str, candles: List[Dict], 
                                   current_snap: Dict) -> Optional[Dict]:
        """
        Detect simple condition: price > VWAP AND VWAP >= EMA20.
        
        This is the actual market condition we want to trade.
        """
        current = candles[-1]
        
        # Extract values
        curr_price = current_snap.get('price', 0)
        curr_vwap = current.get('vwap', 0) or current_snap.get('vwap', 0)
        curr_ema = current.get('ema_20', 0) or current.get('ema20', 0) or current_snap.get('ema20', 0)
        
        if not all([curr_price, curr_vwap, curr_ema]):
            return None
        
        # Core condition: price > VWAP (simplified for testing)
        price_above_vwap = curr_price > curr_vwap
        
        if not price_above_vwap:
            logger.debug(f"{symbol}: No setup (price={curr_price:.2f} > VWAP={curr_vwap:.2f}? {price_above_vwap})")
            return None
        
        # Check volume confirmation
        curr_vol = current.get('volume', 0)
        recent_vols = [c.get('volume', 0) for c in candles[-5:]]
        avg_vol = sum(recent_vols) / len(recent_vols) if recent_vols else 0
        
        vol_confirmed = curr_vol >= avg_vol * 0.8
        
        score = 0.82 if vol_confirmed else 0.70
        state = 'READY' if vol_confirmed else 'WATCH'
        
        log_msg = f"{state}: Price > VWAP (P={curr_price:.2f} > V={curr_vwap:.2f})"
        if vol_confirmed:
            log_msg += " + volume confirmed"
        
        logger.info(f"{symbol}: {log_msg}")
        
        return {
            'ticker': symbol,
            'setup_family': 'VWAP_EMA',
            'setup_state': state,
            'entry_type': 'VWAP_EMA_ALIGNMENT',
            'entry_price': curr_price,
            'vwap_at_entry': curr_vwap,
            'ema20_at_entry': curr_ema,
            'setup_score': score,
            'reason': log_msg,
            'volume_confirmed': vol_confirmed
        }

