"""
Utilitaires pour le bot trading.
"""
import logging
import yaml
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Configure le système de logging.
    
    Args:
        config: Configuration contenant level, file, console
    """
    log_config = config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO'))
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler console
    if log_config.get('console', True):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logging.root.addHandler(console_handler)
    
    # Handler fichier
    if 'file' in log_config:
        log_file = Path(log_config['file'])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logging.root.addHandler(file_handler)
    
    logging.root.setLevel(level)
    logging.info(f"Logging configuré: level={log_config.get('level')}")


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    """
    Charge la configuration depuis YAML.
    
    Args:
        path: Chemin vers fichier config
        
    Returns:
        Dict de configuration
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    logging.info(f"Configuration chargée depuis {path}")
    return config


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Formate un montant en devise.
    
    Args:
        amount: Montant numérique
        currency: Code devise (USD, EUR, etc.)
        
    Returns:
        String formatée
    """
    symbol = {"USD": "$", "EUR": "€", "USDT": "$"}.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def calculate_position_size(capital: float, risk_percent: float, 
                           entry_price: float, stop_loss_price: float) -> float:
    """
    Calcule la taille de position basée sur le risk management.
    
    Args:
        capital: Capital total disponible
        risk_percent: % de capital à risquer (ex: 0.02 = 2%)
        entry_price: Prix d'entrée
        stop_loss_price: Prix du stop loss
        
    Returns:
        Quantité à acheter
    """
    risk_amount = capital * risk_percent
    price_diff = abs(entry_price - stop_loss_price)
    
    if price_diff == 0:
        return 0
    
    quantity = risk_amount / price_diff
    return quantity


def timestamp_to_datetime(timestamp: int) -> datetime:
    """
    Convertit timestamp Unix en datetime.
    
    Args:
        timestamp: Timestamp en millisecondes
        
    Returns:
        Objet datetime
    """
    return datetime.fromtimestamp(timestamp / 1000)
