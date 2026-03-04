"""
Stratégies de trading - Version 1: DCA optimisé.
"""
import pandas as pd
import logging
from typing import Dict, Literal, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DCAStrategy:
    """Dollar Cost Averaging avec indicateurs techniques."""
    
    def __init__(self, config: Dict):
        """
        Initialise la stratégie DCA.
        
        Args:
            config: Dict contenant buy_threshold_rsi, sell_threshold_rsi, sma_period, pairs
        """
        self.rsi_buy = config['buy_threshold_rsi']
        self.rsi_sell = config['sell_threshold_rsi']
        self.sma_period = config.get('sma_period', 20)
        self.pairs = config['pairs']
        self.interval = config.get('interval', '1h')
        
        logger.info(
            f"DCA Strategy init: RSI buy<{self.rsi_buy}, sell>{self.rsi_sell}, "
            f"SMA{self.sma_period}, pairs={self.pairs}"
        )
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """
        Calcule l'indice de force relative (RSI).
        
        Args:
            prices: Série de prix de clôture
            period: Période pour le calcul (défaut 14)
            
        Returns:
            Valeur RSI actuelle (0-100)
        """
        if len(prices) < period + 1:
            return 50.0  # Valeur neutre si pas assez de données
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Éviter division par zéro
        rs = gain / loss.replace(0, 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    def calculate_sma(self, prices: pd.Series, period: int) -> float:
        """
        Calcule la moyenne mobile simple.
        
        Args:
            prices: Série de prix
            period: Période de la moyenne
            
        Returns:
            Valeur SMA actuelle
        """
        if len(prices) < period:
            return prices.mean()
        return prices.rolling(period).mean().iloc[-1]
    
    def generate_signal(self, ohlcv_data: pd.DataFrame) -> Literal["BUY", "SELL", "HOLD"]:
        """
        Génère un signal de trading basé sur RSI et SMA.
        
        Logique:
        - BUY: RSI < seuil_achat ET prix < SMA (survente + tendance baissière)
        - SELL: RSI > seuil_vente (surachat)
        - HOLD: sinon
        
        Args:
            ohlcv_data: DataFrame avec colonnes [timestamp, open, high, low, close, volume]
            
        Returns:
            Signal "BUY", "SELL" ou "HOLD"
        """
        if len(ohlcv_data) < max(self.sma_period, 20):
            logger.warning(f"Pas assez de données: {len(ohlcv_data)} bougies")
            return "HOLD"
        
        close_prices = ohlcv_data['close']
        
        # Calcul indicateurs
        rsi = self.calculate_rsi(close_prices)
        sma = self.calculate_sma(close_prices, self.sma_period)
        current_price = close_prices.iloc[-1]
        
        logger.debug(
            f"Indicateurs: RSI={rsi:.2f}, Prix={current_price:.2f}, "
            f"SMA{self.sma_period}={sma:.2f}"
        )
        
        # Génération signal
        if rsi < self.rsi_buy and current_price < sma:
            logger.info(f"✅ Signal BUY: RSI={rsi:.2f} < {self.rsi_buy}, Prix < SMA")
            return "BUY"
        elif rsi > self.rsi_sell:
            logger.info(f"💰 Signal SELL: RSI={rsi:.2f} > {self.rsi_sell}")
            return "SELL"
        else:
            logger.debug("⏸️ Signal HOLD: conditions non remplies")
            return "HOLD"
    
    def backtest(self, historical_data: pd.DataFrame, initial_capital: float = 100.0) -> Dict:
        """
        Backteste la stratégie sur données historiques.
        
        Args:
            historical_data: DataFrame OHLCV complet
            initial_capital: Capital de départ
            
        Returns:
            Dict avec résultats: profit, nb_trades, win_rate, etc.
        """
        # TODO: Implémenter logique complète de backtest
        logger.info(f"Backtesting sur {len(historical_data)} bougies...")
        
        capital = initial_capital
        trades = []
        position = None  # None, 'LONG'
        
        # Simulation simplifiée
        for i in range(self.sma_period, len(historical_data)):
            window = historical_data.iloc[:i+1]
            signal = self.generate_signal(window.tail(50))
            
            # TODO: Logique achat/vente avec capital tracking
            
        return {
            "initial_capital": initial_capital,
            "final_capital": capital,
            "profit_percent": ((capital - initial_capital) / initial_capital) * 100,
            "num_trades": len(trades),
            "win_rate": 0.0
        }
