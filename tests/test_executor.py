"""
Tests unitaires pour BinanceExecutor.
Utilise des mocks pour éviter vrais appels API.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from src.executor import BinanceExecutor


class TestBinanceExecutor:
    """Tests pour BinanceExecutor."""

    @patch('src.executor.ccxt.binance')
    def test_initialization_testnet(self, mock_binance):
        """Test initialisation en mode testnet."""
        mock_exchange = Mock()
        mock_exchange.load_markets = Mock(return_value={'BTC/USDT': {}})
        mock_exchange.markets = {'BTC/USDT': {}, 'ETH/USDT': {}}
        mock_binance.return_value = mock_exchange

        executor = BinanceExecutor('test_key', 'test_secret', testnet=True)

        assert executor.testnet is True
        mock_exchange.set_sandbox_mode.assert_called_once_with(True)
        mock_exchange.load_markets.assert_called_once()

    @patch('src.executor.ccxt.binance')
    def test_fetch_ohlcv(self, mock_binance):
        """Test récupération données OHLCV."""
        mock_exchange = Mock()
        mock_exchange.load_markets = Mock(return_value={})
        mock_exchange.markets = {}

        # Mock OHLCV data
        mock_ohlcv = [
            [1609459200000, 29000, 29500, 28500, 29200, 1000],  # timestamp, o, h, l, c, v
            [1609462800000, 29200, 29800, 29100, 29600, 1200],
        ]
        mock_exchange.fetch_ohlcv = Mock(return_value=mock_ohlcv)
        mock_binance.return_value = mock_exchange

        executor = BinanceExecutor('key', 'secret', testnet=True)
        df = executor.fetch_ohlcv('BTC/USDT', '1h', 2)

        assert len(df) == 2
        assert 'open' in df.columns
        assert 'close' in df.columns
        assert df['close'].iloc[0] == 29200

    @patch('src.executor.ccxt.binance')
    def test_get_balance(self, mock_binance):
        """Test récupération balance."""
        mock_exchange = Mock()
        mock_exchange.load_markets = Mock(return_value={})
        mock_exchange.markets = {}
        mock_exchange.fetch_balance = Mock(return_value={
            'USDT': {'free': 100.0, 'used': 20.0, 'total': 120.0}
        })
        mock_binance.return_value = mock_exchange

        executor = BinanceExecutor('key', 'secret', testnet=True)
        balance = executor.get_balance('USDT')

        assert balance['free'] == 100.0
        assert balance['total'] == 120.0

    @patch('src.executor.ccxt.binance')
    def test_place_market_order(self, mock_binance):
        """Test placement ordre market."""
        mock_exchange = Mock()
        mock_exchange.load_markets = Mock(return_value={})
        mock_exchange.markets = {}
        mock_exchange.fetch_ticker = Mock(return_value={'last': 50000.0})
        mock_exchange.create_market_order = Mock(return_value={
            'id': '12345',
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'amount': 0.0002,
            'average': 50000.0
        })
        mock_binance.return_value = mock_exchange

        executor = BinanceExecutor('key', 'secret', testnet=True)
        order = executor.place_market_order('BTC/USDT', 'buy', 10.0)

        assert order['id'] == '12345'
        assert order['side'] == 'buy'
        mock_exchange.create_market_order.assert_called_once()

    @patch('src.executor.ccxt.binance')
    def test_get_open_orders(self, mock_binance):
        """Test récupération ordres ouverts."""
        mock_exchange = Mock()
        mock_exchange.load_markets = Mock(return_value={})
        mock_exchange.markets = {}
        mock_exchange.fetch_open_orders = Mock(return_value=[
            {'id': '1', 'symbol': 'BTC/USDT'},
            {'id': '2', 'symbol': 'BTC/USDT'}
        ])
        mock_binance.return_value = mock_exchange

        executor = BinanceExecutor('key', 'secret', testnet=True)
        orders = executor.get_open_orders('BTC/USDT')

        assert len(orders) == 2
        assert orders[0]['id'] == '1'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
