"""
Classe de base pour tous les scrapers.
"""

import time
import requests
from abc import ABC, abstractmethod
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse
import logging

from config import (
    DELAY_BETWEEN_REQUESTS, DELAY_BETWEEN_PAGES, MAX_RETRIES, TIMEOUT, USER_AGENT,
    RESPECT_ROBOTS_TXT, MAX_PAGES_PER_SOURCE
)
from utils.robots_checker import RobotsChecker
from utils.shopify_detector import ShopifyDetector

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Classe de base pour tous les scrapers."""
    
    def __init__(self, source_name: str):
        """
        Initialise le scraper.
        
        Args:
            source_name: Nom de la source (pour le logging)
        """
        self.source_name = source_name
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.robots_checker = RobotsChecker() if RESPECT_ROBOTS_TXT else None
        self.shopify_detector = ShopifyDetector()
        self.urls_found: Set[str] = set()
        self.pages_scraped = 0
    
    def _make_request(self, url: str, retries: int = None) -> Optional[requests.Response]:
        """
        Fait une requête HTTP avec retry et gestion d'erreurs.
        
        Args:
            url: URL à requêter
            retries: Nombre de tentatives (None = utiliser MAX_RETRIES)
        
        Returns:
            Response ou None en cas d'erreur
        """
        if retries is None:
            retries = MAX_RETRIES
        
        # Vérifier robots.txt si activé
        if self.robots_checker and not self.robots_checker.can_fetch(url, USER_AGENT):
            logger.warning(f"URL bloquée par robots.txt: {url}")
            return None
        
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
                response.raise_for_status()
                
                # Délai entre requêtes
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
                return response
                
            except requests.exceptions.HTTPError as e:
                # Gestion spéciale pour les erreurs HTTP
                status_code = e.response.status_code if hasattr(e, 'response') else None
                if status_code == 403:
                    logger.warning(f"Accès refusé (403) pour {url} - Le site bloque probablement les requêtes automatisées")
                    logger.info("  → C'est normal et légal - le site protège ses ressources")
                    logger.info("  → Vous pouvez désactiver cette source dans la configuration")
                    return None  # Ne pas réessayer pour 403
                elif status_code == 429:
                    logger.warning(f"Trop de requêtes (429) pour {url} - Attente plus longue...")
                    time.sleep(DELAY_BETWEEN_REQUESTS * 5)  # Attendre plus longtemps
                else:
                    logger.warning(f"Tentative {attempt + 1}/{retries} échouée pour {url}: {e}")
                    if attempt < retries - 1:
                        time.sleep(DELAY_BETWEEN_REQUESTS * (attempt + 1))  # Backoff exponentiel
                    else:
                        logger.error(f"Impossible de récupérer {url} après {retries} tentatives")
                        return None
            except requests.exceptions.RequestException as e:
                logger.warning(f"Tentative {attempt + 1}/{retries} échouée pour {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(DELAY_BETWEEN_REQUESTS * (attempt + 1))  # Backoff exponentiel
                else:
                    logger.error(f"Impossible de récupérer {url} après {retries} tentatives")
                    return None
        
        return None
    
    def _extract_urls_from_html(self, html: str, base_url: str) -> Set[str]:
        """
        Extrait toutes les URLs d'une page HTML.
        
        Args:
            html: Contenu HTML
            base_url: URL de base pour résoudre les URLs relatives
        
        Returns:
            Set d'URLs trouvées
        """
        from bs4 import BeautifulSoup
        
        urls = set()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extraire tous les liens
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href:
                    # Résoudre l'URL relative
                    absolute_url = urljoin(base_url, href)
                    # Nettoyer l'URL (enlever les fragments, etc.)
                    parsed = urlparse(absolute_url)
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if parsed.query:
                        clean_url += f"?{parsed.query}"
                    urls.add(clean_url)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des URLs: {e}")
        
        return urls
    
    def _filter_shopify_urls(self, urls: Set[str]) -> Set[str]:
        """
        Filtre les URLs pour ne garder que celles qui sont Shopify.
        
        Args:
            urls: Set d'URLs à filtrer
        
        Returns:
            Set d'URLs Shopify
        """
        shopify_urls = set()
        
        for url in urls:
            if self.shopify_detector.is_shopify_url(url):
                shopify_urls.add(url)
        
        return shopify_urls
    
    @abstractmethod
    def get_next_page_url(self, current_url: str, html: str) -> Optional[str]:
        """
        Détermine l'URL de la page suivante.
        
        Args:
            current_url: URL de la page actuelle
            html: Contenu HTML de la page actuelle
        
        Returns:
            URL de la page suivante ou None
        """
        pass
    
    @abstractmethod
    def scrape(self, start_url: str) -> Set[str]:
        """
        Scrape une source de données.
        
        Args:
            start_url: URL de départ
        
        Returns:
            Set d'URLs Shopify trouvées
        """
        pass

