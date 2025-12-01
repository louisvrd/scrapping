"""
Détection des sites Shopify.
"""

import re
import requests
from typing import Set, Optional
from urllib.parse import urlparse
import logging

from config import SHOPIFY_PATTERNS, DEEP_VERIFICATION, TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class ShopifyDetector:
    """Détecte si une URL est un site Shopify."""
    
    def __init__(self):
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in SHOPIFY_PATTERNS]
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
    
    def is_shopify_url(self, url: str) -> bool:
        """
        Vérifie rapidement si une URL est Shopify (sans requête HTTP).
        
        Args:
            url: URL à vérifier
        
        Returns:
            True si l'URL semble être Shopify
        """
        # Vérifier si c'est un domaine myshopify.com
        if '.myshopify.com' in url.lower():
            return True
        
        # Vérifier les patterns dans l'URL
        for pattern in self.compiled_patterns:
            if pattern.search(url):
                return True
        
        return False
    
    def is_shopify_site(self, url: str, check_content: bool = None) -> bool:
        """
        Vérifie si un site est Shopify (avec vérification du contenu si nécessaire).
        
        Args:
            url: URL à vérifier
            check_content: Forcer la vérification du contenu (None = utiliser DEEP_VERIFICATION)
        
        Returns:
            True si le site est Shopify
        """
        # Vérification rapide d'abord
        if self.is_shopify_url(url):
            return True
        
        # Vérification approfondie si demandée
        if check_content is None:
            check_content = DEEP_VERIFICATION
        
        if check_content:
            return self._check_content(url)
        
        return False
    
    def _check_content(self, url: str) -> bool:
        """
        Vérifie le contenu HTML pour détecter Shopify.
        
        Args:
            url: URL à vérifier
        
        Returns:
            True si Shopify détecté dans le contenu
        """
        try:
            response = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
            if response.status_code != 200:
                return False
            
            html_content = response.text.lower()
            
            # Chercher les patterns Shopify dans le HTML
            for pattern in self.compiled_patterns:
                if pattern.search(html_content):
                    logger.debug(f"Shopify détecté dans le contenu de {url}")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Erreur lors de la vérification du contenu de {url}: {e}")
            return False
    
    def extract_shopify_domains(self, text: str) -> Set[str]:
        """
        Extrait tous les domaines Shopify d'un texte.
        
        Args:
            text: Texte à analyser
        
        Returns:
            Set de domaines Shopify trouvés
        """
        domains = set()
        
        # Pattern pour extraire les domaines myshopify.com
        pattern = r'([a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.myshopify\.com'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        for match in matches:
            if match and len(match) > 1:
                domain = match.lower().strip()
                # Filtrer les sous-domaines invalides
                if domain not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store']:
                    domains.add(f"{domain}.myshopify.com")
        
        return domains

