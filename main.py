#!/usr/bin/env python3
"""
Bot Trading Crypto - Main entry point.

Usage:
    python main.py --mode backtest
    python main.py --mode live
    python main.py --mode backtest --pair BTC/USDT --period 30d
"""
import argparse
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Import modules locaux
from src.executor import BinanceExecutor
from src.strategy import DCAStrategy
from src.utils import setup_logging, load_config

logger = logging.getLogger(__name__)


def parse_args():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Bot Trading Crypto - Apprentissage et profit avec 5€/mois",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--mode',
        choices=['backtest', 'live', 'paper'],
        default='backtest',
        help='Mode d\'exécution du bot'
    )

    parser.add_argument(
        '--pair',
        type=str,
        help='Paire de trading (ex: BTC/USDT)'
    )

    parser.add_argument(
        '--period',
        type=str,
        default='30d',
        help='Période pour backtest (ex: 30d, 6m, 1y)'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Chemin vers fichier de configuration'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Active le mode debug'
    )

    return parser.parse_args()


def parse_period(period_str: str) -> int:
    """
    Convertit période string en nombre de bougies.

    Args:
        period_str: '30d', '6m', '1y'

    Returns:
        Nombre de bougies (pour 1h timeframe)
    """
    unit = period_str[-1]
    value = int(period_str[:-1])

    if unit == 'd':
        return value * 24  # jours -> heures
    elif unit == 'm':
        return value * 30 * 24  # mois -> heures
    elif unit == 'y':
        return value * 365 * 24  # années -> heures
    else:
        return 720  # défaut 30 jours


def run_backtest(config: dict, args: argparse.Namespace) -> None:
    """
    Exécute un backtest de la stratégie.

    Args:
        config: Configuration du bot
        args: Arguments ligne de commande
    """
    logger.info("="*60)
    logger.info("DEMARRAGE DU BACKTEST")
    logger.info(f"Période: {args.period}")
    logger.info("="*60)

    # Initialize strategy
    strategy_config = config['strategies']['dca']
    strategy = DCAStrategy(strategy_config)

    # Determine pair
    pair = args.pair or strategy_config['pairs'][0]
    logger.info(f"Paire: {pair}")

    # Initialize executor (sans clés API pour backtest)
    try:
        api_key = os.getenv('BINANCE_API_KEY', 'dummy_key')
        api_secret = os.getenv('BINANCE_API_SECRET', 'dummy_secret')
        executor = BinanceExecutor(api_key, api_secret, testnet=True)

        # Charger données historiques
        limit = parse_period(args.period)
        logger.info(f"Chargement {limit} bougies 1h pour {pair}...")

        ohlcv_data = executor.fetch_ohlcv(pair, '1h', min(limit, 1000))
        logger.info(f"Données chargées: {len(ohlcv_data)} bougies")

        # Exécuter backtest
        initial_capital = config['trading']['capital_initial']
        results = strategy.backtest(ohlcv_data, initial_capital)

        # Afficher résultats
        logger.info("\n" + "="*60)
        logger.info("RESULTATS BACKTEST - REALISTE (avec frais & slippage)")
        logger.info("="*60)
        logger.info(f"Capital initial: {results['initial_capital']:.2f} EUR")
        logger.info(f"Capital final: {results['final_capital']:.2f} EUR")
        logger.info(f"Profit net: {results['profit_percent']:+.2f}%")
        logger.info(f"Total frais payés: {results['total_fees']:.4f} EUR")
        logger.info("")
        logger.info(f"Nombre de trades: {results['num_trades']} ({results['num_buy']} BUY, {results['num_sell']} SELL)")
        logger.info(f"Win rate: {results['win_rate']:.1f}% ({results['winning_trades']} gagnants, {results['losing_trades']} perdants)")
        logger.info("")
        logger.info("=== METRIQUES AVANCEES ===")
        logger.info(f"Espérance de gain (EV): {results['expected_value']:+.4f} EUR/trade")
        logger.info(f"Gain moyen (winners): {results['avg_win']:+.4f} EUR")
        logger.info(f"Perte moyenne (losers): {results['avg_loss']:+.4f} EUR")
        logger.info(f"Max Drawdown: {results['max_drawdown']:.2f}%")
        logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        logger.info("="*60)
        
        # Interprétation
        logger.info("")
        logger.info("=== INTERPRETATION ===")
        if results['expected_value'] > 0:
            logger.info("[+] EV positif: stratégie mathématiquement rentable")
        else:
            logger.warning("[-] EV négatif: stratégie perdante à long terme")
        
        if results['sharpe_ratio'] > 1:
            logger.info("[+] Sharpe > 1: bon ratio rendement/risque")
        elif results['sharpe_ratio'] > 0:
            logger.warning("[~] Sharpe entre 0-1: risque modéré")
        else:
            logger.error("[-] Sharpe négatif: trop risqué")
        
        if abs(results['max_drawdown']) < 5:
            logger.info("[+] Drawdown < 5%: risque contrôlé")
        elif abs(results['max_drawdown']) < 10:
            logger.warning("[~] Drawdown 5-10%: risque acceptable")
        else:
            logger.error(f"[-] Drawdown > 10%: DANGER ({results['max_drawdown']:.1f}%)")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"Erreur backtest: {e}")
        logger.exception("Détails:")
        sys.exit(1)


def run_live(config: dict, args: argparse.Namespace) -> None:
    """
    Exécute le bot en mode live (testnet).

    Args:
        config: Configuration du bot
        args: Arguments ligne de commande
    """
    logger.info("DEMARRAGE DU BOT EN MODE LIVE (testnet)")

    # Vérifier qu'on est bien en testnet
    if not config['exchanges']['binance']['testnet']:
        logger.error("DANGER: Mode live sans testnet activé!")
        response = input("Continuer en PRODUCTION ? (yes/no): ")
        if response.lower() != 'yes':
            sys.exit(1)

    # TODO: Implémentation boucle trading live
    logger.info("Bot arrêté (implémentation en cours)")


def main():
    """Fonction principale."""
    # Load environment variables
    load_dotenv()

    # Parse arguments
    args = parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Erreur: {e}")
        sys.exit(1)

    # Setup logging
    if args.debug:
        config['logging']['level'] = 'DEBUG'
    setup_logging(config)

    # Banner
    logger.info("="*60)
    logger.info("BOT TRADING CRYPTO v0.1.0")
    logger.info(f"Mode: {args.mode.upper()}")
    logger.info("="*60)

    # Route vers mode approprié
    try:
        if args.mode == 'backtest':
            run_backtest(config, args)
        elif args.mode == 'live':
            run_live(config, args)
        elif args.mode == 'paper':
            logger.warning("Mode paper trading pas encore implémenté")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nBot arrêté par l'utilisateur")
    except Exception as e:
        logger.exception(f"Erreur fatale: {e}")
        sys.exit(1)

    logger.info("Bot terminé")


if __name__ == "__main__":
    main()
