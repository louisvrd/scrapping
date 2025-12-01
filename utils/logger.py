"""
Module de logging pour le scraper Shopify.
"""

import logging
import sys
from pathlib import Path
from config import LOG_LEVEL, LOG_FILE, LOG_FORMAT


def setup_logger(name: str = 'shopify_scraper', log_file: Path = None) -> logging.Logger:
    """
    Configure et retourne un logger.
    
    Args:
        name: Nom du logger
        log_file: Chemin du fichier de log (optionnel)
    
    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # Éviter les doublons de handlers
    if logger.handlers:
        return logger
    
    # Format des logs
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Handler pour la console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler pour le fichier
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    elif LOG_FILE:
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

