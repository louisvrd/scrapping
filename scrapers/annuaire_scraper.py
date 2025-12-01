"""
Scraper pour les annuaires publics (shop.app, etc.).
"""

import time
from typing import Set, Optional
from urllib.parse import urljoin, urlparse
import logging

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper
from config import DELAY_BETWEEN_PAGES, MAX_PAGES_PER_SOURCE

logger = logging.getLogger(__name__)


class AnnuaireScraper(BaseScraper):
    """
    Scraper pour les annuaires publics de sites Shopify.
    Gère la pagination automatiquement.
    """
    
    def __init__(self, source_name: str, base_url: str, pagination_type: str = 'next_button'):
        """
        Initialise le scraper d'annuaire.
        
        Args:
            source_name: Nom de la source
            base_url: URL de base de l'annuaire
            pagination_type: Type de pagination ('next_button', 'numbered', 'infinite_scroll')
        """
        super().__init__(source_name)
        self.base_url = base_url
        self.pagination_type = pagination_type
    
    def get_next_page_url(self, current_url: str, html: str) -> Optional[str]:
        """
        Détermine l'URL de la page suivante selon le type de pagination.
        
        Args:
            current_url: URL de la page actuelle
            html: Contenu HTML de la page actuelle
        
        Returns:
            URL de la page suivante ou None
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            if self.pagination_type == 'next_button':
                # Chercher un bouton/lien "Suivant" ou "Next"
                next_selectors = [
                    'a[aria-label*="next" i]',
                    'a[aria-label*="suivant" i]',
                    'a:contains("Next")',
                    'a:contains("Suivant")',
                    'a.next',
                    'a[rel="next"]',
                ]
                
                for selector in next_selectors:
                    try:
                        next_link = soup.select_one(selector)
                        if next_link and next_link.get('href'):
                            href = next_link.get('href')
                            return urljoin(current_url, href)
                    except:
                        continue
            
            elif self.pagination_type == 'numbered':
                # Chercher les liens de pagination numérotés
                # Trouver le numéro de page actuel
                current_page = self._extract_page_number(current_url)
                if current_page is not None:
                    next_page = current_page + 1
                    # Chercher un lien vers la page suivante
                    next_link = soup.find('a', string=str(next_page))
                    if next_link and next_link.get('href'):
                        return urljoin(current_url, next_link.get('href'))
            
            elif self.pagination_type == 'infinite_scroll':
                # Pour le scroll infini, on peut essayer de modifier l'URL
                # ou utiliser une API si disponible
                # Ici, on retourne None car le scroll infini nécessite Selenium/Playwright
                logger.info("Pagination infinite_scroll détectée - nécessite Selenium/Playwright")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection de la page suivante: {e}")
            return None
    
    def _extract_page_number(self, url: str) -> Optional[int]:
        """Extrait le numéro de page d'une URL."""
        import re
        # Chercher des patterns comme ?page=2, /page/2, etc.
        patterns = [
            r'[?&]page=(\d+)',
            r'/page/(\d+)',
            r'/p(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    return int(match.group(1))
                except:
                    continue
        
        return None
    
    def scrape(self, start_url: str) -> Set[str]:
        """
        Scrape l'annuaire en suivant la pagination.
        
        Args:
            start_url: URL de départ
        
        Returns:
            Set d'URLs Shopify trouvées
        """
        logger.info(f"Début du scraping de {self.source_name} depuis {start_url}")
        
        current_url = start_url
        pages_scraped = 0
        shopify_urls = set()
        
        while current_url and pages_scraped < MAX_PAGES_PER_SOURCE:
            logger.info(f"Scraping page {pages_scraped + 1}: {current_url}")
            
            response = self._make_request(current_url)
            if not response:
                logger.warning(f"Impossible de récupérer {current_url}")
                break
            
            html = response.text
            self.pages_scraped += 1
            pages_scraped += 1
            
            # Extraire toutes les URLs de la page
            all_urls = self._extract_urls_from_html(html, current_url)
            logger.debug(f"URLs trouvées sur la page: {len(all_urls)}")
            
            # Filtrer pour ne garder que les URLs Shopify
            page_shopify_urls = self._filter_shopify_urls(all_urls)
            shopify_urls.update(page_shopify_urls)
            
            logger.info(f"URLs Shopify trouvées sur cette page: {len(page_shopify_urls)} (total: {len(shopify_urls)})")
            
            # Trouver la page suivante
            next_url = self.get_next_page_url(current_url, html)
            
            if not next_url:
                logger.info("Aucune page suivante trouvée - fin du scraping")
                break
            
            current_url = next_url
            
            # Délai entre les pages
            time.sleep(DELAY_BETWEEN_PAGES)
        
        logger.info(f"Scraping terminé: {pages_scraped} pages scrapées, {len(shopify_urls)} URLs Shopify trouvées")
        
        return shopify_urls

