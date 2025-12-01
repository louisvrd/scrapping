"""
Module principal de scraping des sites Shopify
"""
import time
from typing import List, Dict
from tqdm import tqdm

from search_engine import SearchEngine
from shop_app_scraper import ShopAppScraper
from shopify_detector import ShopifyDetector
from data_manager import DataManager
from mass_scraper import MassScraper
from config import DELAY_BETWEEN_REQUESTS


class ShopifyScraper:
    """Classe principale pour scraper et répertorier les sites Shopify"""
    
    def __init__(self):
        self.search_engine = SearchEngine()
        self.shop_app_scraper = ShopAppScraper()
        self.mass_scraper = MassScraper()
        self.detector = ShopifyDetector()
        self.data_manager = DataManager()
        self.results: List[Dict] = []
    
    def discover_shopify_sites(self, search_queries: List[str] = None, categories: List[str] = None, max_pages: int = 10, auto_discover: bool = True, use_web_search: bool = True) -> List[str]:
        """
        Découvre des sites Shopify via shop.app ET les moteurs de recherche web
        
        Args:
            search_queries: Liste de termes de recherche
            categories: Liste de catégories à explorer
            max_pages: Nombre maximum de pages à scraper par recherche
            auto_discover: Si True, découvre automatiquement toutes les pages
            use_web_search: Si True, utilise aussi les moteurs de recherche web
            
        Returns:
            Liste d'URLs trouvées
        """
        print("=== DÉCOUVERTE DE SITES SHOPIFY ===\n")
        
        all_urls = []
        web_urls = []  # Initialiser même si pas utilisé
        
        # Méthode 1: Scraping de shop.app
        print("=== MÉTHODE 1: SCRAPING DE SHOP.APP ===\n")
        shop_app_urls = self.shop_app_scraper.scrape_all(
            search_queries=search_queries,
            categories=categories,
            max_pages=max_pages,
            use_selenium_fallback=True,
            auto_discover=auto_discover
        )
        all_urls.extend(shop_app_urls)
        print(f"  → {len(shop_app_urls)} URLs trouvées sur shop.app\n")
        
        # Méthode 2: Recherche sur le web (moteurs de recherche)
        if use_web_search:
            print("=== MÉTHODE 2: RECHERCHE SUR LE WEB ===\n")
            
            # Générer des requêtes de recherche pour le web
            web_queries = []
            
            # Requêtes par défaut
            from config import GOOGLE_DORK_QUERIES
            web_queries.extend(GOOGLE_DORK_QUERIES)
            
            # Ajouter les requêtes personnalisées
            if search_queries:
                for query in search_queries:
                    # Ajouter des variantes pour le web
                    web_queries.append(f'site:myshopify.com {query}')
                    web_queries.append(f'"{query}" shopify')
                    web_queries.append(f'{query} myshopify.com')
            
            # Ajouter des recherches par lettres/chiffres pour le web
            import string
            for letter in string.ascii_lowercase[:10]:  # a-j pour commencer
                web_queries.append(f'site:{letter}.myshopify.com')
            
            # Rechercher sur tous les moteurs
            web_urls = self.search_engine.search_all_engines(web_queries)
            all_urls.extend(web_urls)
            print(f"  → {len(web_urls)} URLs trouvées via moteurs de recherche\n")
        
        # Déduplication
        unique_urls = list(set(all_urls))
        
        # Séparer les URLs par source (approximatif)
        shop_app_set = set(shop_app_urls)
        web_set = set(web_urls) if use_web_search else set()
        shop_app_unique = len(shop_app_set)
        web_unique = len(web_set)
        
        print(f"\n{'='*60}")
        print(f"TOTAL: {len(unique_urls)} URLs uniques trouvées")
        print(f"  - shop.app: {shop_app_unique} URLs")
        if use_web_search:
            print(f"  - Web (moteurs de recherche): {web_unique} URLs")
        print(f"{'='*60}\n")
        
        return unique_urls
    
    def verify_and_extract(self, urls: List[str], verify_all: bool = True) -> List[Dict]:
        """
        Vérifie et extrait les informations des sites
        
        Args:
            urls: Liste d'URLs à vérifier
            verify_all: Si True, vérifie tous les sites même ceux qui semblent Shopify
            
        Returns:
            Liste de dictionnaires avec les informations extraites
        """
        print("\n=== VÉRIFICATION ET EXTRACTION DES INFORMATIONS ===\n")
        
        results = []
        
        for url in tqdm(urls, desc="Vérification des sites"):
            try:
                # Vérifier si c'est un site Shopify
                detection = self.detector.is_shopify_site(url)
                
                if detection['is_shopify'] or verify_all:
                    # Extraire les informations
                    info = self.detector.extract_shopify_info(url)
                    info['evidence'] = detection['evidence']
                    
                    results.append(info)
                    
                    if detection['is_shopify']:
                        print(f"✓ Site Shopify trouvé: {url}")
                    else:
                        print(f"✗ Site non-Shopify: {url}")
                else:
                    print(f"✗ Site non-Shopify ignoré: {url}")
                
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
            except Exception as e:
                print(f"Erreur lors du traitement de {url}: {e}")
                continue
        
        self.results = results
        return results
    
    def run_massive_scrape(self, strategy: str = "comprehensive", verify_all: bool = False, skip_verification: bool = True, use_web_search: bool = True):
        """
        Exécute un scraping massif pour découvrir le maximum de sites
        
        Args:
            strategy: 'comprehensive' (tout), 'categories', 'combinations', 'discovery', 'pagination'
            verify_all: Si True, vérifie tous les sites même ceux qui ne semblent pas Shopify
            skip_verification: Si True, saute la vérification (recommandé pour 4M sites)
        """
        print("=" * 60)
        print("SCRAPING MASSIF DES SITES SHOPIFY")
        print("=" * 60 + "\n")
        
        if skip_verification:
            print("⚡ MODE RAPIDE: Vérification désactivée")
            print("⚡ Temps estimé: 12-24 heures pour 4M URLs (au lieu de 46 jours)")
            print("⚡ Les URLs seront collectées depuis shop.app sans vérification\n")
        else:
            print("⚠️  MODE LENT: Vérification activée")
            print(f"⚠️  Temps estimé: ~{4000000 * DELAY_BETWEEN_REQUESTS / 86400:.0f} jours pour 4M URLs\n")
        
        # Scraping massif (shop.app + web)
        urls = self.mass_scraper.massive_scrape(strategy=strategy, use_web_search=use_web_search)
        
        if not urls:
            print("Aucune URL trouvée. Arrêt du scraping.")
            return
        
        # Vérification (optionnelle, désactivée par défaut pour aller vite)
        if not skip_verification and verify_all:
            print(f"\nVérification de {len(urls)} URLs...")
            print(f"⏱️  Temps estimé: ~{len(urls) * DELAY_BETWEEN_REQUESTS / 3600:.1f} heures")
            results = self.verify_and_extract(list(urls), verify_all=False)
            shopify_results = [r for r in results if r.get('verified', False)]
        else:
            # Sauvegarder directement sans vérification pour aller plus vite
            print(f"\nSauvegarde de {len(urls)} URLs sans vérification...")
            shopify_results = [{'url': url, 'verified': False, 'source': 'shop.app'} for url in urls]
        
        # Sauvegarder les résultats
        print("\n=== SAUVEGARDE DES RÉSULTATS ===\n")
        self.data_manager.save_to_json(shopify_results)
        self.data_manager.save_to_csv(shopify_results)
        self.data_manager.export_statistics(shopify_results)
        
        print(f"\n✓ Scraping massif terminé: {len(shopify_results)} sites répertoriés")
        from config import OUTPUT_DIR
        print(f"✓ Fichiers sauvegardés dans le dossier '{OUTPUT_DIR}'")
    
    def run_full_scrape(self, search_queries: List[str] = None, categories: List[str] = None, max_pages: int = 10, verify_all: bool = False, auto_discover: bool = True, skip_verification: bool = False, use_web_search: bool = True):
        """
        Exécute un scraping complet via shop.app
        
        Args:
            search_queries: Liste de termes de recherche sur shop.app
            categories: Liste de catégories à explorer
            max_pages: Nombre maximum de pages à scraper par recherche
            verify_all: Si True, vérifie tous les sites même ceux qui ne semblent pas Shopify
            skip_verification: Si True, saute la vérification pour aller beaucoup plus vite
        """
        print("=" * 60)
        print("SCRAPING COMPLET DES SITES SHOPIFY VIA SHOP.APP")
        print("=" * 60 + "\n")
        
        if skip_verification:
            print("⚠️  MODE RAPIDE: Vérification désactivée")
            print("⚠️  Les URLs seront collectées sans vérification Shopify\n")
        
        # Étape 1: Découvrir les sites via shop.app ET le web
        urls = self.discover_shopify_sites(search_queries=search_queries, categories=categories, max_pages=max_pages, auto_discover=auto_discover, use_web_search=use_web_search)
        
        if not urls:
            print("Aucune URL trouvée. Arrêt du scraping.")
            return
        
        # Étape 2: Vérifier et extraire les informations (ou sauter)
        if skip_verification:
            print(f"\nSauvegarde directe de {len(urls)} URLs sans vérification...")
            shopify_results = [{'url': url, 'verified': False, 'source': 'shop.app'} for url in urls]
        else:
            print(f"\nVérification de {len(urls)} URLs...")
            print(f"⏱️  Temps estimé: ~{len(urls) * DELAY_BETWEEN_REQUESTS / 3600:.1f} heures")
            results = self.verify_and_extract(urls, verify_all)
            
            # Filtrer seulement les sites Shopify vérifiés
            shopify_results = [r for r in results if r.get('verified', False)]
            
            if not shopify_results:
                print("Aucun site Shopify vérifié trouvé.")
                if results:
                    print(f"Note: {len(results)} sites vérifiés mais aucun n'était Shopify.")
                return
        
        # Étape 3: Sauvegarder les résultats
        print("\n=== SAUVEGARDE DES RÉSULTATS ===\n")
        self.data_manager.save_to_json(shopify_results)
        self.data_manager.save_to_csv(shopify_results)
        self.data_manager.export_statistics(shopify_results)
        
        print(f"\n✓ Scraping terminé: {len(shopify_results)} sites répertoriés")
        if skip_verification:
            print("⚠️  Note: Les sites n'ont pas été vérifiés (verified=False)")
        from config import OUTPUT_DIR
        print(f"✓ Fichiers sauvegardés dans le dossier '{OUTPUT_DIR}'")
    
    def add_custom_urls(self, urls: List[str], verify: bool = True):
        """
        Ajoute des URLs personnalisées à vérifier
        
        Args:
            urls: Liste d'URLs à ajouter
            verify: Si True, vérifie les sites avant de les ajouter
        """
        print(f"\n=== AJOUT DE {len(urls)} URLs PERSONNALISÉES ===\n")
        
        if verify:
            results = self.verify_and_extract(urls, verify_all=False)
            # Filtrer seulement les sites Shopify vérifiés
            shopify_results = [r for r in results if r.get('verified', False)]
            
            if shopify_results:
                # Fusionner avec les résultats existants
                existing = self.data_manager.load_from_json()
                merged = self.data_manager.merge_data(shopify_results, existing_file=None)
                
                self.data_manager.save_to_json(merged)
                self.data_manager.save_to_csv(merged)
                
                print(f"✓ {len(shopify_results)} nouveaux sites Shopify ajoutés")
        else:
            # Ajouter directement sans vérification
            new_results = [{'url': url, 'verified': False} for url in urls]
            existing = self.data_manager.load_from_json()
            merged = self.data_manager.merge_data(new_results, existing_file=None)
            
            self.data_manager.save_to_json(merged)
            self.data_manager.save_to_csv(merged)
            
            print(f"✓ {len(urls)} URLs ajoutées (non vérifiées)")

