#!/usr/bin/env python3
"""
Multi-Pair Strategy Optimizer

Teste automatiquement plusieurs paires de trading et trouve les meilleures combinaisons
de paramètres (RSI, SMA, stop-loss, etc.).

Usage:
    python optimizer.py --period 30d
    python optimizer.py --period 90d --output results.csv
"""
import argparse
import logging
import sys
import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.executor import BinanceExecutor
from src.strategy import DCAStrategy
from src.utils import setup_logging, load_config

logger = logging.getLogger(__name__)

# Paires à tester
TOP_PAIRS = [
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
    'SOL/USDT',
    'MATIC/USDT',
    'AVAX/USDT',
    'LINK/USDT',
    'UNI/USDT',
    'ATOM/USDT',
    'DOT/USDT'
]


def test_pair(
    pair: str,
    executor: BinanceExecutor,
    strategy_config: Dict,
    initial_capital: float,
    limit: int
) -> Dict:
    """
    Teste une paire de trading avec la stratégie.
    
    Args:
        pair: Paire à tester
        executor: Executor Binance
        strategy_config: Config de la stratégie
        initial_capital: Capital initial
        limit: Nombre de bougies
        
    Returns:
        Dict avec résultats du backtest
    """
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing {pair}...")
        logger.info(f"{'='*60}")
        
        # Charger données
        ohlcv_data = executor.fetch_ohlcv(pair, '1h', limit)
        
        if len(ohlcv_data) < 250:
            logger.warning(f"{pair}: Pas assez de données ({len(ohlcv_data)} bougies)")
            return None
        
        # Créer stratégie pour cette paire
        config = strategy_config.copy()
        config['pairs'] = [pair]
        strategy = DCAStrategy(config)
        
        # Backtest
        results = strategy.backtest(ohlcv_data, initial_capital)
        results['pair'] = pair
        
        logger.info(f"{pair}: Profit={results['profit_percent']:+.2f}%, WinRate={results['win_rate']:.1f}%")
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur test {pair}: {e}")
        return None


def optimize_parameters(
    pair: str,
    executor: BinanceExecutor,
    base_config: Dict,
    initial_capital: float,
    limit: int,
    rsi_buy_values: List[int] = [25, 30, 35],
    rsi_sell_values: List[int] = [65, 70, 75]
) -> Dict:
    """
    Optimise les paramètres RSI pour une paire.
    
    Args:
        pair: Paire à optimiser
        executor: Executor
        base_config: Config de base
        initial_capital: Capital
        limit: Bougies
        rsi_buy_values: Seuils RSI achat à tester
        rsi_sell_values: Seuils RSI vente à tester
        
    Returns:
        Meilleurs paramètres trouvés
    """
    logger.info(f"\nOptimisation paramètres pour {pair}...")
    
    try:
        ohlcv_data = executor.fetch_ohlcv(pair, '1h', limit)
        
        if len(ohlcv_data) < 250:
            logger.warning(f"{pair}: Pas assez de données")
            return None
        
        best_result = None
        best_sharpe = -999
        
        # Tester toutes combinaisons
        for rsi_buy in rsi_buy_values:
            for rsi_sell in rsi_sell_values:
                if rsi_sell <= rsi_buy:
                    continue
                
                config = base_config.copy()
                config['pairs'] = [pair]
                config['buy_threshold_rsi'] = rsi_buy
                config['sell_threshold_rsi'] = rsi_sell
                
                strategy = DCAStrategy(config)
                results = strategy.backtest(ohlcv_data, initial_capital)
                
                # Optimiser sur Sharpe ratio (meilleur indicateur risque/rendement)
                if results['sharpe_ratio'] > best_sharpe:
                    best_sharpe = results['sharpe_ratio']
                    best_result = results.copy()
                    best_result['rsi_buy'] = rsi_buy
                    best_result['rsi_sell'] = rsi_sell
                    best_result['pair'] = pair
        
        if best_result:
            logger.info(
                f"{pair}: Best config RSI({best_result['rsi_buy']}/{best_result['rsi_sell']}) "
                f"-> Sharpe={best_sharpe:.2f}, Profit={best_result['profit_percent']:+.2f}%"
            )
        
        return best_result
        
    except Exception as e:
        logger.error(f"Erreur optimisation {pair}: {e}")
        return None


def main():
    """Fonction principale."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Multi-Pair Strategy Optimizer")
    parser.add_argument('--period', type=str, default='30d', help='Période de test')
    parser.add_argument('--output', type=str, default='optimization_results.csv', help='Fichier output')
    parser.add_argument('--optimize', action='store_true', help='Optimiser paramètres RSI')
    parser.add_argument('--pairs', type=str, nargs='+', help='Paires spécifiques à tester')
    args = parser.parse_args()
    
    # Load env et config
    load_dotenv()
    config = load_config('config.yaml')
    setup_logging(config)
    
    logger.info("="*60)
    logger.info("MULTI-PAIR STRATEGY OPTIMIZER")
    logger.info(f"Période: {args.period}")
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
        limit = 720
    limit = min(limit, 1000)
    
    # Paires à tester
    pairs_to_test = args.pairs if args.pairs else TOP_PAIRS
    logger.info(f"Testing {len(pairs_to_test)} paires: {', '.join(pairs_to_test)}")
    
    # Strategy config
    strategy_config = config['strategies']['dca']
    initial_capital = config['trading']['capital_initial']
    
    # Tester paires
    results = []
    
    if args.optimize:
        logger.info("\nMode OPTIMIZATION activé (recherche meilleurs paramètres)...\n")
        for pair in pairs_to_test:
            result = optimize_parameters(
                pair, executor, strategy_config, initial_capital, limit
            )
            if result:
                results.append(result)
            time.sleep(0.5)  # Rate limit
    else:
        logger.info("\nMode TEST STANDARD (paramètres config.yaml)...\n")
        for pair in pairs_to_test:
            result = test_pair(
                pair, executor, strategy_config, initial_capital, limit
            )
            if result:
                results.append(result)
            time.sleep(0.5)  # Rate limit
    
    # Créer DataFrame
    if not results:
        logger.error("Aucun résultat valide !")
        sys.exit(1)
    
    df = pd.DataFrame(results)
    
    # Trier par Sharpe ratio (meilleur indicateur)
    df = df.sort_values('sharpe_ratio', ascending=False)
    
    # Afficher résultats
    logger.info("\n" + "="*80)
    logger.info("RESULTATS FINAUX (triés par Sharpe Ratio)")
    logger.info("="*80)
    
    # Colonnes importantes
    display_cols = [
        'pair', 'profit_percent', 'win_rate', 'sharpe_ratio', 
        'max_drawdown', 'num_trades', 'expected_value',
        'stop_loss_triggered', 'trailing_stop_triggered'
    ]
    
    if args.optimize:
        display_cols.insert(1, 'rsi_buy')
        display_cols.insert(2, 'rsi_sell')
    
    print("\n")
    print(df[display_cols].to_string(index=False))
    print("\n")
    
    # Top 3
    logger.info("="*60)
    logger.info("TOP 3 PAIRES RECOMMANDEES")
    logger.info("="*60)
    
    for i, row in df.head(3).iterrows():
        logger.info(f"\n#{df.index.get_loc(i)+1}: {row['pair']}")
        if args.optimize:
            logger.info(f"  Config: RSI buy<{row['rsi_buy']}, sell>{row['rsi_sell']}")
        logger.info(f"  Profit: {row['profit_percent']:+.2f}%")
        logger.info(f"  Win Rate: {row['win_rate']:.1f}%")
        logger.info(f"  Sharpe: {row['sharpe_ratio']:.2f}")
        logger.info(f"  Max DD: {row['max_drawdown']:.2f}%")
        logger.info(f"  EV: {row['expected_value']:+.4f} EUR/trade")
    
    # Sauvegarder CSV
    output_path = Path(args.output)
    df.to_csv(output_path, index=False)
    logger.info(f"\nRésultats sauvegardés: {output_path.absolute()}")
    
    # Recommandations
    logger.info("\n" + "="*60)
    logger.info("RECOMMANDATIONS")
    logger.info("="*60)
    
    positive_pairs = df[df['profit_percent'] > 0]
    negative_pairs = df[df['profit_percent'] <= 0]
    
    logger.info(f"\nPaires RENTABLES: {len(positive_pairs)}/{len(df)}")
    if len(positive_pairs) > 0:
        logger.info(f"Profit moyen: {positive_pairs['profit_percent'].mean():+.2f}%")
        logger.info(f"Best: {positive_pairs.iloc[0]['pair']} ({positive_pairs.iloc[0]['profit_percent']:+.2f}%)")
    
    if len(negative_pairs) > 0:
        logger.warning(f"\nPaires PERDANTES: {len(negative_pairs)} - À ÉVITER")
        for _, row in negative_pairs.iterrows():
            logger.warning(f"  - {row['pair']}: {row['profit_percent']:.2f}%")
    
    logger.info("\n" + "="*60)
    logger.info("Optimizer terminé")
    logger.info("="*60)


if __name__ == "__main__":
    main()
