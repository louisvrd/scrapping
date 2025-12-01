"""
Scraper alternatif pour Certificate Transparency utilisant d'autres endpoints.
Source légale : APIs publiques de CT logs.
"""

import requests
import time
from typing import Set
import logging
from urllib.parse import quote

from config import DELAY_BETWEEN_REQUESTS, TIMEOUT, USER_AGENT, CT_LOGS_URL

logger = logging.getLogger(__name__)


class CTAlternativeScraper:
    """
    Scraper alternatif pour Certificate Transparency.
    Utilise différentes méthodes pour obtenir plus de résultats.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
    
    def _fetch_with_different_endpoints(self) -> Set[str]:
        """
        Utilise différents endpoints de crt.sh pour obtenir plus de résultats.
        
        Returns:
            Set de domaines trouvés
        """
        all_domains = set()
        
        # Différents endpoints et méthodes
        endpoints = [
            # Méthode 1: Requête directe avec output=json
            f"{CT_LOGS_URL}/?q=%.myshopify.com&output=json",
            # Méthode 2: Avec identité
            f"{CT_LOGS_URL}/?q=%.myshopify.com&output=json",
            # Méthode 3: Recherche par identité (peut retourner plus de résultats)
            f"{CT_LOGS_URL}/?Identity=%.myshopify.com&output=json",
        ]
        
        for endpoint in endpoints:
            try:
                logger.info(f"Tentative avec endpoint: {endpoint[:80]}...")
                response = self.session.get(endpoint, timeout=TIMEOUT * 3)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"  → {len(data)} certificats trouvés")
                
                # Extraire les domaines
                for cert in data:
                    name_value = cert.get('name_value', '')
                    if name_value:
                        for domain in name_value.split('\n'):
                            domain = domain.strip().lower()
                            if domain.endswith('.myshopify.com'):
                                domain = domain.replace('*.', '').replace('www.', '')
                                if domain and domain != 'myshopify.com':
                                    parts = domain.split('.')
                                    if len(parts) >= 2 and parts[0]:
                                        all_domains.add(domain)
                
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
            except Exception as e:
                logger.debug(f"Erreur avec endpoint {endpoint}: {e}")
                continue
        
        return all_domains
    
    def scrape(self) -> Set[str]:
        """
        Scrape avec différentes méthodes pour obtenir plus de résultats.
        
        Returns:
            Set d'URLs Shopify trouvées
        """
        logger.info("Début du scraping CT alternatif")
        
        domains = self._fetch_with_different_endpoints()
        
        # Convertir en URLs
        shopify_urls = set()
        for domain in domains:
            shopify_urls.add(f"https://{domain}")
        
        logger.info(f"✓ CT Alternatif: {len(shopify_urls)} URLs trouvées")
        return shopify_urls



