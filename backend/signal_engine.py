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
        
        Args:
            symbol: Ticker
            candles: List of dict {time, open, high, low, close, volume, vwap, ema_20}
            current_snap: Latest market snapshot {price, vwap, ema_20, ...}
        
        Returns:
            Signal dict if triggered, None otherwise
        """
        if len(candles) < self.lookback:
            logger.debug(f"{symbol}: Not enough candles ({len(candles)} < {self.lookback})")
            return None
        
        # Get recent candles
        recent = candles[-self.lookback:]
        current = recent[-1]
        prev = recent[-2] if len(recent) > 1 else None
        
        # Check for VWAP/EMA crossover
        crossover_signal = self._detect_vwap_ema_crossover(symbol, recent, current_snap)
        if crossover_signal:
            return crossover_signal
        
        # Check for pullback reclaim
        reclaim_signal = self._detect_pullback_reclaim(symbol, recent, current_snap)
        if reclaim_signal:
            return reclaim_signal
        
        return None
    
    def _detect_vwap_ema_crossover(self, symbol: str, candles: List[Dict], 
                                   current_snap: Dict) -> Optional[Dict]:
        """
        Detect VWAP crossing above EMA20 with confirmation.
        
        Rules:
        - VWAP crosses above EMA20
        - Both VWAP and EMA20 are above the previous candle's values
        - Volume confirmation
        
        Log format: "WATCH: {reason}" / "READY: {reason}" / "INVALIDATED: {reason}"
        """
        current = candles[-1]
        prev = candles[-2] if len(candles) > 1 else None
        
        if not prev:
            logger.debug(f"{symbol}: Not enough history for crossover detection")
            return None
        
        # Extract values
        curr_vwap = current.get('vwap', 0)
        curr_ema = current.get('ema_20', 0)
        prev_vwap = prev.get('vwap', 0)
        prev_ema = prev.get('ema_20', 0)
        
        if not all([curr_vwap, curr_ema, prev_vwap, prev_ema]):
            logger.debug(f"{symbol}: Missing VWAP/EMA data")
            return None
        
        # Detect crossover: VWAP transitions from below to above EMA20
        was_below = prev_vwap < prev_ema
        is_above = curr_vwap > curr_ema
        
        if not (was_below and is_above):
            logger.debug(f"{symbol}: No VWAP/EMA crossover (prev: V={prev_vwap:.2f} E={prev_ema:.2f}, curr: V={curr_vwap:.2f} E={curr_ema:.2f})")
            return None
        
        # Check uptrend confirmation: both VWAP and EMA increasing
        vwap_up = curr_vwap > prev_vwap
        ema_up = curr_ema > prev_ema
        
        if not (vwap_up and ema_up):
            logger.info(f"{symbol}: INVALIDATED: Crossover but no uptrend (VWAP up={vwap_up}, EMA up={ema_up})")
            return {
                'ticker': symbol,
                'setup_family': 'VWAP_EMA_CROSSOVER',
                'setup_state': 'INVALIDATED',
                'entry_type': 'CROSSOVER',
                'reason': 'No uptrend confirmation',
                'setup_score': 0.35
            }
        
        # Check volume confirmation: current volume >= recent average
        curr_vol = current.get('volume', 0)
        recent_vols = [c.get('volume', 0) for c in candles[-5:]]
        avg_vol = sum(recent_vols) / len(recent_vols) if recent_vols else 0
        
        vol_confirmed = curr_vol >= avg_vol * 0.8  # 80% of average acceptable
        
        score = 0.75 if vol_confirmed else 0.60
        state = 'READY' if vol_confirmed else 'WATCH'
        
        log_msg = f"{state}: VWAP/EMA crossover (V={curr_vwap:.2f} > E={curr_ema:.2f})"
        if vol_confirmed:
            log_msg += f" + volume confirmed ({curr_vol})"
        
        logger.info(f"{symbol}: {log_msg}")
        
        return {
            'ticker': symbol,
            'setup_family': 'VWAP_EMA_CROSSOVER',
            'setup_state': state,
            'entry_type': 'CROSSOVER',
            'entry_price': current_snap.get('price', 0),
            'vwap_at_entry': curr_vwap,
            'ema20_at_entry': curr_ema,
            'setup_score': score,
            'reason': log_msg,
            'volume_confirmed': vol_confirmed
        }
    
    def _detect_pullback_reclaim(self, symbol: str, candles: List[Dict], 
                                 current_snap: Dict) -> Optional[Dict]:
        """
        Detect pullback reclaim: Price pulls below VWAP, then reclaims it.
        
        Rules:
        - Previous candle: price was above VWAP
        - Current candle: 
          - Low goes below VWAP (pullback)
          - Close reclaims above VWAP (reclaim)
        - EMA20 alignment confirmed
        
        Log format: "WATCH: Pullback detected" / "READY: Pullback reclaim confirmed"
        """
        if len(candles) < 2:
            return None
        
        current = candles[-1]
        prev = candles[-2]
        
        curr_price = current.get('close', 0)
        curr_vwap = current.get('vwap', 0)
        curr_ema = current.get('ema_20', 0)
        curr_high = current.get('high', 0)
        curr_low = current.get('low', 0)
        
        prev_price = prev.get('close', 0)
        prev_vwap = prev.get('vwap', 0)
        
        if not all([curr_price, curr_vwap, curr_ema, prev_price, prev_vwap]):
            return None
        
        # Setup condition: previous candle closed above VWAP
        prev_above_vwap = prev_price > prev_vwap
        if not prev_above_vwap:
            logger.debug(f"{symbol}: Previous candle not above VWAP (price={prev_price:.2f} vs VWAP={prev_vwap:.2f})")
            return None
        
        # Current candle: pulled below VWAP but reclaimed
        pulled_below = curr_low < curr_vwap
        reclaimed = curr_price > curr_vwap
        
        if not (pulled_below and reclaimed):
            logger.debug(f"{symbol}: No pullback/reclaim (low={curr_low:.2f}, VWAP={curr_vwap:.2f}, close={curr_price:.2f})")
            return None
        
        # EMA alignment
        ema_aligned = curr_vwap >= curr_ema
        
        if not ema_aligned:
            logger.info(f"{symbol}: INVALIDATED: Pullback reclaim but EMA misaligned (V={curr_vwap:.2f} < E={curr_ema:.2f})")
            return {
                'ticker': symbol,
                'setup_family': 'VWAP_PULLBACK_RECLAIM',
                'setup_state': 'INVALIDATED',
                'entry_type': 'PULLBACK_RECLAIM',
                'reason': 'EMA misalignment',
                'setup_score': 0.40
            }
        
        # Strong reclaim if close near high
        reclaim_strength = (curr_price - curr_low) / (curr_high - curr_low) if (curr_high - curr_low) > 0 else 0
        strong_reclaim = reclaim_strength > 0.7  # Upper 30% of candle
        
        score = 0.80 if strong_reclaim else 0.70
        state = 'READY' if strong_reclaim else 'WATCH'
        
        log_msg = f"{state}: Pullback reclaim (low={curr_low:.2f}, VWAP={curr_vwap:.2f}, close={curr_price:.2f})"
        if ema_aligned:
            log_msg += " + EMA aligned"
        
        logger.info(f"{symbol}: {log_msg}")
        
        return {
            'ticker': symbol,
            'setup_family': 'VWAP_PULLBACK_RECLAIM',
            'setup_state': state,
            'entry_type': 'PULLBACK_RECLAIM',
            'entry_price': curr_price,
            'vwap_at_entry': curr_vwap,
            'ema20_at_entry': curr_ema,
            'setup_score': score,
            'reason': log_msg,
            'pullback_low': curr_low,
            'reclaim_strength': reclaim_strength
        }
