"""
Stratégies de trading - Version 1: DCA optimisé.
"""
import pandas as pd
import numpy as np
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
        
        # NOUVEAU: Simulation réaliste
        self.maker_fee = config.get('maker_fee', 0.001)  # 0.1% Binance
        self.taker_fee = config.get('taker_fee', 0.001)  # 0.1% Binance
        self.slippage = config.get('slippage', 0.0005)  # 0.05% slippage moyen

        logger.info(
            f"DCA Strategy init: RSI buy<{self.rsi_buy}, sell>{self.rsi_sell}, "
            f"SMA{self.sma_period}, pairs={self.pairs}, fees={self.taker_fee*100:.2f}%, "
            f"slippage={self.slippage*100:.3f}%"
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
    
    def calculate_ema(self, prices: pd.Series, period: int) -> float:
        """
        Calcule la moyenne mobile exponentielle (EMA).
        
        Args:
            prices: Série de prix
            period: Période (ex: 200 pour EMA200)
            
        Returns:
            Valeur EMA actuelle
        """
        if len(prices) < period:
            return prices.mean()
        return prices.ewm(span=period, adjust=False).mean().iloc[-1]

    def generate_signal(self, ohlcv_data: pd.DataFrame) -> Literal["BUY", "SELL", "HOLD"]:
        """
        Génère un signal de trading basé sur RSI, SMA et EMA200 (filtre macro).

        Logique:
        - BUY: RSI < seuil_achat ET prix < SMA ET prix > EMA200 (tendance haussière globale)
        - SELL: RSI > seuil_vente (surachat)
        - HOLD: sinon

        Args:
            ohlcv_data: DataFrame avec colonnes [timestamp, open, high, low, close, volume]

        Returns:
            Signal "BUY", "SELL" ou "HOLD"
        """
        if len(ohlcv_data) < max(self.sma_period, 200):
            logger.warning(f"Pas assez de données: {len(ohlcv_data)} bougies")
            return "HOLD"

        close_prices = ohlcv_data['close']

        # Calcul indicateurs
        rsi = self.calculate_rsi(close_prices)
        sma = self.calculate_sma(close_prices, self.sma_period)
        ema200 = self.calculate_ema(close_prices, 200)
        current_price = close_prices.iloc[-1]

        logger.debug(
            f"Indicateurs: RSI={rsi:.2f}, Prix={current_price:.2f}, "
            f"SMA{self.sma_period}={sma:.2f}, EMA200={ema200:.2f}"
        )

        # NOUVEAU: Filtre de régime macro (EMA200)
        trend_bullish = current_price > ema200

        # Génération signal
        if rsi < self.rsi_buy and current_price < sma and trend_bullish:
            logger.debug(
                f"Signal BUY: RSI={rsi:.2f}<{self.rsi_buy}, Prix<SMA, Trend bullish"
            )
            return "BUY"
        elif rsi > self.rsi_sell:
            logger.debug(f"Signal SELL: RSI={rsi:.2f}>{self.rsi_sell}")
            return "SELL"
        else:
            logger.debug("Signal HOLD: conditions non remplies")
            return "HOLD"

    def backtest(self, historical_data: pd.DataFrame, initial_capital: float = 100.0) -> Dict:
        """
        Backteste la stratégie sur données historiques avec frais et slippage.

        Args:
            historical_data: DataFrame OHLCV complet
            initial_capital: Capital de départ

        Returns:
            Dict avec résultats: profit, nb_trades, win_rate, Sharpe, Max DD, etc.
        """
        logger.info(f"Backtesting sur {len(historical_data)} bougies...")

        # Variables de suivi
        cash = initial_capital
        position_size = 0.0  # Quantité de crypto détenue
        position_entry_price = 0.0
        trades = []
        in_position = False
        equity_curve = []  # Pour Sharpe et Max Drawdown

        # Parcourir les données historiques
        for i in range(max(self.sma_period, 200) + 20, len(historical_data)):
            # Fenêtre de données pour indicateurs
            window = historical_data.iloc[:i+1]
            current_price = window['close'].iloc[-1]
            current_time = window['timestamp'].iloc[-1]

            # Générer signal
            signal = self.generate_signal(window)

            # Exécuter trade selon signal
            if signal == "BUY" and not in_position and cash > 0:
                # NOUVEAU: Simulation slippage (achète un peu plus cher)
                execution_price = current_price * (1 + self.slippage)
                
                trade_amount = cash * self.trade_amount_percent
                
                # NOUVEAU: Déduire les frais taker (market order)
                fees = trade_amount * self.taker_fee
                trade_amount_after_fees = trade_amount - fees
                
                position_size = trade_amount_after_fees / execution_price
                position_entry_price = execution_price
                cash -= trade_amount
                in_position = True

                logger.info(
                    f"[{current_time}] BUY {position_size:.6f} @ {execution_price:.2f} "
                    f"(slippage: {self.slippage*100:.2f}%, fees: {fees:.4f}, "
                    f"total cost: {trade_amount:.2f})"
                )

                trades.append({
                    'type': 'BUY',
                    'timestamp': current_time,
                    'price': execution_price,
                    'amount': position_size,
                    'cost': trade_amount,
                    'fees': fees
                })

            elif signal == "SELL" and in_position:
                # NOUVEAU: Simulation slippage (vend un peu moins cher)
                execution_price = current_price * (1 - self.slippage)
                
                sell_value_gross = position_size * execution_price
                
                # NOUVEAU: Déduire les frais taker
                fees = sell_value_gross * self.taker_fee
                sell_value_net = sell_value_gross - fees
                
                profit = sell_value_net - (position_size * position_entry_price)
                profit_pct = (profit / (position_size * position_entry_price)) * 100

                cash += sell_value_net

                logger.info(
                    f"[{current_time}] SELL {position_size:.6f} @ {execution_price:.2f} "
                    f"(gross: {sell_value_gross:.2f}, fees: {fees:.4f}, "
                    f"net: {sell_value_net:.2f}, P&L: {profit:.2f} [{profit_pct:+.2f}%])"
                )

                trades.append({
                    'type': 'SELL',
                    'timestamp': current_time,
                    'price': execution_price,
                    'amount': position_size,
                    'revenue': sell_value_net,
                    'fees': fees,
                    'profit': profit,
                    'profit_pct': profit_pct
                })

                position_size = 0.0
                in_position = False
            
            # Tracker equity pour métriques avancées
            current_equity = cash
            if in_position:
                current_equity += position_size * current_price
            equity_curve.append(current_equity)

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
        total_fees = sum(t.get('fees', 0) for t in trades)
        profit_percent = ((final_capital - initial_capital) / initial_capital) * 100
        
        # NOUVEAU: Espérance de gain (EV) par trade
        avg_win = np.mean([t['profit'] for t in winning_trades]) if winning_trades else 0
        losing_trades_list = [t for t in sell_trades if t['profit'] <= 0]
        avg_loss = np.mean([t['profit'] for t in losing_trades_list]) if losing_trades_list else 0
        expected_value = (win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss) if sell_trades else 0
        
        # NOUVEAU: Max Drawdown
        equity_series = pd.Series(equity_curve)
        running_max = equity_series.cummax()
        drawdown = (equity_series - running_max) / running_max
        max_drawdown = drawdown.min() * 100 if len(drawdown) > 0 else 0
        
        # NOUVEAU: Sharpe Ratio (approximation)
        returns = equity_series.pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 1 and returns.std() > 0 else 0

        return {
            "initial_capital": initial_capital,
            "final_capital": final_capital,
            "profit_percent": profit_percent,
            "total_profit": total_profit,
            "total_fees": total_fees,
            "num_trades": len(trades),
            "num_buy": len([t for t in trades if t['type'] == 'BUY']),
            "num_sell": len(sell_trades),
            "win_rate": win_rate,
            "winning_trades": len(winning_trades),
            "losing_trades": len(sell_trades) - len(winning_trades),
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "expected_value": expected_value,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "trades": trades
        }
