"""
Stratégies de trading - Version 1: DCA optimisé.
"""
import pandas as pd
import logging
from typing import Dict, Literal, Optional

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
        self.trade_amount_percent = config.get('trade_amount_percent', 0.5)

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
            logger.debug(f"Signal BUY: RSI={rsi:.2f} < {self.rsi_buy}, Prix < SMA")
            return "BUY"
        elif rsi > self.rsi_sell:
            logger.debug(f"Signal SELL: RSI={rsi:.2f} > {self.rsi_sell}")
            return "SELL"
        else:
            logger.debug("Signal HOLD: conditions non remplies")
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
        logger.info(f"Backtesting sur {len(historical_data)} bougies...")

        # Variables de suivi
        cash = initial_capital
        position_size = 0.0  # Quantité de crypto détenue
        position_entry_price = 0.0
        trades = []
        in_position = False

        # Parcourir les données historiques
        for i in range(self.sma_period + 20, len(historical_data)):
            # Fenêtre de données pour indicateurs
            window = historical_data.iloc[:i+1]
            current_price = window['close'].iloc[-1]
            current_time = window['timestamp'].iloc[-1]

            # Générer signal
            signal = self.generate_signal(window)

            # Exécuter trade selon signal
            if signal == "BUY" and not in_position and cash > 0:
                # Acheter
                trade_amount = cash * self.trade_amount_percent
                position_size = trade_amount / current_price
                position_entry_price = current_price
                cash -= trade_amount
                in_position = True

                logger.info(
                    f"[{current_time}] BUY {position_size:.6f} @ {current_price:.2f} "
                    f"(total: {trade_amount:.2f})"
                )

                trades.append({
                    'type': 'BUY',
                    'timestamp': current_time,
                    'price': current_price,
                    'amount': position_size,
                    'cost': trade_amount
                })

            elif signal == "SELL" and in_position:
                # Vendre
                sell_value = position_size * current_price
                profit = sell_value - (position_size * position_entry_price)
                profit_pct = (profit / (position_size * position_entry_price)) * 100

                cash += sell_value

                logger.info(
                    f"[{current_time}] SELL {position_size:.6f} @ {current_price:.2f} "
                    f"(total: {sell_value:.2f}, P&L: {profit:.2f} [{profit_pct:+.2f}%])"
                )

                trades.append({
                    'type': 'SELL',
                    'timestamp': current_time,
                    'price': current_price,
                    'amount': position_size,
                    'revenue': sell_value,
                    'profit': profit,
                    'profit_pct': profit_pct
                })

                position_size = 0.0
                in_position = False

        # Calculer capital final (inclure position ouverte)
        final_capital = cash
        if in_position:
            final_price = historical_data['close'].iloc[-1]
            final_capital += position_size * final_price
            logger.warning(
                f"Position encore ouverte: {position_size:.6f} @ {final_price:.2f}"
            )

        # Calculer métriques
        sell_trades = [t for t in trades if t['type'] == 'SELL']
        winning_trades = [t for t in sell_trades if t['profit'] > 0]

        win_rate = (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0
        total_profit = sum(t['profit'] for t in sell_trades)
        profit_percent = ((final_capital - initial_capital) / initial_capital) * 100

        return {
            "initial_capital": initial_capital,
            "final_capital": final_capital,
            "profit_percent": profit_percent,
            "total_profit": total_profit,
            "num_trades": len(trades),
            "num_buy": len([t for t in trades if t['type'] == 'BUY']),
            "num_sell": len(sell_trades),
            "win_rate": win_rate,
            "winning_trades": len(winning_trades),
            "losing_trades": len(sell_trades) - len(winning_trades),
            "trades": trades
        }
