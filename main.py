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
from pathlib import Path
from dotenv import load_dotenv

# Import modules locaux
from src.blockscout_client import BlockscoutClient
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


def run_backtest(config: dict, args: argparse.Namespace) -> None:
    """
    Exécute un backtest de la stratégie.
    
    Args:
        config: Configuration du bot
        args: Arguments ligne de commande
    """
    logger.info("📊 Démarrage du backtest...")
    logger.info(f"Période: {args.period}")
    
    # Initialize strategy
    strategy_config = config['strategies']['dca']
    strategy = DCAStrategy(strategy_config)
    
    # TODO: Charger données historiques via ccxt
    # TODO: Exécuter backtest
    # TODO: Afficher résultats
    
    logger.info("✅ Backtest terminé")
    logger.info("\n=== Résultats (TODO) ===")
    logger.info("Profit: N/A")
    logger.info("Win rate: N/A")
    logger.info("Nombre de trades: N/A")


def run_live(config: dict, args: argparse.Namespace) -> None:
    """
    Exécute le bot en mode live (testnet).
    
    Args:
        config: Configuration du bot
        args: Arguments ligne de commande
    """
    logger.info("🚀 Démarrage du bot en mode LIVE (testnet)")
    
    # Vérifier qu'on est bien en testnet
    if not config['exchanges']['binance']['testnet']:
        logger.error("⚠️  DANGER: Mode live sans testnet activé!")
        response = input("Continuer en PRODUCTION ? (yes/no): ")
        if response.lower() != 'yes':
            sys.exit(1)
    
    # Initialize clients
    blockscout = BlockscoutClient(config['blockscout']['default_chain_id'])
    strategy = DCAStrategy(config['strategies']['dca'])
    
    # TODO: Implémenter boucle de trading live
    logger.info("⏸️  Bot arrêté (implémentation en cours)")


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
        print(f"❌ Erreur: {e}")
        sys.exit(1)
    
    # Setup logging
    if args.debug:
        config['logging']['level'] = 'DEBUG'
    setup_logging(config)
    
    # Banner
    logger.info("="*60)
    logger.info("🤖 BOT TRADING CRYPTO v0.1.0")
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
        logger.info("\n⏹️  Bot arrêté par l'utilisateur")
    except Exception as e:
        logger.exception(f"❌ Erreur fatale: {e}")
        sys.exit(1)
    
    logger.info("🏁 Bot terminé")


if __name__ == "__main__":
    main()
