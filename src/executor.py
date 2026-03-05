"""
Binance Executor - Gestion des ordres via ccxt.
Supporte testnet et production, market/limit orders.
Inclut kill-switch, circuit breaker, et gestion d'erreur robuste.
"""
import ccxt
import logging
import pandas as pd
import time
from typing import Dict, List, Optional, Literal
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)


def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """
    Décorateur pour retry automatique en cas d'erreur réseau.
    
    Args:
        max_retries: Nombre max de tentatives
        delay: Délai entre tentatives (secondes)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ccxt.NetworkError, ccxt.RequestTimeout) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"❌ {func.__name__} failed after {max_retries} attempts")
                        raise
                    logger.warning(
                        f"⚠️ {func.__name__} attempt {attempt+1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
        return wrapper
    return decorator


class KillSwitch:
    """
    Kill-switch pour arrêter le bot en cas de problème critique.
    """
    def __init__(self, max_loss_pct: float = 10.0, max_consecutive_losses: int = 5):
        """
        Args:
            max_loss_pct: Perte max en % avant kill (ex: 10 = -10%)
            max_consecutive_losses: Nombre max de pertes consécutives
        """
        self.max_loss_pct = max_loss_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.consecutive_losses = 0
        self.initial_capital = None
        self.is_active = True
        
    def check(self, current_capital: float, last_trade_profit: float = 0) -> bool:
        """
        Vérifie si le kill-switch doit s'activer.
        
        Args:
            current_capital: Capital actuel
            last_trade_profit: Profit du dernier trade (0 si pas de trade)
            
        Returns:
            True si OK, False si KILL
        """
        if not self.is_active:
            return False
        
        # Init
        if self.initial_capital is None:
            self.initial_capital = current_capital
            return True
        
        # Check perte totale
        total_loss_pct = ((current_capital - self.initial_capital) / self.initial_capital) * 100
        if total_loss_pct <= -self.max_loss_pct:
            logger.critical(
                f"🛑 KILL-SWITCH ACTIVÉ: Perte totale {total_loss_pct:.2f}% > {self.max_loss_pct}%"
            )
            self.is_active = False
            return False
        
        # Check pertes consécutives
        if last_trade_profit < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.max_consecutive_losses:
                logger.critical(
                    f"🛑 KILL-SWITCH ACTIVÉ: {self.consecutive_losses} pertes consécutives"
                )
                self.is_active = False
                return False
        else:
            self.consecutive_losses = 0
        
        return True


class CircuitBreaker:
    """
    Circuit breaker pour limiter la fréquence de trading.
    """
    def __init__(self, max_trades_per_hour: int = 5):
        self.max_trades_per_hour = max_trades_per_hour
        self.trade_timestamps = []
        
    def can_trade(self) -> bool:
        """
        Vérifie si on peut trader (pas trop de trades récents).
        """
        now = time.time()
        # Nettoyer trades > 1h
        self.trade_timestamps = [t for t in self.trade_timestamps if now - t < 3600]
        
        if len(self.trade_timestamps) >= self.max_trades_per_hour:
            logger.warning(
                f"⚠️ Circuit breaker: {len(self.trade_timestamps)} trades dans la dernière heure. "
                f"Max = {self.max_trades_per_hour}"
            )
            return False
        return True
    
    def record_trade(self):
        """Enregistre un trade."""
        self.trade_timestamps.append(time.time())


class BinanceExecutor:
    """Exécuteur d'ordres sur Binance via ccxt."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        enable_kill_switch: bool = True,
        kill_switch_max_loss: float = 10.0
    ):
        """
        Initialise la connexion Binance.

        Args:
            api_key: Clé API Binance
            api_secret: Secret API Binance
            testnet: Si True, utilise testnet (recommandé pour début)
            enable_kill_switch: Activer le kill-switch
            kill_switch_max_loss: Perte max en % avant kill
        """
        self.testnet = testnet
        
        # Kill-switch & circuit breaker
        self.kill_switch = KillSwitch(max_loss_pct=kill_switch_max_loss) if enable_kill_switch else None
        self.circuit_breaker = CircuitBreaker(max_trades_per_hour=10)

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
    
    def is_operational(self, current_capital: float = None, last_trade_profit: float = 0) -> bool:
        """
        Vérifie si le bot peut continuer à trader.
        
        Args:
            current_capital: Capital actuel
            last_trade_profit: Profit dernier trade
            
        Returns:
            True si OK, False si STOP
        """
        # Check kill-switch
        if self.kill_switch and current_capital is not None:
            if not self.kill_switch.check(current_capital, last_trade_profit):
                return False
        
        # Check circuit breaker
        if not self.circuit_breaker.can_trade():
            return False
        
        return True

    @retry_on_error(max_retries=3, delay=1.0)
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

        except ccxt.ExchangeError as e:
            logger.error(f"⚠️ Erreur exchange: {e}")
            raise

    @retry_on_error(max_retries=3, delay=1.0)
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

    @retry_on_error(max_retries=3, delay=1.0)
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
        # Check circuit breaker
        if not self.circuit_breaker.can_trade():
            raise RuntimeError("Circuit breaker activé: trop de trades récents")
        
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
            
            # Record trade
            self.circuit_breaker.record_trade()

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

    @retry_on_error(max_retries=3, delay=1.0)
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
        # Check circuit breaker
        if not self.circuit_breaker.can_trade():
            raise RuntimeError("Circuit breaker activé: trop de trades récents")
        
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
            
            # Record trade
            self.circuit_breaker.record_trade()

            logger.info(f"✅ Ordre limit placé: {order['id']}")
            return order

        except Exception as e:
            logger.error(f"❌ Erreur place_limit_order: {e}")
            raise

    @retry_on_error(max_retries=3, delay=1.0)
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

    @retry_on_error(max_retries=3, delay=1.0)
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

    @retry_on_error(max_retries=3, delay=1.0)
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
