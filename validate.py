#!/usr/bin/env python3
"""
Out-of-Sample Validator

Valide la stratégie sur données jamais vues pour éviter l'overfitting.

Méthode:
- Split data: 60% training, 40% test
- Optimise paramètres sur training
- Valide sur test (données jamais vues)
- Si test résultats << training résultats -> overfitting

Usage:
    python validate.py --pair BTC/USDT --period 180d
"""
import argparse
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import numpy as np

from src.executor import BinanceExecutor
from src.strategy import DCAStrategy
from src.utils import setup_logging, load_config

logger = logging.getLogger(__name__)


def split_data(df: pd.DataFrame, train_pct: float = 0.6):
    """
    Split data en training et test sets.
    
    Args:
        df: DataFrame OHLCV
        train_pct: Pourcentage pour training (0.6 = 60%)
        
    Returns:
        train_df, test_df
    """
    split_idx = int(len(df) * train_pct)
    train = df.iloc[:split_idx].copy()
    test = df.iloc[split_idx:].copy()
    
    return train, test


def optimize_on_train(
    train_data: pd.DataFrame,
    config: dict,
    initial_capital: float
) -> dict:
    """
    Optimise paramètres sur training set.
    
    Args:
        train_data: Données d'entraînement
        config: Config de base
        initial_capital: Capital
        
    Returns:
        Meilleurs paramètres trouvés
    """
    logger.info("\nOptimisation sur TRAINING SET...")
    
    best_config = None
    best_sharpe = -999
    
    # Grille de recherche
    rsi_buy_values = [25, 30, 35, 40]
    rsi_sell_values = [60, 65, 70, 75]
    
    for rsi_buy in rsi_buy_values:
        for rsi_sell in rsi_sell_values:
            if rsi_sell <= rsi_buy:
                continue
            
            test_config = config.copy()
            test_config['buy_threshold_rsi'] = rsi_buy
            test_config['sell_threshold_rsi'] = rsi_sell
            
            strategy = DCAStrategy(test_config)
            results = strategy.backtest(train_data, initial_capital)
            
            if results['sharpe_ratio'] > best_sharpe:
                best_sharpe = results['sharpe_ratio']
                best_config = test_config.copy()
                best_config['train_results'] = results
    
    logger.info(
        f"Meilleurs paramètres: RSI buy<{best_config['buy_threshold_rsi']}, "
        f"sell>{best_config['sell_threshold_rsi']}")
    logger.info(f"Training Sharpe: {best_sharpe:.2f}")
    logger.info(f"Training Profit: {best_config['train_results']['profit_percent']:+.2f}%")
    
    return best_config


def validate_on_test(
    test_data: pd.DataFrame,
    optimized_config: dict,
    initial_capital: float
) -> dict:
    """
    Valide les paramètres optimisés sur test set (jamais vu).
    
    Args:
        test_data: Données de test
        optimized_config: Config optimisée sur train
        initial_capital: Capital
        
    Returns:
        Résultats sur test set
    """
    logger.info("\nValidation sur TEST SET (données jamais vues)...")
    
    strategy = DCAStrategy(optimized_config)
    test_results = strategy.backtest(test_data, initial_capital)
    
    logger.info(f"Test Sharpe: {test_results['sharpe_ratio']:.2f}")
    logger.info(f"Test Profit: {test_results['profit_percent']:+.2f}%")
    
    return test_results


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Out-of-Sample Validator")
    parser.add_argument('--pair', type=str, default='BTC/USDT', help='Paire de trading')
    parser.add_argument('--period', type=str, default='180d', help='Période totale (minimum 180d)')
    parser.add_argument('--train-pct', type=float, default=0.6, help='% pour training (0.6 = 60%)')
    args = parser.parse_args()
    
    # Load env et config
    load_dotenv()
    config = load_config('config.yaml')
    setup_logging(config)
    
    logger.info("="*60)
    logger.info("OUT-OF-SAMPLE VALIDATION")
    logger.info(f"Paire: {args.pair}")
    logger.info(f"Période: {args.period}")
    logger.info(f"Split: {args.train_pct*100:.0f}% train / {(1-args.train_pct)*100:.0f}% test")
    logger.info("="*60)
    
    # Initialize executor
    api_key = os.getenv('BINANCE_API_KEY', 'dummy_key')
    api_secret = os.getenv('BINANCE_API_SECRET', 'dummy_secret')
    executor = BinanceExecutor(api_key, api_secret, testnet=True)
    
    # Parse period
    unit = args.period[-1]
    value = int(args.period[:-1])
    if unit == 'd':
        limit = value * 24
    elif unit == 'm':
        limit = value * 30 * 24
    else:
        limit = 1000
    limit = min(limit, 1000)
    
    # Charger données
    logger.info(f"\nChargement {limit} bougies pour {args.pair}...")
    ohlcv_data = executor.fetch_ohlcv(args.pair, '1h', limit)
    logger.info(f"Données chargées: {len(ohlcv_data)} bougies")
    
    if len(ohlcv_data) < 500:
        logger.error("Pas assez de données pour validation robuste (min 500 bougies)")
        sys.exit(1)
    
    # Split data
    train_data, test_data = split_data(ohlcv_data, args.train_pct)
    logger.info(f"\nSplit: {len(train_data)} train, {len(test_data)} test")
    logger.info(
        f"Training période: {train_data['timestamp'].iloc[0]} -> {train_data['timestamp'].iloc[-1]}"
    )
    logger.info(
        f"Test période: {test_data['timestamp'].iloc[0]} -> {test_data['timestamp'].iloc[-1]}"
    )
    
    # Strategy config
    strategy_config = config['strategies']['dca'].copy()
    strategy_config['pairs'] = [args.pair]
    initial_capital = config['trading']['capital_initial']
    
    # 1. Optimiser sur training
    optimized_config = optimize_on_train(train_data, strategy_config, initial_capital)
    train_results = optimized_config['train_results']
    
    # 2. Valider sur test
    test_results = validate_on_test(test_data, optimized_config, initial_capital)
    
    # 3. Comparer résultats
    logger.info("\n" + "="*60)
    logger.info("COMPARAISON TRAIN vs TEST")
    logger.info("="*60)
    
    metrics = [
        ('Profit %', 'profit_percent'),
        ('Win Rate %', 'win_rate'),
        ('Sharpe Ratio', 'sharpe_ratio'),
        ('Max Drawdown %', 'max_drawdown'),
        ('Expected Value', 'expected_value'),
        ('Trades', 'num_trades')
    ]
    
    print(f"\n{'Metric':<20} {'Training':<15} {'Test':<15} {'Diff':<15}")
    print("="*65)
    
    for metric_name, metric_key in metrics:
        train_val = train_results[metric_key]
        test_val = test_results[metric_key]
        diff = test_val - train_val
        
        if metric_key in ['profit_percent', 'win_rate', 'max_drawdown']:
            print(f"{metric_name:<20} {train_val:>13.2f}  {test_val:>13.2f}  {diff:>+13.2f}")
        elif metric_key == 'expected_value':
            print(f"{metric_name:<20} {train_val:>13.4f}  {test_val:>13.4f}  {diff:>+13.4f}")
        elif metric_key == 'sharpe_ratio':
            print(f"{metric_name:<20} {train_val:>13.2f}  {test_val:>13.2f}  {diff:>+13.2f}")
        else:
            print(f"{metric_name:<20} {train_val:>13.0f}  {test_val:>13.0f}  {diff:>+13.0f}")
    
    print("="*65)
    
    # 4. Détecter overfitting
    logger.info("\n" + "="*60)
    logger.info("ANALYSE OVERFITTING")
    logger.info("="*60)
    
    profit_degradation = test_results['profit_percent'] - train_results['profit_percent']
    sharpe_degradation = test_results['sharpe_ratio'] - train_results['sharpe_ratio']
    
    if profit_degradation < -5:
        logger.error(
            f"[OVERFITTING DÉTECTÉ] Profit dégrade de {profit_degradation:.2f}% sur test"
        )
        logger.error("-> Stratégie trop ajustée aux données d'entraînement")
    elif profit_degradation < -2:
        logger.warning(
            f"[OVERFITTING MODÉRÉ] Profit dégrade de {profit_degradation:.2f}% sur test"
        )
    else:
        logger.info(
            f"[OK] Performance test proche du train ({profit_degradation:+.2f}%)"
        )
    
    if sharpe_degradation < -0.5:
        logger.warning(
            f"[ATTENTION] Sharpe dégrade de {sharpe_degradation:.2f} sur test"
        )
    else:
        logger.info(f"[OK] Sharpe stable ({sharpe_degradation:+.2f})")
    
    # 5. Recommandation finale
    logger.info("\n" + "="*60)
    logger.info("RECOMMANDATION FINALE")
    logger.info("="*60)
    
    if test_results['profit_percent'] > 0 and test_results['sharpe_ratio'] > 0.5:
        logger.info("[+] STRATÉGIE VALIDÉE")
        logger.info(f"    Config recommandée: RSI buy<{optimized_config['buy_threshold_rsi']}, sell>{optimized_config['sell_threshold_rsi']}")
        logger.info(f"    Performance attendue: {test_results['profit_percent']:+.2f}% avec Sharpe {test_results['sharpe_ratio']:.2f}")
        logger.info("    -> Prêt pour live testnet")
    else:
        logger.error("[-] STRATÉGIE NON VALIDÉE")
        logger.error("    Performance test insuffisante")
        logger.error("    -> NE PAS utiliser en live")
        logger.error("    -> Essayer autre période ou autre paire")
    
    logger.info("\n" + "="*60)


if __name__ == "__main__":
    main()
