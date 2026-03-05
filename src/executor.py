"""
Binance Executor - Gestion des ordres via ccxt.
Supporte testnet et production, market/limit orders.
"""
import ccxt
import logging
import pandas as pd
from typing import Dict, List, Optional, Literal
from datetime import datetime

logger = logging.getLogger(__name__)


class BinanceExecutor:
    """Exécuteur d'ordres sur Binance via ccxt."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialise la connexion Binance.

        Args:
            api_key: Clé API Binance
            api_secret: Secret API Binance
            testnet: Si True, utilise testnet (recommandé pour début)
        """
        self.testnet = testnet

        if testnet:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'test': True
                }
            })
            # URLs testnet
            self.exchange.set_sandbox_mode(True)
            logger.info("⚠️ Binance Executor en mode TESTNET")
        else:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            logger.warning("🔴 Binance Executor en mode PRODUCTION")

        # Vérifier connexion
        try:
            self.exchange.load_markets()
            logger.info(f"✅ Connecté à Binance ({len(self.exchange.markets)} paires)")
        except Exception as e:
            logger.error(f"❌ Erreur connexion Binance: {e}")
            raise

    def fetch_ohlcv(
        self, pair: str, timeframe: str = '1h', limit: int = 100
    ) -> pd.DataFrame:
        """
        Récupère les données OHLCV historiques.

        Args:
            pair: Paire de trading (ex: 'BTC/USDT')
            timeframe: Intervalle ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Nombre de bougies (max 1000)

        Returns:
            DataFrame avec colonnes [timestamp, open, high, low, close, volume]

        Example:
            >>> executor = BinanceExecutor(key, secret, testnet=True)
            >>> df = executor.fetch_ohlcv('BTC/USDT', '1h', 50)
            >>> print(df.tail())
        """
        try:
            logger.debug(f"Fetching {limit} bougies {timeframe} pour {pair}")
            ohlcv = self.exchange.fetch_ohlcv(pair, timeframe, limit=limit)

            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            logger.info(
                f"✅ {len(df)} bougies récupérées pour {pair} "
                f"({df['timestamp'].min()} -> {df['timestamp'].max()})"
            )
            return df

        except ccxt.NetworkError as e:
            logger.error(f"🌐 Erreur réseau: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"⚠️ Erreur exchange: {e}")
            raise

    def get_balance(self, asset: str = 'USDT') -> Dict[str, float]:
        """
        Récupère la balance d'un asset.

        Args:
            asset: Symbole de l'asset (USDT, BTC, ETH, etc.)

        Returns:
            Dict avec 'free' (disponible), 'used' (bloqué), 'total'

        Example:
            >>> balance = executor.get_balance('USDT')
            >>> print(f"Disponible: {balance['free']} USDT")
        """
        try:
            balance = self.exchange.fetch_balance()

            if asset not in balance:
                logger.warning(f"{asset} non trouvé dans le wallet")
                return {'free': 0.0, 'used': 0.0, 'total': 0.0}

            asset_balance = balance[asset]
            logger.info(
                f"💰 Balance {asset}: {asset_balance['free']:.2f} libre, "
                f"{asset_balance['used']:.2f} bloqué"
            )
            return asset_balance

        except ccxt.AuthenticationError as e:
            logger.error(f"🔑 Erreur authentification: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Erreur get_balance: {e}")
            raise

    def place_market_order(
        self, pair: str, side: Literal['buy', 'sell'], amount_usdt: float
    ) -> Dict:
        """
        Place un ordre market (exécution immédiate au prix marché).

        Args:
            pair: Paire de trading (ex: 'BTC/USDT')
            side: 'buy' ou 'sell'
            amount_usdt: Montant en USDT à trader

        Returns:
            Dict avec infos ordre (id, price, amount, cost, etc.)

        Example:
            >>> order = executor.place_market_order('BTC/USDT', 'buy', 10.0)
            >>> print(f"Achaté {order['amount']} BTC à {order['price']}")
        """
        try:
            # Calculer quantité en base asset
            ticker = self.exchange.fetch_ticker(pair)
            current_price = ticker['last']
            amount = amount_usdt / current_price

            logger.info(
                f"📊 {side.upper()} {amount:.6f} {pair} à ~{current_price:.2f} "
                f"(total ~{amount_usdt:.2f} USDT)"
            )

            order = self.exchange.create_market_order(
                symbol=pair,
                side=side,
                amount=amount
            )

            logger.info(
                f"✅ Ordre market exécuté: {order['id']} | "
                f"Prix moyen: {order.get('average', 'N/A')}"
            )
            return order

        except ccxt.InsufficientFunds as e:
            logger.error(f"🚫 Fonds insuffisants: {e}")
            raise
        except ccxt.InvalidOrder as e:
            logger.error(f"⚠️ Ordre invalide: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Erreur place_market_order: {e}")
            raise

    def place_limit_order(
        self, pair: str, side: Literal['buy', 'sell'],
        amount: float, price: float
    ) -> Dict:
        """
        Place un ordre limit (exécution au prix spécifié ou meilleur).

        Args:
            pair: Paire de trading
            side: 'buy' ou 'sell'
            amount: Quantité en base asset (BTC, ETH, etc.)
            price: Prix limit en quote asset (USDT)

        Returns:
            Dict avec infos ordre

        Example:
            >>> order = executor.place_limit_order('BTC/USDT', 'buy', 0.001, 40000)
        """
        try:
            logger.info(
                f"🎯 {side.upper()} limit {amount:.6f} {pair} @ {price:.2f}"
            )

            order = self.exchange.create_limit_order(
                symbol=pair,
                side=side,
                amount=amount,
                price=price
            )

            logger.info(f"✅ Ordre limit placé: {order['id']}")
            return order

        except Exception as e:
            logger.error(f"❌ Erreur place_limit_order: {e}")
            raise

    def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        """
        Récupère les ordres ouverts.

        Args:
            pair: Filtre par paire (optionnel, None = tous)

        Returns:
            Liste d'ordres ouverts

        Example:
            >>> orders = executor.get_open_orders('BTC/USDT')
            >>> print(f"{len(orders)} ordres ouverts")
        """
        try:
            orders = self.exchange.fetch_open_orders(pair)
            logger.info(f"📜 {len(orders)} ordres ouverts pour {pair or 'toutes paires'}")
            return orders

        except Exception as e:
            logger.error(f"❌ Erreur get_open_orders: {e}")
            raise

    def cancel_order(self, order_id: str, pair: str) -> Dict:
        """
        Annule un ordre ouvert.

        Args:
            order_id: ID de l'ordre à annuler
            pair: Paire de trading

        Returns:
            Dict avec infos annulation

        Example:
            >>> result = executor.cancel_order('12345', 'BTC/USDT')
        """
        try:
            result = self.exchange.cancel_order(order_id, pair)
            logger.info(f"❌ Ordre {order_id} annulé sur {pair}")
            return result

        except ccxt.OrderNotFound as e:
            logger.warning(f"⚠️ Ordre introuvable: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Erreur cancel_order: {e}")
            raise

    def get_ticker(self, pair: str) -> Dict[str, float]:
        """
        Récupère le ticker (prix actuel, 24h stats).

        Args:
            pair: Paire de trading

        Returns:
            Dict avec last, bid, ask, high, low, volume
        """
        try:
            ticker = self.exchange.fetch_ticker(pair)
            return {
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'high': ticker['high'],
                'low': ticker['low'],
                'volume': ticker['quoteVolume']
            }
        except Exception as e:
            logger.error(f"❌ Erreur get_ticker: {e}")
            raise
