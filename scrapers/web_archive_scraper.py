"""
Scraper pour Internet Archive (Wayback Machine).
Source légale : Archive publique d'Internet.
"""

import requests
import time
import re
from typing import Set
import logging

from config import DELAY_BETWEEN_REQUESTS, TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class WebArchiveScraper:
    """
    Scraper pour Internet Archive (Wayback Machine).
    Recherche des snapshots de sites Shopify.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
    
    def _search_wayback(self, domain_pattern: str, max_results: int = 1000) -> Set[str]:
        """
        Recherche dans Wayback Machine.
        
        Args:
            domain_pattern: Pattern de domaine à rechercher
            max_results: Nombre maximum de résultats
        
        Returns:
            Set d'URLs trouvées
        """
        shopify_urls = set()
        
        try:
            # API CDX de Wayback Machine
            # Recherche les snapshots de domaines myshopify.com
            api_url = "http://web.archive.org/cdx/search/cdx"
            params = {
                'url': domain_pattern,
                'output': 'json',
                'limit': min(max_results, 10000),
            }
            
            logger.info(f"Recherche Wayback Machine: {domain_pattern}")
            response = self.session.get(api_url, params=params, timeout=TIMEOUT * 2)
            
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:  # Première ligne = headers
                    logger.info(f"  → {len(data) - 1} snapshots trouvés")
                    
                    # Extraire les domaines uniques
                    domains = set()
                    for row in data[1:]:  # Skip header
                        if len(row) > 2:
                            url = row[2]  # URL dans la colonne 2
                            # Extraire le domaine myshopify.com
                            match = re.search(r'([a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.myshopify\.com', url)
                            if match:
                                domain = match.group(1).lower()
                                if domain and domain not in ['www', 'admin', 'cdn', 'login', 'api']:
                                    domains.add(f"{domain}.myshopify.com")
                    
                    # Convertir en URLs
                    for domain in domains:
                        shopify_urls.add(f"https://{domain}")
                    
                    logger.info(f"  → {len(shopify_urls)} URLs Shopify extraites")
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            logger.warning(f"Erreur lors de la recherche Wayback: {e}")
        
        return shopify_urls
    
    def scrape(self) -> Set[str]:
        """
        Scrape Internet Archive pour trouver des URLs Shopify.
        
        Returns:
            Set d'URLs Shopify trouvées
        """
        logger.info("Début du scraping Internet Archive (Wayback Machine)")
        
        all_urls = set()
        
        # Rechercher différents patterns
        patterns = [
            '*.myshopify.com',
            'myshopify.com/*',
        ]
        
        for pattern in patterns:
            try:
                urls = self._search_wayback(pattern, max_results=5000)
                new_urls = urls - all_urls
                all_urls.update(urls)
                logger.info(f"  → {len(new_urls)} nouvelles URLs (total: {len(all_urls)})")
            except Exception as e:
                logger.warning(f"Erreur pour le pattern '{pattern}': {e}")
        
        logger.info(f"✓ Internet Archive: {len(all_urls)} URLs trouvées")
        return all_urls



