"""
Scraper pour les listes publiques de sites Shopify.
Scrape des sources publiques légales comme des forums, blogs, etc.
"""

import requests
import time
import re
from typing import Set, List
import logging
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from config import DELAY_BETWEEN_REQUESTS, TIMEOUT, USER_AGENT
from utils.shopify_detector import ShopifyDetector

logger = logging.getLogger(__name__)


class PublicListsScraper:
    """
    Scraper pour trouver des URLs Shopify dans des listes publiques.
    """
    
    def __init__(self):
        self.shopify_detector = ShopifyDetector()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
    
    def _extract_shopify_urls_from_text(self, text: str) -> Set[str]:
        """
        Extrait toutes les URLs Shopify d'un texte.
        
        Args:
            text: Texte à analyser
        
        Returns:
            Set d'URLs Shopify
        """
        urls = set()
        
        # Pattern pour trouver les URLs myshopify.com
        patterns = [
            r'https?://([a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.myshopify\.com[^\s\)]*',
            r'([a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.myshopify\.com',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match and match.lower() not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store']:
                    urls.add(f"https://{match.lower()}.myshopify.com")
        
        return urls
    
    def _scrape_url(self, url: str) -> Set[str]:
        """
        Scrape une URL pour trouver des URLs Shopify.
        
        Args:
            url: URL à scraper
        
        Returns:
            Set d'URLs Shopify trouvées
        """
        shopify_urls = set()
        
        try:
            response = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
            if response.status_code != 200:
                return shopify_urls
            
            # Extraire depuis le HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraire depuis tous les liens
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href and '.myshopify.com' in href.lower():
                    absolute_url = urljoin(url, href)
                    if self.shopify_detector.is_shopify_url(absolute_url):
                        shopify_urls.add(absolute_url)
            
            # Extraire depuis le texte
            text_urls = self._extract_shopify_urls_from_text(response.text)
            shopify_urls.update(text_urls)
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            logger.debug(f"Erreur lors du scraping de {url}: {e}")
        
        return shopify_urls
    
    def scrape(self) -> Set[str]:
        """
        Scrape plusieurs sources publiques pour trouver des URLs Shopify.
        
        Returns:
            Set d'URLs Shopify trouvées
        """
        logger.info("Début du scraping de listes publiques")
        
        all_urls = set()
        
        # Sources publiques potentielles (à adapter selon vos besoins)
        # Note: Ces URLs doivent être publiques et accessibles
        public_sources = [
            # Exemples de sources (remplacer par des sources réelles)
            # 'https://example.com/shopify-stores',
            # 'https://another-site.com/listings',
        ]
        
        # Si aucune source n'est configurée, on cherche dans des endroits communs
        if not public_sources:
            logger.info("Aucune source publique configurée - recherche dans des emplacements communs")
            # Vous pouvez ajouter ici des recherches dans des forums, blogs, etc.
        
        for source_url in public_sources:
            try:
                logger.info(f"Scraping: {source_url}")
                urls = self._scrape_url(source_url)
                new_urls = urls - all_urls
                all_urls.update(urls)
                logger.info(f"  → {len(new_urls)} nouvelles URLs (total: {len(all_urls)})")
            except Exception as e:
                logger.warning(f"Erreur pour {source_url}: {e}")
        
        logger.info(f"✓ Listes publiques: {len(all_urls)} URLs trouvées")
        return all_urls

