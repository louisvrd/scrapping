"""
Scraper pour ProjectDiscovery Sonar (chaos.projectdiscovery.io).
Source légale et publique pour découvrir des sous-domaines.
Utilise l'API publique de Sonar pour trouver des domaines *.myshopify.com
"""

import requests
import time
from typing import Set, Optional, List
import logging
from urllib.parse import urlparse, quote

from config import (
    DELAY_BETWEEN_REQUESTS, TIMEOUT, USER_AGENT
)
from utils.shopify_detector import ShopifyDetector

logger = logging.getLogger(__name__)


class SonarScraper:
    """
    Scraper pour ProjectDiscovery Sonar.
    Utilise l'API publique de chaos.projectdiscovery.io pour trouver des sous-domaines myshopify.com
    """
    
    def __init__(self):
        self.shopify_detector = ShopifyDetector()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.base_url = "https://chaos.projectdiscovery.io"
    
    def _fetch_subdomains_from_sonar(self, domain: str = "myshopify.com") -> Set[str]:
        """
        Récupère les sous-domaines depuis l'API Sonar.
        Note: L'API Sonar peut ne pas avoir de données pour tous les domaines.
        
        Args:
            domain: Domaine à rechercher (par défaut: myshopify.com)
        
        Returns:
            Set de sous-domaines trouvés
        """
        subdomains = set()
        
        try:
            # API Sonar pour récupérer les sous-domaines
            # Format: https://chaos.projectdiscovery.io/v1/{domain}/subdomains
            api_url = f"{self.base_url}/v1/{domain}/subdomains"
            
            logger.debug(f"Requête Sonar: {api_url}")
            response = self.session.get(api_url, timeout=TIMEOUT * 2)
            
            # Ne pas lever d'exception pour 404, c'est normal si le domaine n'est pas dans Sonar
            if response.status_code == 404:
                logger.info(f"  → Domaine '{domain}' non disponible dans Sonar (normal - tous les domaines ne sont pas indexés)")
                return subdomains
            
            response.raise_for_status()
            
            data = response.json()
            
            # L'API retourne une liste de sous-domaines ou un dict
            if isinstance(data, list):
                for subdomain in data:
                    subdomain = str(subdomain).strip().lower()
                    if subdomain:
                        # Construire le domaine complet
                        full_domain = f"{subdomain}.{domain}"
                        # Filtrer les domaines invalides
                        if self._is_valid_subdomain(subdomain):
                            subdomains.add(full_domain)
            elif isinstance(data, dict):
                # Si la réponse est un dict, chercher dans différentes clés possibles
                subdomains_list = data.get('subdomains', data.get('data', data.get('results', [])))
                if isinstance(subdomains_list, list):
                    for subdomain in subdomains_list:
                        subdomain = str(subdomain).strip().lower()
                        if subdomain:
                            full_domain = f"{subdomain}.{domain}"
                            if self._is_valid_subdomain(subdomain):
                                subdomains.add(full_domain)
                elif isinstance(subdomains_list, str):
                    # Si c'est une chaîne, la traiter comme une liste séparée par des retours à la ligne
                    for subdomain in subdomains_list.split('\n'):
                        subdomain = subdomain.strip().lower()
                        if subdomain:
                            full_domain = f"{subdomain}.{domain}"
                            if self._is_valid_subdomain(subdomain):
                                subdomains.add(full_domain)
            
            logger.info(f"  → {len(subdomains)} sous-domaines trouvés pour '{domain}'")
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout pour la requête Sonar '{domain}'")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"  → Domaine '{domain}' non disponible dans Sonar (normal - tous les domaines ne sont pas indexés)")
            elif e.response.status_code == 429:
                logger.warning(f"Limite de rate Sonar atteinte - attendre avant de continuer")
                time.sleep(DELAY_BETWEEN_REQUESTS * 5)
            else:
                logger.warning(f"Erreur HTTP {e.response.status_code} pour '{domain}': {e}")
        except Exception as e:
            logger.warning(f"Erreur lors de la requête Sonar '{domain}': {e}")
        
        return subdomains
    
    def _is_valid_subdomain(self, subdomain: str) -> bool:
        """
        Vérifie si un sous-domaine est valide.
        
        Args:
            subdomain: Nom du sous-domaine à vérifier
        
        Returns:
            True si valide, False sinon
        """
        # Filtrer les sous-domaines invalides
        invalid_prefixes = ['www', 'admin', 'cdn', 'login', 'api', 'app', 'mail', 'ftp', 'test']
        
        if not subdomain or len(subdomain) == 0:
            return False
        
        # Vérifier si c'est un préfixe invalide
        if subdomain.lower() in invalid_prefixes:
            return False
        
        # Vérifier la longueur minimale
        if len(subdomain) < 2:
            return False
        
        # Vérifier qu'il ne contient que des caractères valides
        if not all(c.isalnum() or c == '-' for c in subdomain):
            return False
        
        return True
    
    def scrape(self, max_results: Optional[int] = None) -> Set[str]:
        """
        Scrape Sonar pour trouver des domaines Shopify.
        
        Args:
            max_results: Nombre maximum de résultats (None = tous)
        
        Returns:
            Set d'URLs Shopify trouvées
        """
        logger.info("Début du scraping Sonar (ProjectDiscovery)")
        logger.info("Note: Sonar peut ne pas avoir de données pour tous les domaines")
        
        all_domains = set()
        
        # Rechercher les sous-domaines de myshopify.com
        try:
            domains = self._fetch_subdomains_from_sonar("myshopify.com")
            
            if max_results:
                domains = set(list(domains)[:max_results])
            
            all_domains.update(domains)
            
            if len(domains) > 0:
                logger.info(f"  → {len(domains)} domaines trouvés via Sonar")
            else:
                logger.info(f"  → Aucun domaine trouvé (myshopify.com n'est peut-être pas indexé dans Sonar)")
            
        except Exception as e:
            logger.error(f"Erreur lors du scraping Sonar: {e}")
        
        # Convertir en URLs
        shopify_urls = set()
        for domain in all_domains:
            shopify_urls.add(f"https://{domain}")
        
        if len(shopify_urls) > 0:
            logger.info(f"✓ URLs Shopify générées: {len(shopify_urls)}")
        else:
            logger.info(f"✓ Sonar: 0 URLs trouvées (domaine non indexé dans Sonar)")
        
        return shopify_urls

