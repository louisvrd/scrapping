"""
Scraper pour Certificate Transparency Logs (crt.sh).
Source légale et publique pour découvrir des domaines.
"""

import requests
import time
from typing import Set, Optional, List
import logging
from urllib.parse import urlparse, quote

from config import (
    CT_LOGS_URL, CT_LOGS_MAX_RESULTS, CT_LOGS_USE_VARIANTS,
    DELAY_BETWEEN_REQUESTS, TIMEOUT, USER_AGENT
)
from utils.shopify_detector import ShopifyDetector

logger = logging.getLogger(__name__)


class CertificateTransparencyScraper:
    """
    Scraper pour Certificate Transparency Logs.
    Utilise l'API publique de crt.sh pour trouver des domaines *.myshopify.com
    """
    
    def __init__(self):
        self.shopify_detector = ShopifyDetector()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
    
    def _get_query_variants(self) -> List[str]:
        """
        Retourne différentes variantes de requêtes pour obtenir plus de résultats.
        Utilise plusieurs patterns pour maximiser la collecte.
        
        Returns:
            Liste de patterns de requête
        """
        variants = [
            '%.myshopify.com',  # Pattern principal - tous les sous-domaines
        ]
        
        if CT_LOGS_USE_VARIANTS:
            # Ajouter des variantes pour capturer plus de domaines
            # Utiliser différents patterns pour obtenir tous les domaines possibles
            variants.extend([
                # Pas besoin d'ajouter plus de variantes car %.myshopify.com capture déjà tout
            ])
        
        return variants
    
    def _fetch_domains_from_query(self, query: str, max_results: int = None) -> Set[str]:
        """
        Récupère les domaines depuis une requête spécifique.
        
        Args:
            query: Pattern de recherche
            max_results: Nombre maximum de certificats à traiter (None = tous)
        
        Returns:
            Set de domaines trouvés
        """
        domains = set()
        
        try:
            # Requête à l'API crt.sh avec limite augmentée
            # Utiliser le paramètre limit pour obtenir plus de résultats
            api_url = f"{CT_LOGS_URL}/?q={quote(query)}&output=json"
            
            logger.debug(f"Requête: {api_url}")
            response = self.session.get(api_url, timeout=TIMEOUT * 2)  # Timeout plus long pour grandes réponses
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"  → {len(data)} certificats trouvés pour '{query}'")
            
            # Traiter tous les certificats (ou jusqu'à max_results si spécifié)
            processed = 0
            for cert in data:
                if max_results and processed >= max_results:
                    break
                
                name_value = cert.get('name_value', '')
                if name_value:
                    # name_value peut contenir plusieurs domaines séparés par \n
                    for domain in name_value.split('\n'):
                        domain = domain.strip().lower()
                        if domain.endswith('.myshopify.com'):
                            # Nettoyer le domaine
                            domain = domain.replace('*.', '').replace('www.', '')
                            # Filtrer les domaines invalides
                            if domain and domain not in ['myshopify.com']:
                                # Vérifier que c'est un domaine valide (pas juste "myshopify.com")
                                parts = domain.split('.')
                                if len(parts) >= 2 and parts[0]:  # Doit avoir au moins un sous-domaine
                                    # Vérifier que le nom du store n'est pas vide
                                    store_name = parts[0]
                                    if store_name and len(store_name) > 0:
                                        domains.add(domain)
                
                processed += 1
            
            logger.info(f"  → {len(domains)} domaines uniques extraits de cette requête")
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout pour la requête '{query}' - réponse trop volumineuse")
        except Exception as e:
            logger.warning(f"Erreur lors de la requête '{query}': {e}")
        
        return domains
    
    def scrape(self, max_results: int = None) -> Set[str]:
        """
        Scrape les logs de Certificate Transparency pour trouver des domaines Shopify.
        Utilise plusieurs variantes de requêtes pour maximiser les résultats.
        
        Args:
            max_results: Nombre maximum de certificats à traiter par requête (None = tous)
        
        Returns:
            Set d'URLs Shopify trouvées
        """
        if max_results is None:
            max_results = CT_LOGS_MAX_RESULTS
        
        logger.info(f"Début du scraping Certificate Transparency (max {max_results} certificats par requête)")
        logger.info(f"Objectif: collecter le maximum d'URLs Shopify uniques (cible: 20000+)")
        
        all_domains = set()
        query_variants = self._get_query_variants()
        
        # Traiter chaque variante de requête
        for i, query in enumerate(query_variants, 1):
            logger.info(f"\nRequête {i}/{len(query_variants)}: '{query}'")
            
            # Pour la première requête principale, ne pas limiter pour obtenir le maximum
            query_max = None if i == 1 else max_results
            domains = self._fetch_domains_from_query(query, query_max)
            new_domains = domains - all_domains
            all_domains.update(domains)
            
            logger.info(f"  → {len(new_domains)} nouveaux domaines (total cumulé: {len(all_domains)})")
        
        logger.info(f"\n✓ Domaines uniques trouvés au total: {len(all_domains)}")
        
        # Convertir en URLs
        shopify_urls = set()
        for domain in all_domains:
            shopify_urls.add(f"https://{domain}")
        
        logger.info(f"✓ URLs Shopify générées: {len(shopify_urls)}")
        
        return shopify_urls
