"""
Scraper pour des URLs personnalisées (liste de pages à scraper).
"""

import logging
from pathlib import Path
from typing import Set

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class CustomUrlsScraper(BaseScraper):
    """
    Scraper pour une liste personnalisée d'URLs.
    Lit un fichier avec une URL par ligne et scrape chaque page.
    """
    
    def __init__(self, urls_file: str):
        """
        Initialise le scraper.
        
        Args:
            urls_file: Chemin vers le fichier contenant les URLs (une par ligne)
        """
        super().__init__("custom_urls")
        self.urls_file = Path(urls_file)
    
    def get_next_page_url(self, current_url: str, html: str) -> None:
        """
        Pas de pagination pour les URLs personnalisées.
        Chaque URL est traitée indépendamment.
        """
        return None
    
    def scrape(self, start_url: str = None) -> Set[str]:
        """
        Scrape toutes les URLs du fichier.
        
        Args:
            start_url: Ignoré (utilisé pour compatibilité avec BaseScraper)
        
        Returns:
            Set d'URLs Shopify trouvées
        """
        if not self.urls_file.exists():
            logger.error(f"Fichier d'URLs introuvable: {self.urls_file}")
            return set()
        
        logger.info(f"Lecture des URLs depuis {self.urls_file}")
        
        # Lire toutes les URLs du fichier
        urls_to_scrape = set()
        with open(self.urls_file, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith('#'):  # Ignorer les lignes vides et commentaires
                    urls_to_scrape.add(url)
        
        logger.info(f"{len(urls_to_scrape)} URLs à scraper")
        
        shopify_urls = set()
        
        for url in urls_to_scrape:
            logger.info(f"Scraping: {url}")
            
            response = self._make_request(url)
            if not response:
                continue
            
            html = response.text
            self.pages_scraped += 1
            
            # Extraire toutes les URLs de la page
            all_urls = self._extract_urls_from_html(html, url)
            
            # Filtrer pour ne garder que les URLs Shopify
            page_shopify_urls = self._filter_shopify_urls(all_urls)
            shopify_urls.update(page_shopify_urls)
            
            logger.info(f"URLs Shopify trouvées: {len(page_shopify_urls)} (total: {len(shopify_urls)})")
        
        logger.info(f"Scraping terminé: {len(shopify_urls)} URLs Shopify trouvées")
        
        return shopify_urls

