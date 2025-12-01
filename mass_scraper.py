"""
Module de scraping massif pour découvrir le maximum de sites Shopify
"""
import string
import itertools
from typing import List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from shop_app_scraper import ShopAppScraper
from search_engine import SearchEngine
from config import DELAY_BETWEEN_REQUESTS, GOOGLE_DORK_QUERIES


class MassScraper:
    """Classe pour scraper massivement shop.app et découvrir le maximum de sites"""
    
    def __init__(self):
        self.scraper = ShopAppScraper()
        self.search_engine = SearchEngine()
        self.all_urls: Set[str] = set()
    
    def generate_search_combinations(self) -> List[str]:
        """
        Génère toutes les combinaisons de recherche possibles
        
        Returns:
            Liste de termes de recherche
        """
        searches = []
        
        # 1. Recherches par lettres simples (a-z)
        print("Génération des recherches par lettres...")
        for letter in string.ascii_lowercase:
            searches.append(letter)
        
        # 2. Recherches par combinaisons de 2 lettres (aa-zz)
        print("Génération des recherches par combinaisons de 2 lettres...")
        for combo in itertools.product(string.ascii_lowercase, repeat=2):
            searches.append(''.join(combo))
        
        # 3. Recherches par chiffres (0-9, 00-99, etc.)
        print("Génération des recherches par chiffres...")
        for num in range(100):
            searches.append(str(num))
        
        # 4. Mots-clés courants
        common_keywords = [
            'shop', 'store', 'boutique', 'market', 'mall', 'buy', 'sell',
            'fashion', 'style', 'trend', 'design', 'art', 'craft', 'gift',
            'home', 'decor', 'tech', 'gadget', 'book', 'music', 'sport',
            'health', 'beauty', 'food', 'drink', 'coffee', 'tea', 'wine',
            'jewelry', 'watch', 'shoe', 'bag', 'clothing', 'accessory',
            'electronic', 'phone', 'computer', 'laptop', 'camera',
            'furniture', 'kitchen', 'bathroom', 'bedroom', 'living',
            'toy', 'game', 'puzzle', 'educational', 'baby', 'kid',
            'pet', 'dog', 'cat', 'bird', 'fish',
            'garden', 'outdoor', 'camping', 'hiking', 'travel',
            'car', 'bike', 'motorcycle', 'vehicle', 'auto'
        ]
        searches.extend(common_keywords)
        
        # 5. Combinaisons mots-clés + lettres
        for keyword in common_keywords[:20]:  # Limiter pour éviter trop de combinaisons
            for letter in string.ascii_lowercase[:5]:  # a-e seulement
                searches.append(f"{keyword}{letter}")
                searches.append(f"{letter}{keyword}")
        
        print(f"Total de {len(searches)} combinaisons de recherche générées")
        return searches
    
    def scrape_with_pagination(self, query: str = "", max_pages: int = 1000) -> Set[str]:
        """
        Scrape avec pagination agressive
        
        Args:
            query: Terme de recherche
            max_pages: Nombre maximum de pages à scraper
            
        Returns:
            Set d'URLs trouvées
        """
        urls = set()
        consecutive_empty = 0
        max_consecutive_empty = 5  # Arrêter après 5 pages vides consécutives
        
        print(f"  Scraping '{query}' jusqu'à {max_pages} pages...")
        
        for page in range(1, max_pages + 1):
            try:
                page_urls = self.scraper.search_shops(query=query, page=page)
                
                if page_urls:
                    urls.update(page_urls)
                    self.all_urls.update(page_urls)
                    consecutive_empty = 0
                    if page % 10 == 0:
                        print(f"    Page {page}: {len(page_urls)} URLs (Total: {len(urls)})")
                else:
                    consecutive_empty += 1
                    if consecutive_empty >= max_consecutive_empty:
                        print(f"    Arrêt après {consecutive_empty} pages vides consécutives")
                        break
                
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
            except Exception as e:
                print(f"    Erreur page {page}: {e}")
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive_empty:
                    break
                continue
        
        print(f"  → {len(urls)} URLs trouvées pour '{query}'")
        return urls
    
    def scrape_all_categories(self, max_pages_per_category: int = 500) -> Set[str]:
        """
        Scrape toutes les catégories disponibles
        
        Args:
            max_pages_per_category: Nombre maximum de pages par catégorie
            
        Returns:
            Set d'URLs trouvées
        """
        urls = set()
        
        # Liste exhaustive de catégories possibles
        categories = [
            'fashion', 'clothing', 'accessories', 'jewelry', 'watches',
            'shoes', 'bags', 'luggage', 'beauty', 'cosmetics', 'skincare',
            'electronics', 'computers', 'phones', 'cameras', 'audio',
            'home', 'furniture', 'decor', 'kitchen', 'bath', 'bedding',
            'toys', 'games', 'baby', 'kids', 'sports', 'outdoor',
            'books', 'music', 'movies', 'art', 'crafts',
            'food', 'drinks', 'coffee', 'tea', 'wine', 'beer',
            'health', 'fitness', 'wellness', 'supplements',
            'automotive', 'tools', 'hardware', 'garden',
            'pets', 'animals', 'travel', 'luggage',
            'office', 'stationery', 'education',
            'collectibles', 'antiques', 'vintage'
        ]
        
        print(f"Exploration de {len(categories)} catégories...")
        
        for category in categories:
            try:
                category_urls = self.scrape_with_pagination(query=category, max_pages=max_pages_per_category)
                urls.update(category_urls)
                print(f"  Catégorie '{category}': {len(category_urls)} URLs")
            except Exception as e:
                print(f"  Erreur catégorie '{category}': {e}")
                continue
        
        return urls
    
    def scrape_parallel(self, queries: List[str], max_workers: int = 10, max_pages: int = 100) -> Set[str]:
        """
        Scrape en parallèle plusieurs requêtes
        
        Args:
            queries: Liste de termes de recherche
            max_workers: Nombre de threads parallèles
            max_pages: Nombre maximum de pages par requête
            
        Returns:
            Set d'URLs trouvées
        """
        all_urls = set()
        
        print(f"Scraping parallèle de {len(queries)} requêtes avec {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.scrape_with_pagination, query, max_pages): query 
                for query in queries
            }
            
            completed = 0
            for future in as_completed(futures):
                query = futures[future]
                try:
                    urls = future.result()
                    all_urls.update(urls)
                    completed += 1
                    print(f"  [{completed}/{len(queries)}] '{query}' terminé: {len(urls)} URLs")
                except Exception as e:
                    print(f"  Erreur pour '{query}': {e}")
        
        return all_urls
    
    def scrape_web_search(self, max_queries: int = 1000) -> Set[str]:
        """
        Scrape le web via les moteurs de recherche
        
        Args:
            max_queries: Nombre maximum de requêtes à tester
            
        Returns:
            Set d'URLs trouvées
        """
        urls = set()
        
        print("=== STRATÉGIE WEB: RECHERCHE SUR LES MOTEURS DE RECHERCHE ===\n")
        
        # Requêtes de base
        base_queries = GOOGLE_DORK_QUERIES.copy()
        
        # Générer des requêtes supplémentaires
        import string
        web_queries = []
        
        # Recherches par lettres (site:a.myshopify.com, site:b.myshopify.com, etc.)
        print("  Génération de requêtes par lettres...")
        for letter in string.ascii_lowercase:
            web_queries.append(f'site:{letter}.myshopify.com')
            web_queries.append(f'inurl:{letter}.myshopify.com')
        
        # Recherches par combinaisons de 2 lettres
        print("  Génération de requêtes par combinaisons...")
        for combo in itertools.product(string.ascii_lowercase, repeat=2):
            if len(web_queries) >= max_queries:
                break
            combo_str = ''.join(combo)
            web_queries.append(f'site:{combo_str}.myshopify.com')
        
        # Recherches par chiffres
        print("  Génération de requêtes par chiffres...")
        for num in range(100):
            web_queries.append(f'site:{num}.myshopify.com')
        
        # Mots-clés + shopify
        keywords = ['shop', 'store', 'boutique', 'fashion', 'electronics', 'home', 'beauty']
        for keyword in keywords:
            web_queries.append(f'"{keyword}" myshopify.com')
            web_queries.append(f'site:myshopify.com {keyword}')
        
        # Limiter le nombre de requêtes
        all_queries = base_queries + web_queries[:max_queries]
        print(f"  Total de {len(all_queries)} requêtes web à tester\n")
        
        # Rechercher sur tous les moteurs
        web_urls = self.search_engine.search_all_engines(all_queries)
        urls.update(web_urls)
        self.all_urls.update(web_urls)
        
        print(f"\n  → {len(web_urls)} URLs trouvées via moteurs de recherche")
        return urls
    
    def massive_scrape(self, strategy: str = "comprehensive", use_web_search: bool = True) -> Set[str]:
        """
        Scraping massif avec différentes stratégies (shop.app + web)
        
        Args:
            strategy: 'comprehensive' (tout), 'categories', 'combinations', 'discovery', 'pagination', 'web'
            use_web_search: Si True, recherche aussi sur le web
            
        Returns:
            Set d'URLs trouvées
        """
        print("=" * 60)
        print("SCRAPING MASSIF (SHOP.APP + WEB)")
        print("=" * 60 + "\n")
        
        all_urls = set()
        
        if strategy == "comprehensive" or strategy == "categories":
            print("=== STRATÉGIE 1: EXPLORATION DES CATÉGORIES (SHOP.APP) ===\n")
            category_urls = self.scrape_all_categories(max_pages_per_category=1000)
            all_urls.update(category_urls)
            print(f"\nTotal catégories shop.app: {len(category_urls)} URLs\n")
        
        if strategy == "comprehensive" or strategy == "combinations":
            print("=== STRATÉGIE 2: RECHERCHES PAR COMBINAISONS (SHOP.APP) ===\n")
            searches = self.generate_search_combinations()
            # Limiter pour éviter trop de requêtes
            limited_searches = searches[:1000]  # Premiers 1000
            combination_urls = self.scrape_parallel(limited_searches, max_workers=5, max_pages=50)
            all_urls.update(combination_urls)
            print(f"\nTotal combinaisons shop.app: {len(combination_urls)} URLs\n")
        
        if strategy == "comprehensive" or strategy == "discovery":
            print("=== STRATÉGIE 3: DÉCOUVERTE AUTOMATIQUE PROFONDE (SHOP.APP) ===\n")
            discovery_urls = self.scraper.discover_all_pages(
                start_url=self.scraper.base_url,
                max_depth=5,  # Profondeur augmentée
                use_selenium=True
            )
            all_urls.update(discovery_urls)
            print(f"\nTotal découverte shop.app: {len(discovery_urls)} URLs\n")
        
        if strategy == "comprehensive" or strategy == "pagination":
            print("=== STRATÉGIE 4: PAGINATION AGRESSIVE (SHOP.APP) ===\n")
            pagination_urls = self.scrape_with_pagination(query="", max_pages=5000)
            all_urls.update(pagination_urls)
            print(f"\nTotal pagination shop.app: {len(pagination_urls)} URLs\n")
        
        # Recherche sur le web
        if use_web_search and (strategy == "comprehensive" or strategy == "web"):
            web_urls = self.scrape_web_search(max_queries=2000)
            all_urls.update(web_urls)
            print(f"\nTotal web: {len(web_urls)} URLs\n")
        
        unique_urls = list(self.all_urls)
        
        # Séparer les URLs par source
        shop_app_count = len([u for u in unique_urls if 'shop.app' not in u and not any(engine in u for engine in ['google.com', 'bing.com', 'duckduckgo.com'])])
        web_count = len(unique_urls) - shop_app_count
        
        print(f"\n{'='*60}")
        print(f"TOTAL FINAL: {len(unique_urls)} URLs UNIQUES TROUVÉES")
        print(f"  - shop.app: {shop_app_count} URLs")
        print(f"  - Web (moteurs de recherche): {web_count} URLs")
        print(f"{'='*60}\n")
        
        return set(unique_urls)

