"""
Tests unitaires pour le client Blockscout.
"""
import pytest
from src.blockscout_client import BlockscoutClient


class TestBlockscoutClient:
    """Tests pour BlockscoutClient."""
    
    def test_initialization(self):
        """Test initialisation du client."""
        client = BlockscoutClient(default_chain_id="1")
        assert client.chain_id == "1"
    
    def test_get_address_balance_mock(self):
        """Test récupération balance (mock)."""
        client = BlockscoutClient()
        
        # Test avec adresse Ethereum valide
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        balance = client.get_address_balance(address)
        
        assert balance is not None
        assert 'coin_balance' in balance
        assert 'coin_balance_decimal' in balance
    
    def test_get_token_holdings_mock(self):
        """Test récupération tokens (mock)."""
        client = BlockscoutClient()
        
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        tokens = client.get_token_holdings(address)
        
        assert isinstance(tokens, list)
    
    def test_get_gas_price(self):
        """Test récupération prix gas."""
        client = BlockscoutClient()
        gas = client.get_gas_price()
        
        assert 'slow' in gas
        assert 'average' in gas
        assert 'fast' in gas
        assert gas['fast'] >= gas['average'] >= gas['slow']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
