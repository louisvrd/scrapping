"""
Script de découverte GRATUITE de sites Shopify via scraping web.

Ce script utilise plusieurs méthodes gratuites pour découvrir des sites Shopify :
1. Recherche via moteurs de recherche (Google, DuckDuckGo, Bing) avec des dorks
2. Scraping de shop.app (annuaire de sites Shopify)
3. Utilisation de listes publiques (GitHub, forums, etc.)

Aucune clé API payante requise !
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import List, Set, Optional
from urllib.parse import urlparse, quote_plus
from pathlib import Path

# Charger les variables d'environnement
BASE_DIR = Path(__file__).parent
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path), override=True)
else:
    load_dotenv(override=True)

# Gestion des User Agents (avec fallback)
# Initialiser une seule fois pour éviter les problèmes
try:
    from fake_useragent import UserAgent
    _ua_instance = UserAgent()
    def get_random_user_agent():
        """Retourne un User-Agent aléatoire depuis fake_useragent"""
        try:
            # fake_useragent utilise .random comme propriété, pas méthode
            return _ua_instance.random
        except Exception:
            # En cas d'erreur, utiliser le fallback
            import random
            USER_AGENTS_LIST = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ]
            return random.choice(USER_AGENTS_LIST)
except ImportError:
    # Fallback si fake_useragent n'est pas installé
    import random
    USER_AGENTS_LIST = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
    def get_random_user_agent():
        """Retourne un User-Agent aléatoire depuis la liste de fallback"""
        return random.choice(USER_AGENTS_LIST)

# Configuration
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)  # Créer le dossier s'il n'existe pas
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'domains_to_scrape.txt')
MAX_RESULTS = int(os.getenv('MAX_RESULTS', '5000'))  # Nombre maximum de résultats
DELAY_BETWEEN_REQUESTS = float(os.getenv('DELAY_BETWEEN_REQUESTS', '1.0'))  # Délai entre requêtes
MAX_PAGES_PER_QUERY = int(os.getenv('MAX_PAGES_PER_QUERY', '100'))  # Nombre maximum de pages par requête
MAX_CONSECUTIVE_EMPTY_PAGES = int(os.getenv('MAX_CONSECUTIVE_EMPTY_PAGES', '10'))  # Nombre de pages vides consécutives avant d'arrêter
MAX_RETRIES = 100
TIMEOUT = 10
DEBUG_SAVE_HTML = os.getenv('DEBUG_SAVE_HTML', 'false').lower() == 'true'  # Sauvegarder HTML pour debug

# Configuration Selenium (pour contourner les blocages)
USE_SELENIUM = os.getenv('USE_SELENIUM', 'true').lower() == 'true'  # Utiliser Selenium au lieu de requests
SELENIUM_BROWSER = os.getenv('SELENIUM_BROWSER', 'chrome').lower()  # chrome, firefox, edge
SELENIUM_HEADLESS = os.getenv('SELENIUM_HEADLESS', 'true').lower() == 'true'  # Mode headless

# Patterns pour identifier les sites Shopify
SHOPIFY_PATTERNS = [
    r'myshopify\.com',
    r'cdn\.shopify\.com',
    r'shopifycdn\.com',
    r'Shopify\.theme',
    r'window\.Shopify',
    r'data-shopify',
    r'shopify-section'
]


class FreeShopifyDiscoverer:
    """Classe pour découvrir des sites Shopify gratuitement"""
    
    def __init__(self):
        global USE_SELENIUM
        self.session = requests.Session()
        self.found_domains: Set[str] = set()
        self.total_requests = 0
        self.selenium_driver = None
        
        # Initialiser Selenium si activé
        if USE_SELENIUM:
            try:
                self._init_selenium()
            except Exception as e:
                print(f"⚠ Impossible d'initialiser Selenium: {e}")
                print("   Le script continuera avec requests (peut être bloqué par Bing)")
                USE_SELENIUM = False
    
    def _init_selenium(self):
        """Initialise le driver Selenium avec le navigateur configuré"""
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.firefox.service import Service as FirefoxService
        from selenium.webdriver.edge.service import Service as EdgeService
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.firefox import GeckoDriverManager
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        
        print(f"  Initialisation de Selenium avec {SELENIUM_BROWSER}...")
        
        if SELENIUM_BROWSER == 'chrome':
            options = ChromeOptions()
            if SELENIUM_HEADLESS:
                options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument(f'user-agent={get_random_user_agent()}')
            # Options pour être moins détectable
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')
            # Préférences pour masquer l'automatisation
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2
            }
            options.add_experimental_option("prefs", prefs)
            
            service = ChromeService(ChromeDriverManager().install())
            self.selenium_driver = webdriver.Chrome(service=service, options=options)
            
        elif SELENIUM_BROWSER == 'firefox':
            options = FirefoxOptions()
            if SELENIUM_HEADLESS:
                options.add_argument('--headless')
            options.set_preference("general.useragent.override", get_random_user_agent())
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            
            service = FirefoxService(GeckoDriverManager().install())
            self.selenium_driver = webdriver.Firefox(service=service, options=options)
            
        elif SELENIUM_BROWSER == 'edge':
            options = EdgeOptions()
            if SELENIUM_HEADLESS:
                options.add_argument('--headless=new')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument(f'user-agent={get_random_user_agent()}')
            
            service = EdgeService(EdgeChromiumDriverManager().install())
            self.selenium_driver = webdriver.Edge(service=service, options=options)
        else:
            raise ValueError(f"Navigateur non supporté: {SELENIUM_BROWSER}")
        
        # Masquer les signaux d'automatisation avec un script plus complet
        stealth_script = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        window.chrome = {runtime: {}};
        Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})});
        """
        self.selenium_driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': stealth_script})
        
        print(f"  ✓ Selenium initialisé avec {SELENIUM_BROWSER}")
    
    def __del__(self):
        """Fermer le driver Selenium à la destruction"""
        if self.selenium_driver:
            try:
                self.selenium_driver.quit()
            except:
                pass
        
    def _make_request(self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> Optional[requests.Response]:
        """
        Fait une requête HTTP avec retry et rotation d'user agent
        Utilise Selenium si activé pour contourner les blocages
        """
        global USE_SELENIUM
        # Construire l'URL complète avec les paramètres
        if params:
            from urllib.parse import urlencode
            url_with_params = f"{url}?{urlencode(params)}"
        else:
            url_with_params = url
        
        # Utiliser Selenium si activé
        if USE_SELENIUM and self.selenium_driver:
            try:
                import random
                self.selenium_driver.get(url_with_params)
                
                # Attendre que la page se charge avec délai aléatoire (simule comportement humain)
                wait_time = random.uniform(2.5, 4.5)  # Délai aléatoire entre 2.5 et 4.5 secondes
                time.sleep(wait_time)
                
                # Attendre que les résultats de recherche se chargent (pour Bing)
                try:
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    from selenium.webdriver.common.by import By
                    # Attendre que les résultats de recherche soient présents
                    WebDriverWait(self.selenium_driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ol#b_results, #search"))
                    )
                    # Attendre un peu plus pour le chargement JavaScript
                    time.sleep(random.uniform(1.0, 2.0))
                except:
                    # Si l'attente échoue, continuer quand même
                    pass
                
                # Faire défiler un peu pour simuler un utilisateur
                self.selenium_driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                time.sleep(random.uniform(0.5, 1.0))
                
                # Récupérer le HTML
                html_content = self.selenium_driver.page_source
                
                # Créer un objet Response-like pour compatibilité
                class SeleniumResponse:
                    def __init__(self, html, status_code=200):
                        self.text = html
                        self.status_code = status_code
                        self.url = url_with_params
                
                self.total_requests += 1
                time.sleep(DELAY_BETWEEN_REQUESTS)
                return SeleniumResponse(html_content, 200)
            except Exception as e:
                print(f"    ✗ Erreur Selenium: {e}")
                # Fallback sur requests si Selenium échoue
                pass
        
        # Fallback sur requests classique
        if headers is None:
            headers = {}
        
        headers['User-Agent'] = get_random_user_agent()
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=TIMEOUT,
                    allow_redirects=True
                )
                self.total_requests += 1
                time.sleep(DELAY_BETWEEN_REQUESTS)
                return response
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(DELAY_BETWEEN_REQUESTS * (attempt + 1))
                    continue
                print(f"    ✗ Erreur: {e}")
                return None
        
        return None
    
    def extract_domains_from_text(self, text: str) -> Set[str]:
        """Extrait les domaines depuis un texte"""
        domains = set()
        
        # Pattern pour les URLs
        url_pattern = r'https?://([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'
        urls = re.findall(url_pattern, text)
        
        for url_match in urls:
            domain = url_match[0] if isinstance(url_match, tuple) else url_match
            # Nettoyer le domaine
            domain = domain.lower().strip()
            # Exclure les domaines non pertinents
            if any(excluded in domain for excluded in ['google', 'facebook', 'twitter', 'youtube', 'amazon']):
                continue
            domains.add(domain)
        
        return domains
    
    def method_1_google_dork_search(self, max_queries: int = 50) -> Set[str]:
        """
        Méthode 1: Recherche via Google avec des dorks spécifiques Shopify
        
        ATTENTION: Google limite les requêtes automatisées. Cette méthode
        peut être bloquée après quelques requêtes. Utilisez avec modération.
        """
        print("\n=== MÉTHODE 1: RECHERCHE GOOGLE DORK ===\n")
        domains = set()
        
        # Requêtes Google Dork pour Shopify
        dork_queries = [
            'site:myshopify.com',
            'inurl:myshopify.com',
            '"powered by Shopify"',
            '"Shopify.analytics"',
            'inurl:shopify.com/store',
            'site:myshopify.com/store',
            '"Shopify.theme"',
            'myshopify.com -site:myshopify.com/admin',
        ]
        
        # Ajouter des variantes avec des mots-clés
        keywords = ['shop', 'store', 'boutique', 'fashion', 'jewelry', 'electronics', 'home', 'beauty']
        for keyword in keywords[:5]:  # Limiter pour éviter trop de requêtes
            dork_queries.append(f'site:myshopify.com {keyword}')
            dork_queries.append(f'"{keyword}" myshopify.com')
        
        queries_to_test = dork_queries[:max_queries]
        print(f"  Test de {len(queries_to_test)} requêtes Google...")
        
        for i, query in enumerate(queries_to_test, 1):
            print(f"  [{i}/{len(queries_to_test)}] Recherche: '{query[:50]}...'")
            
            try:
                # Utiliser l'API de recherche Google (si disponible) ou scraper les résultats
                # Note: Google bloque souvent le scraping, donc cette méthode peut être limitée
                search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=100"
                
                response = self._make_request(search_url)
                if response and response.status_code == 200:
                    # Utiliser la méthode exhaustive d'extraction qui parse TOUT le HTML
                    page_domains = self.extract_all_myshopify_domains_from_html(response.text)
                    
                    new_domains = page_domains - domains  # Nouveaux domaines trouvés
                    domains.update(page_domains)
                    
                    if new_domains:
                        print(f"    → {len(new_domains)} nouveau(x) domaine(s) trouvé(s): {', '.join(list(new_domains)[:5])}")
                        if len(new_domains) > 5:
                            print(f"      ... et {len(new_domains) - 5} autre(s)")
                    else:
                        print(f"    → Aucun nouveau domaine trouvé (total: {len(domains)})")
                else:
                    print(f"    ⚠ Requête bloquée ou échouée (code: {response.status_code if response else 'None'})")
                    if i > 5:  # Si plusieurs échecs, arrêter pour éviter le blocage
                        print(f"    ⚠ Arrêt anticipé pour éviter le blocage Google")
                        break
                        
            except Exception as e:
                print(f"    ✗ Erreur: {e}")
                continue
        
        print(f"  ✓ Total: {len(domains)} domaines trouvés via Google\n")
        return domains
    
    def extract_all_myshopify_domains_from_html(self, html_text: str) -> Set[str]:
        """
        Extrait TOUS les domaines myshopify.com depuis le HTML brut
        Utilise plusieurs méthodes pour être exhaustif
        """
        domains = set()
        
        # D'abord, vérifier si le HTML contient vraiment des domaines myshopify.com
        if '.myshopify.com' not in html_text.lower():
            return domains  # Aucun domaine dans le HTML
        
        # Patterns pour trouver les domaines myshopify.com
        # Format: nom-store.myshopify.com
        # Pattern très permissif en premier pour capturer le maximum
        patterns = [
            r'([a-zA-Z0-9\-_]{2,})\.myshopify\.com',  # Pattern très permissif (en premier) - minimum 2 caractères
            r'([a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.myshopify\.com',  # Pattern standard
            r'([a-zA-Z0-9][a-zA-Z0-9_\-]{0,61}[a-zA-Z0-9])\.myshopify\.com',  # Avec underscores
            r'https?://([a-zA-Z0-9][a-zA-Z0-9_\-]{0,61}[a-zA-Z0-9])\.myshopify\.com',  # URLs complètes
            r'//([a-zA-Z0-9\-_]{2,})\.myshopify\.com',  # URLs avec //
            r'"([a-zA-Z0-9\-_]{2,})\.myshopify\.com"',  # Entre guillemets
            r"'([a-zA-Z0-9\-_]{2,})\.myshopify\.com'",  # Entre apostrophes
        ]
        
        # Méthode 1: Regex directe sur tout le texte avec plusieurs patterns
        for pattern in patterns:
            matches = re.findall(pattern, html_text, re.IGNORECASE)
            for match in matches:
                if match and len(match) > 1:
                    match_lower = match.lower().strip()
                    # Filtrer les domaines invalides mais être moins restrictif
                    invalid_domains = ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store', 'com', 'net', 'org', 'http', 'https']
                    if match_lower not in invalid_domains and not match_lower.startswith('http'):
                        domains.add(match_lower)
        
        # Méthode 2: Parser avec BeautifulSoup et extraire tous les liens
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Extraire tous les liens (a, href)
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href:
                    # Chercher dans l'attribut href avec plusieurs patterns
                    for pattern in patterns:
                        matches = re.findall(pattern, href, re.IGNORECASE)
                        for match in matches:
                            if match and len(match) > 1:
                                match_lower = match.lower().strip()
                                if match_lower not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store']:
                                    domains.add(match_lower)
                    
                    # Chercher aussi dans le texte du lien
                    link_text = link.get_text()
                    for pattern in patterns[:2]:  # Utiliser seulement les 2 premiers patterns pour le texte
                        matches = re.findall(pattern, link_text, re.IGNORECASE)
                        for match in matches:
                            if match and len(match) > 1:
                                match_lower = match.lower().strip()
                                if match_lower not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store']:
                                    domains.add(match_lower)
            
            # Extraire depuis tous les attributs qui pourraient contenir des URLs
            for element in soup.find_all(True):  # Tous les éléments
                for attr_name, attr_value in element.attrs.items():
                    if isinstance(attr_value, str) and 'myshopify.com' in attr_value:
                        for pattern in patterns:
                            matches = re.findall(pattern, attr_value, re.IGNORECASE)
                            for match in matches:
                                if match and len(match) > 1:
                                    match_lower = match.lower().strip()
                                    if match_lower not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store']:
                                        domains.add(match_lower)
                    elif isinstance(attr_value, list):
                        for item in attr_value:
                            if isinstance(item, str) and 'myshopify.com' in item:
                                for pattern in patterns:
                                    matches = re.findall(pattern, item, re.IGNORECASE)
                                    for match in matches:
                                        if match and len(match) > 1:
                                            match_lower = match.lower().strip()
                                            if match_lower not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store']:
                                                domains.add(match_lower)
        except Exception as e:
            pass  # Si le parsing échoue, on continue avec les résultats de la regex
        
        # Méthode 3: Extraction spécifique pour les résultats de recherche Bing
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Bing structure ses résultats dans des <li class="b_algo">
            result_items = soup.find_all('li', class_='b_algo')
            for item in result_items:
                # Chercher dans les liens de résultats
                for link in item.find_all('a', href=True):
                    href = link.get('href', '')
                    # Extraire depuis l'URL
                    for pattern in patterns:
                        matches = re.findall(pattern, href, re.IGNORECASE)
                        for match in matches:
                            if match and len(match) > 1:
                                match_lower = match.lower().strip()
                                if match_lower not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store']:
                                    domains.add(match_lower)
                
                # Chercher aussi dans le texte visible du résultat
                result_text = item.get_text()
                for pattern in patterns[:2]:
                    matches = re.findall(pattern, result_text, re.IGNORECASE)
                    for match in matches:
                        if match and len(match) > 1:
                            match_lower = match.lower().strip()
                            if match_lower not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store']:
                                domains.add(match_lower)
        except Exception as e:
            pass
        
        # Méthode 4: Extraction depuis les citations et snippets
        try:
            # Chercher dans les citations (Bing utilise parfois des citations)
            citations = soup.find_all('cite')
            for cite in citations:
                cite_text = cite.get_text()
                for pattern in patterns:
                    matches = re.findall(pattern, cite_text, re.IGNORECASE)
                    for match in matches:
                        if match and len(match) > 1:
                            match_lower = match.lower().strip()
                            if match_lower not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store']:
                                domains.add(match_lower)
        except Exception as e:
            pass
        
        # Méthode 5: Extraction de secours ultra-agressive (si rien n'a été trouvé)
        # Cette méthode est utilisée si les autres échouent
        if len(domains) == 0:
            # Pattern ultra-permissif qui capture TOUT ce qui précède .myshopify.com
            fallback_pattern = r'([a-zA-Z0-9\-_]{1,})\.myshopify\.com'
            fallback_matches = re.findall(fallback_pattern, html_text, re.IGNORECASE)
            for match in fallback_matches:
                if match and len(match) > 0:
                    match_lower = match.lower().strip()
                    # Filtrer seulement les pires cas
                    if match_lower not in ['www', 'admin', 'cdn', 'login', 'api']:
                        domains.add(match_lower)
        
        return domains
    
    def method_2_bing_search(self, max_queries: int = 30, max_pages_per_query: int = 10) -> Set[str]:
        """
        Méthode 2: Recherche via Bing avec parsing exhaustif et pagination
        Parcourt toutes les pages de résultats pour chaque requête
        """
        print("\n=== MÉTHODE 2: RECHERCHE BING (AVEC PAGINATION) ===\n")
        domains = set()
        
        queries = [
            'site:myshopify.com',
            'myshopify.com store',
            '"powered by Shopify"',
            'shopify store',
            'myshopify.com',
            'shopify online store',
            'shopify ecommerce',
            'myshopify.com -admin',
            'inurl:myshopify.com',
            'shopify boutique',
            'shopify shop',
            'myshopify.com -login',
            'myshopify.com -admin -login',
        ]
        
        queries_to_test = queries[:max_queries]
        print(f"  Test de {len(queries_to_test)} requêtes Bing avec jusqu'à {max_pages_per_query} pages chacune...")
        
        for i, query in enumerate(queries_to_test, 1):
            print(f"\n  [{i}/{len(queries_to_test)}] Recherche: '{query}'")
            query_domains = set()
            
            # Parcourir exactement 100 pages pour chaque filtre
            for page in range(0, max_pages_per_query):
                try:
                    # Bing utilise first= pour la pagination (0, 10, 20, 30, etc.)
                    # Augmenter le nombre de résultats par page pour plus d'efficacité
                    first_result = page * 20  # 20 résultats par page au lieu de 10
                    search_url = f"https://www.bing.com/search?q={quote_plus(query)}&count=20&first={first_result}"
                    
                    response = self._make_request(search_url)
                    if response and response.status_code == 200:
                        # Debug: vérifier la taille de la réponse
                        html_size = len(response.text)
                        
                        # Extraire TOUS les domaines myshopify.com depuis le HTML complet
                        page_domains = self.extract_all_myshopify_domains_from_html(response.text)
                        
                        # Extraction de secours si rien n'a été trouvé (fallback ultra-permissif)
                        if len(page_domains) == 0:
                            # Essayer une extraction ultra-basique directement depuis le texte brut
                            fallback_extraction = re.findall(r'([a-zA-Z0-9\-_]{2,})\.myshopify\.com', response.text, re.IGNORECASE)
                            for match in fallback_extraction:
                                if match and len(match) > 1:
                                    match_lower = match.lower().strip()
                                    if match_lower not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store', 'com', 'net', 'org']:
                                        page_domains.add(match_lower)
                        
                        new_domains = page_domains - query_domains
                        query_domains.update(page_domains)
                        
                        if new_domains:
                            print(f"    Page {page + 1}/{max_pages_per_query}: {len(new_domains)} nouveau(x) domaine(s) trouvé(s) (HTML: {html_size} chars)")
                            # Afficher quelques exemples
                            if len(new_domains) <= 5:
                                print(f"      → {', '.join(list(new_domains))}")
                            else:
                                print(f"      → Exemples: {', '.join(list(new_domains)[:5])}...")
                        else:
                            print(f"    Page {page + 1}/{max_pages_per_query}: Aucun nouveau domaine (HTML: {html_size} chars, domaines trouvés sur page: {len(page_domains)})")
                            # Si aucune extraction, peut-être un problème de parsing
                            if len(page_domains) == 0 and html_size > 10000:
                                # Essayer une extraction basique pour debug
                                basic_matches = len(re.findall(r'\.myshopify\.com', response.text, re.IGNORECASE))
                                if basic_matches > 0:
                                    print(f"      ⚠ {basic_matches} occurrences de '.myshopify.com' trouvées mais non extraites!")
                                    # Essayer d'extraire manuellement avec pattern ultra-permissif
                                    all_myshopify = re.findall(r'([a-zA-Z0-9\-_]{2,})\.myshopify\.com', response.text, re.IGNORECASE)
                                    unique_found = set([m.lower().strip() for m in all_myshopify if m and len(m) > 1])
                                    # Filtrer les domaines invalides
                                    valid_domains = [d for d in unique_found if d not in ['www', 'admin', 'cdn', 'login', 'api', 'shop', 'store', 'com', 'net', 'org']]
                                    print(f"      → Extraction manuelle: {len(valid_domains)} domaines valides trouvés (sur {len(unique_found)} total)")
                                    if len(valid_domains) > 0:
                                        print(f"      → Exemples: {', '.join(list(valid_domains)[:10])}")
                                        # Ajouter ces domaines
                                        for domain in valid_domains:
                                            page_domains.add(domain)
                                        new_domains = page_domains - query_domains
                                        query_domains.update(page_domains)
                                        if new_domains:
                                            print(f"      ✓ {len(new_domains)} domaines ajoutés via extraction manuelle")
                                else:
                                    # Vérifier si Bing a bloqué ou retourné une page différente
                                    if 'captcha' in response.text.lower() or 'verify' in response.text.lower() or 'challenge' in response.text.lower():
                                        print(f"      ⚠ CAPTCHA/vérification détectée - Bing bloque peut-être les requêtes automatisées")
                                    elif 'b_algo' not in response.text and 'b_search' not in response.text:
                                        print(f"      ⚠ Structure HTML Bing non détectée - peut-être une page d'erreur")
                                        # Sauvegarder un échantillon pour debug (premiers 2000 chars)
                                        debug_sample = response.text[:2000]
                                        if 'myshopify' in debug_sample.lower():
                                            print(f"      → 'myshopify' trouvé dans l'échantillon, mais format peut-être différent")
                                    else:
                                        # Vérifier si les résultats sont chargés via JavaScript
                                        if 'b_algo' in response.text:
                                            result_count = response.text.count('b_algo')
                                            print(f"      ⚠ {result_count} résultats 'b_algo' trouvés mais aucun domaine extrait")
                                            print(f"      → Les domaines peuvent être dans du JavaScript ou un format non standard")
                                        
                                        # Sauvegarder un échantillon HTML pour debug si activé
                                        if DEBUG_SAVE_HTML and page == 0:  # Seulement pour la première page
                                            debug_file = os.path.join(OUTPUT_DIR, f'debug_bing_page_{query.replace(":", "_")[:20]}.html')
                                            try:
                                                with open(debug_file, 'w', encoding='utf-8') as f:
                                                    f.write(response.text)
                                                print(f"      → HTML sauvegardé dans {debug_file} pour inspection")
                                            except:
                                                pass
                        
                        # Continuer jusqu'à atteindre max_pages_per_query pages, peu importe les résultats
                    else:
                        # Si erreur, continuer quand même (peut être temporaire)
                        print(f"    ⚠ Page {page + 1}/{max_pages_per_query}: Erreur HTTP {response.status_code if response else 'None'}, continuation...")
                        continue
                        
                except Exception as e:
                    print(f"    ⚠ Erreur page {page + 1}: {e}")
                    break
            
            # Ajouter les domaines trouvés pour cette requête
            new_query_domains = query_domains - domains
            domains.update(query_domains)
            
            if new_query_domains:
                print(f"  → Total pour cette requête: {len(query_domains)} domaines ({len(new_query_domains)} nouveaux)")
            else:
                print(f"  → Total pour cette requête: {len(query_domains)} domaines (tous déjà connus)")
        
        print(f"\n  ✓ Total: {len(domains)} domaines trouvés via Bing\n")
        return domains
    
    def method_2_duckduckgo_search(self, max_queries: int = 30, max_pages_per_query: int = 10) -> Set[str]:
        """
        Méthode 2: Recherche via DuckDuckGo avec parsing exhaustif et pagination
        """
        print("\n=== MÉTHODE 2: RECHERCHE DUCKDUCKGO (AVEC PAGINATION) ===\n")
        domains = set()
        
        queries = [
            'site:myshopify.com',
            'myshopify.com store',
            '"powered by Shopify"',
            'shopify store',
            'myshopify.com',
            'shopify online store',
            'shopify ecommerce',
            'myshopify.com -admin',
            'inurl:myshopify.com',
            'shopify boutique',
            'shopify shop',
        ]
        
        queries_to_test = queries[:max_queries]
        print(f"  Test de {len(queries_to_test)} requêtes DuckDuckGo avec jusqu'à {max_pages_per_query} pages chacune...")
        
        for i, query in enumerate(queries_to_test, 1):
            print(f"\n  [{i}/{len(queries_to_test)}] Recherche: '{query}'")
            query_domains = set()
            
            # Parcourir exactement 100 pages pour chaque filtre
            for page in range(max_pages_per_query):
                try:
                    # DuckDuckGo utilise s= pour la pagination
                    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}&s={page * 20}"
                    
                    response = self._make_request(search_url)
                    if response and response.status_code == 200:
                        if len(response.text) < 1000:
                            print(f"    ⚠ Page {page + 1}/{max_pages_per_query}: Réponse très courte, peut-être un CAPTCHA")
                            continue
                        
                        # Utiliser la méthode exhaustive d'extraction
                        page_domains = self.extract_all_myshopify_domains_from_html(response.text)
                        
                        new_domains = page_domains - query_domains
                        query_domains.update(page_domains)
                        
                        if new_domains:
                            print(f"    Page {page + 1}/{max_pages_per_query}: {len(new_domains)} nouveau(x) domaine(s) trouvé(s)")
                        else:
                            print(f"    Page {page + 1}/{max_pages_per_query}: Aucun nouveau domaine")
                        
                        # Continuer jusqu'à atteindre max_pages_per_query pages, peu importe les résultats
                    else:
                        # Si erreur, continuer quand même (peut être temporaire)
                        print(f"    ⚠ Page {page + 1}/{max_pages_per_query}: Erreur HTTP {response.status_code if response else 'None'}, continuation...")
                        continue
                        
                except Exception as e:
                    print(f"    ⚠ Erreur page {page + 1}: {e}")
                    break
            
            # Ajouter les domaines trouvés pour cette requête
            new_query_domains = query_domains - domains
            domains.update(query_domains)
            
            if new_query_domains:
                print(f"  → Total pour cette requête: {len(query_domains)} domaines ({len(new_query_domains)} nouveaux)")
            else:
                print(f"  → Total pour cette requête: {len(query_domains)} domaines (tous déjà connus)")
        
        print(f"\n  ✓ Total: {len(domains)} domaines trouvés via DuckDuckGo\n")
        return domains
    
    def method_3_shop_app_scraping(self, max_pages: int = 100) -> Set[str]:
        """
        Méthode 3: Scraping de shop.app (annuaire de sites Shopify)
        """
        print("\n=== MÉTHODE 3: SCRAPING DE SHOP.APP ===\n")
        domains = set()
        
        print(f"  Scraping de shop.app (max {max_pages} pages)...")
        
        # shop.app liste des sites Shopify par catégorie et par page
        base_urls = [
            'https://shop.app/discover',
            'https://shop.app/discover/popular',
            'https://shop.app/discover/new',
        ]
        
        # Catégories populaires
        categories = ['fashion', 'electronics', 'home', 'beauty', 'sports', 'food', 'books']
        
        for category in categories:
            base_urls.append(f'https://shop.app/discover/{category}')
        
        for base_url in base_urls:
            try:
                print(f"  Scraping: {base_url}")
                response = self._make_request(base_url)
                
                if response and response.status_code == 200:
                    # Méthode 1: Extraire TOUS les domaines myshopify.com depuis le HTML complet
                    page_domains = self.extract_all_myshopify_domains_from_html(response.text)
                    domains.update(page_domains)
                    
                    # Méthode 2: Extraire les noms de stores depuis les URLs /store/
                    store_pattern = r'/store/([a-zA-Z0-9-]+)'
                    
                    # Chercher dans le texte brut avec regex
                    matches = re.findall(store_pattern, response.text)
                    for match in matches:
                        if match and len(match) > 1:
                            domains.add(match)
                    
                    # Chercher aussi dans les liens HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        match = re.search(store_pattern, href)
                        if match:
                            store_name = match.group(1)
                            if store_name and len(store_name) > 1:
                                domains.add(store_name)
                    
            except Exception as e:
                print(f"    ✗ Erreur: {e}")
                continue
        
        print(f"  ✓ Total: {len(domains)} domaines trouvés via shop.app\n")
        return domains
    
    def method_4_public_lists(self) -> Set[str]:
        """
        Méthode 4: Utilisation de listes publiques de sites Shopify
        
        Recherche et extrait des domaines depuis des listes publiques,
        forums, GitHub, etc.
        """
        print("\n=== MÉTHODE 4: LISTES PUBLIQUES ===\n")
        domains = set()
        
        # URLs de listes publiques potentielles
        public_sources = [
            'https://github.com/search?q=myshopify.com',
            'https://github.com/search?q=shopify+store',
        ]
        
        print(f"  Recherche dans {len(public_sources)} sources publiques...")
        
        for source_url in public_sources:
            try:
                print(f"  Scraping: {source_url}")
                response = self._make_request(source_url)
                
                if response and response.status_code == 200:
                    # Extraire les domaines du texte
                    page_domains = self.extract_domains_from_text(response.text)
                    domains.update(page_domains)
                    
            except Exception as e:
                print(f"    ✗ Erreur: {e}")
                continue
        
        print(f"  ✓ Total: {len(domains)} domaines trouvés via listes publiques\n")
        return domains
    
    def discover_all(self, methods: Optional[List[str]] = None) -> Set[str]:
        """
        Exécute toutes les méthodes de découverte
        
        Args:
            methods: Liste des méthodes à exécuter (None = toutes)
                    Options: 'google', 'bing', 'duckduckgo', 'shopapp', 'public'
        """
        if methods is None:
            methods = ['bing', 'shopapp']  # Par défaut, utiliser Bing (plus fiable) et shop.app
        
        all_domains = set()
        
        print("=" * 70)
        print("DÉCOUVERTE GRATUITE DE SITES SHOPIFY")
        print("=" * 70)
        print(f"\nMéthodes activées: {', '.join(methods)}")
        print(f"Maximum de résultats: {MAX_RESULTS}")
        print(f"Délai entre requêtes: {DELAY_BETWEEN_REQUESTS}s\n")
        
        if 'google' in methods:
            google_domains = self.method_1_google_dork_search(max_queries=20)
            all_domains.update(google_domains)
        
        if 'bing' in methods:
            bing_domains = self.method_2_bing_search(max_queries=20, max_pages_per_query=MAX_PAGES_PER_QUERY)
            all_domains.update(bing_domains)
        
        if 'duckduckgo' in methods:
            ddg_domains = self.method_2_duckduckgo_search(max_queries=30, max_pages_per_query=MAX_PAGES_PER_QUERY)
            all_domains.update(ddg_domains)
        
        if 'shopapp' in methods:
            shopapp_domains = self.method_3_shop_app_scraping(max_pages=50)
            all_domains.update(shopapp_domains)
        
        if 'public' in methods:
            public_domains = self.method_4_public_lists()
            all_domains.update(public_domains)
        
        # Limiter le nombre de résultats
        if len(all_domains) > MAX_RESULTS:
            all_domains = set(list(all_domains)[:MAX_RESULTS])
        
        print("=" * 70)
        print(f"RÉSULTATS FINAUX")
        print("=" * 70)
        print(f"Total de domaines uniques trouvés: {len(all_domains)}")
        print(f"Total de requêtes effectuées: {self.total_requests}")
        print("=" * 70)
        
        return all_domains


def main():
    """Point d'entrée principal"""
    discoverer = FreeShopifyDiscoverer()
    
    # Méthodes à utiliser (modifiez selon vos besoins)
    # Options: 'google', 'bing', 'duckduckgo', 'shopapp', 'public'
    # Note: 'google' peut être bloqué rapidement, 'bing' est généralement plus fiable
    methods = ['bing', 'shopapp']
    
    # Découvrir les sites
    domains = discoverer.discover_all(methods=methods)
    
    print(f"\n{'='*70}")
    print(f"SAUVEGARDE DES RÉSULTATS")
    print(f"{'='*70}")
    print(f"Domaines trouvés (bruts): {len(domains)}")
    
    # Convertir les noms de stores en domaines complets si nécessaire
    full_domains = set()
    for domain in domains:
        domain = str(domain).strip().lower()
        if not domain or len(domain) == 0:
            continue
        
        # Filtrer les domaines invalides
        if domain in ['www', 'admin', 'cdn', 'shop', 'store', 'app', 'login']:
            continue
        
        # Si c'est déjà un domaine complet avec myshopify.com
        if 'myshopify.com' in domain:
            # Nettoyer le domaine (enlever http://, https://, etc.)
            domain = domain.replace('https://', '').replace('http://', '').replace('www.', '')
            if domain.startswith('//'):
                domain = domain[2:]
            if domain.endswith('/'):
                domain = domain[:-1]
            # Extraire juste le nom du store.myshopify.com
            match = re.search(r'([a-zA-Z0-9-]+)\.myshopify\.com', domain)
            if match:
                store_name = match.group(1)
                if store_name and len(store_name) > 1:
                    full_domains.add(f"{store_name}.myshopify.com")
        # Si c'est juste un nom de store (sans point), ajouter .myshopify.com
        elif '.' not in domain and len(domain) < 50 and len(domain) > 0:
            full_domains.add(f"{domain}.myshopify.com")
        # Sinon, essayer d'ajouter .myshopify.com si c'est un nom valide
        elif len(domain) < 50 and len(domain) > 0:
            # Vérifier que ce n'est pas déjà un domaine complet
            if not any(ext in domain for ext in ['.com', '.net', '.org', '.io']):
                full_domains.add(f"{domain}.myshopify.com")
    
    print(f"Domaines après nettoyage: {len(full_domains)}")
    
    # Sauvegarder les résultats
    output_path = OUTPUT_FILE
    # S'assurer que le dossier existe
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    if full_domains:
        with open(output_path, 'w', encoding='utf-8') as f:
            for domain in sorted(full_domains):
                if domain.strip():  # Ne pas écrire de lignes vides
                    f.write(f"{domain.strip()}\n")
        
        print(f"\n✓ {len(full_domains)} domaine(s) sauvegardé(s) dans {output_path}")
        if len(full_domains) <= 10:
            print(f"   Tous les domaines: {', '.join(sorted(full_domains))}")
        else:
            print(f"   Exemples: {', '.join(list(sorted(full_domains))[:10])}...")
    else:
        print(f"\n⚠ Aucun domaine valide à sauvegarder.")
        print(f"   Les domaines trouvés étaient peut-être invalides ou mal formatés.")
        # Créer quand même le fichier vide
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("")


if __name__ == '__main__':
    main()

