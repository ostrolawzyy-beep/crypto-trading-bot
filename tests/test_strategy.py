"""
Tests unitaires pour les stratégies de trading.
"""
import pytest
import pandas as pd
import numpy as np
from src.strategy import DCAStrategy


@pytest.fixture
def strategy_config():
    """Configuration de test pour DCA."""
    return {
        'buy_threshold_rsi': 30,
        'sell_threshold_rsi': 70,
        'sma_period': 20,
        'pairs': ['BTC/USDT'],
        'interval': '1h'
    }


@pytest.fixture
def sample_ohlcv():
    """Données OHLCV de test."""
    dates = pd.date_range('2024-01-01', periods=50, freq='1h')
    np.random.seed(42)
    
    # Simuler une tendance baissière pour RSI bas
    close_prices = 100 * (1 - np.linspace(0, 0.2, 50)) + np.random.randn(50) * 2
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': close_prices + np.random.randn(50) * 0.5,
        'high': close_prices + np.abs(np.random.randn(50)) * 1,
        'low': close_prices - np.abs(np.random.randn(50)) * 1,
        'close': close_prices,
        'volume': np.random.randint(1000, 5000, 50)
    })


class TestDCAStrategy:
    """Tests pour la stratégie DCA."""
    
    def test_initialization(self, strategy_config):
        """Test initialisation de la stratégie."""
        strategy = DCAStrategy(strategy_config)
        
        assert strategy.rsi_buy == 30
        assert strategy.rsi_sell == 70
        assert strategy.sma_period == 20
        assert 'BTC/USDT' in strategy.pairs
    
    def test_calculate_rsi(self, strategy_config):
        """Test calcul RSI."""
        strategy = DCAStrategy(strategy_config)
        
        # Créer série avec tendance baissière (RSI devrait être bas)
        prices = pd.Series([100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50, 48, 46, 44, 42])
        rsi = strategy.calculate_rsi(prices, period=14)
        
        assert 0 <= rsi <= 100, "RSI doit être entre 0 et 100"
        assert rsi < 50, "RSI devrait être bas avec tendance baissière"
    
    def test_calculate_sma(self, strategy_config):
        """Test calcul SMA."""
        strategy = DCAStrategy(strategy_config)
        
        prices = pd.Series([10, 20, 30, 40, 50])
        sma = strategy.calculate_sma(prices, period=3)
        
        # SMA des 3 derniers: (30+40+50)/3 = 40
        assert sma == 40.0
    
    def test_generate_buy_signal(self, strategy_config, sample_ohlcv):
        """Test génération signal BUY."""
        strategy = DCAStrategy(strategy_config)
        signal = strategy.generate_signal(sample_ohlcv)
        
        # Avec tendance baissière, devrait générer BUY
        assert signal in ['BUY', 'SELL', 'HOLD']
    
    def test_generate_signal_insufficient_data(self, strategy_config):
        """Test avec données insuffisantes."""
        strategy = DCAStrategy(strategy_config)
        
        # Seulement 5 bougies (< 20 requis)
        small_df = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'open': [99, 100, 101, 102, 103],
            'high': [101, 102, 103, 104, 105],
            'low': [98, 99, 100, 101, 102],
            'volume': [1000] * 5
        })
        
        signal = strategy.generate_signal(small_df)
        assert signal == 'HOLD', "Devrait retourner HOLD avec données insuffisantes"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
