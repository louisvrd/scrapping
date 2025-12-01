"""
Module de scraping de shop.app pour découvrir des sites Shopify
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Set
import time
import re
from urllib.parse import urlparse, urljoin, quote_plus
from fake_useragent import UserAgent

from config import DELAY_BETWEEN_REQUESTS, TIMEOUT, USE_SELENIUM


class ShopAppScraper:
    """Classe pour scraper shop.app et découvrir des sites Shopify"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        # Headers complets pour simuler un vrai navigateur
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        self.found_urls: Set[str] = set()
        self.base_url = 'https://shop.app'
    
    def search_shops(self, query: str = "", category: str = "", page: int = 1) -> List[str]:
        """
        Recherche des boutiques sur shop.app en utilisant les filtres de recherche
        
        Args:
            query: Terme de recherche
            category: Catégorie à filtrer
            page: Numéro de page (pour la pagination)
            
        Returns:
            Liste d'URLs de sites Shopify trouvés
        """
        urls = []
        
        try:
            # Construire l'URL de recherche
            search_params = []
            if query:
                search_params.append(f"q={quote_plus(query)}")
            if category:
                search_params.append(f"category={quote_plus(category)}")
            if page > 1:
                search_params.append(f"page={page}")
            
            search_url = f"{self.base_url}/search"
            if search_params:
                search_url += "?" + "&".join(search_params)
            
            print(f"  Recherche: {search_url}")
            
            headers = {
                'Referer': self.base_url,
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-Mode': 'navigate',
            }
            
            response = self.session.get(search_url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
            
            if response.status_code == 403:
                print("  Erreur 403, tentative avec approche alternative...")
                import requests as req_module
                alt_headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
                response = req_module.get(search_url, headers=alt_headers, timeout=TIMEOUT, allow_redirects=True)
            
            response.raise_for_status()
            
            if not response.text or len(response.text) < 100:
                print("  Avertissement: Réponse très courte")
                return urls
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extraire les URLs des boutiques
            urls.extend(self._extract_shop_urls_from_page(soup))
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except requests.HTTPError as e:
            if '403' in str(e):
                print(f"  Erreur 403: {e}")
            else:
                print(f"Erreur HTTP lors de la recherche: {e}")
        except Exception as e:
            print(f"Erreur lors de la recherche: {e}")
        
        unique_urls = list(set(urls))
        print(f"  → {len(unique_urls)} URLs trouvées")
        return unique_urls
    
    def _extract_shop_urls_from_page(self, soup: BeautifulSoup) -> List[str]:
        """
        Extrait les URLs des boutiques depuis une page HTML de shop.app
        
        Args:
            soup: Objet BeautifulSoup de la page
            
        Returns:
            Liste d'URLs trouvées
        """
        urls = []
        
        # Méthode 1: Rechercher tous les liens
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '').strip()
            if not href:
                continue
            
            # Convertir les URLs relatives en absolues
            if href.startswith('/'):
                href = urljoin(self.base_url, href)
            elif not href.startswith(('http://', 'https://')):
                continue
            
            # Ignorer les URLs d'images
            if self._is_image_url(href):
                continue
            
            # Filtrer les liens shop.app qui pointent vers des boutiques
            if 'shop.app' in href and ('/shop/' in href or href.count('/') >= 3):
                shop_url = self._extract_shop_url_from_link(href)
                if shop_url and self._is_valid_shopify_url(shop_url) and not self._is_image_url(shop_url):
                    urls.append(shop_url)
                    self.found_urls.add(shop_url)
            # Liens directs vers des sites externes
            elif not 'shop.app' in href and self._is_valid_shopify_url(href) and not self._is_image_url(href):
                urls.append(href)
                self.found_urls.add(href)
        
        # Méthode 2: Rechercher dans les attributs data-*
        shop_elements = soup.find_all(attrs={'data-shop-url': True})
        for elem in shop_elements:
            shop_url = elem.get('data-shop-url', '')
            if shop_url and self._is_valid_shopify_url(shop_url) and not self._is_image_url(shop_url):
                urls.append(shop_url)
                self.found_urls.add(shop_url)
        
        # Méthode 3: Recherche par regex dans le HTML
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.(?:myshopify\.com|com|net|org|io)[^\s<>"{}|\\^`\[\]]*'
        html_text = str(soup)
        found_urls = re.findall(url_pattern, html_text)
        for found_url in found_urls:
            clean_url = found_url.split('&')[0].split('"')[0].split("'")[0].split(')')[0].split(']')[0]
            # Filtrer les images et vérifier la validité
            if (self._is_valid_shopify_url(clean_url) and 'shop.app' not in clean_url 
                and not self._is_image_url(clean_url)):
                urls.append(clean_url)
                self.found_urls.add(clean_url)
        
        # Méthode 4: Rechercher dans les scripts JSON
        script_tags = soup.find_all('script', type='application/json')
        for script in script_tags:
            try:
                import json
                data = json.loads(script.string)
                urls.extend(self._extract_urls_from_json(data))
            except:
                pass
        
        return urls
    
    def scrape_categories_page(self) -> List[str]:
        """
        Scrape la page des catégories pour trouver des liens vers des sites Shopify
        
        Returns:
            Liste d'URLs de sites Shopify trouvés
        """
        urls = []
        
        try:
            # D'abord visiter la page d'accueil pour établir une session
            print(f"Établissement de la session avec {self.base_url}...")
            try:
                home_response = self.session.get(
                    self.base_url,
                    timeout=TIMEOUT,
                    allow_redirects=True
                )
                time.sleep(1)  # Petit délai pour simuler un comportement humain
            except:
                pass  # Continuer même si la page d'accueil échoue
            
            print(f"Scraping de {self.base_url}/categories...")
            # Mettre à jour les headers pour la requête spécifique
            headers = {
                'Referer': self.base_url,
                'Sec-Fetch-Site': 'same-origin',
            }
            response = self.session.get(
                f"{self.base_url}/categories",
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=True
            )
            
            # Si on obtient toujours un 403, essayer avec une approche différente
            if response.status_code == 403:
                print("  Erreur 403 détectée, tentative avec approche alternative...")
                # Essayer sans session pour éviter les cookies problématiques
                import requests as req_module
                alt_headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                response = req_module.get(
                    f"{self.base_url}/categories",
                    headers=alt_headers,
                    timeout=TIMEOUT,
                    allow_redirects=True
                )
                
                # Si ça ne fonctionne toujours pas, lever une exception pour utiliser Selenium
                if response.status_code == 403:
                    raise requests.HTTPError(f"403 Forbidden - Le site bloque les requêtes automatisées. Essayez d'activer Selenium dans config.py")
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Méthode 1: Rechercher tous les liens (approche large)
            all_links = soup.find_all('a', href=True)
            print(f"  Trouvé {len(all_links)} liens sur la page")
            
            for link in all_links:
                href = link.get('href', '').strip()
                if not href:
                    continue
                
                # Convertir les URLs relatives en absolues
                if href.startswith('/'):
                    href = urljoin(self.base_url, href)
                elif not href.startswith(('http://', 'https://')):
                    continue
                
                # Filtrer les liens shop.app internes qui pointent vers des boutiques
                # Format possible: https://shop.app/shop/nom-boutique ou https://shop.app/nom-boutique
                if 'shop.app' in href and ('/shop/' in href or href.count('/') >= 3):
                    # C'est probablement un lien vers une boutique
                    shop_url = self._extract_shop_url_from_link(href)
                    if shop_url and self._is_valid_shopify_url(shop_url):
                        urls.append(shop_url)
                        self.found_urls.add(shop_url)
                # Liens directs vers des sites externes
                elif not 'shop.app' in href and self._is_valid_shopify_url(href):
                    urls.append(href)
                    self.found_urls.add(href)
            
            # Méthode 1b: Rechercher dans les divs/cards de boutiques
            # shop.app peut utiliser des structures comme <div data-shop-url="...">
            shop_elements = soup.find_all(attrs={'data-shop-url': True})
            for elem in shop_elements:
                shop_url = elem.get('data-shop-url', '')
                if shop_url and self._is_valid_shopify_url(shop_url):
                    urls.append(shop_url)
                    self.found_urls.add(shop_url)
            
            # Méthode 1c: Rechercher dans les images avec des liens
            img_links = soup.find_all('img', src=True)
            for img in img_links:
                parent = img.find_parent('a')
                if parent and parent.get('href'):
                    href = parent.get('href', '')
                    if href.startswith('/'):
                        href = urljoin(self.base_url, href)
                    if 'shop.app' in href:
                        shop_url = self._extract_shop_url_from_link(href)
                        if shop_url and self._is_valid_shopify_url(shop_url):
                            urls.append(shop_url)
                            self.found_urls.add(shop_url)
            
            # Méthode 2: Recherche par regex dans le HTML
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.(?:myshopify\.com|com|net|org|io)[^\s<>"{}|\\^`\[\]]*'
            found_urls = re.findall(url_pattern, response.text)
            for found_url in found_urls:
                # Nettoyer l'URL
                clean_url = found_url.split('&')[0].split('"')[0].split("'")[0].split(')')[0].split(']')[0]
                if self._is_valid_shopify_url(clean_url) and 'shop.app' not in clean_url:
                    urls.append(clean_url)
                    self.found_urls.add(clean_url)
            
            # Méthode 3: Rechercher dans les données JSON (si la page utilise du JavaScript)
            script_tags = soup.find_all('script', type='application/json')
            for script in script_tags:
                try:
                    import json
                    data = json.loads(script.string)
                    # Rechercher récursivement dans les données JSON
                    urls.extend(self._extract_urls_from_json(data))
                except:
                    pass
            
            # Méthode 4: Rechercher dans les attributs data-*
            data_attrs = soup.find_all(attrs=lambda x: x and any(k.startswith('data-') for k in x.keys()))
            for elem in data_attrs:
                for attr_name, attr_value in elem.attrs.items():
                    if isinstance(attr_value, str) and ('shopify' in attr_value.lower() or 'http' in attr_value):
                        if (self._is_valid_shopify_url(attr_value) and not self._is_image_url(attr_value)):
                            urls.append(attr_value)
                            self.found_urls.add(attr_value)
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            print(f"Erreur lors du scraping de shop.app/categories: {e}")
        
        unique_urls = list(self.found_urls)
        print(f"  → {len(unique_urls)} URLs trouvées sur la page des catégories")
        return unique_urls
    
    def scrape_category_pages(self, max_categories: int = 50) -> List[str]:
        """
        Scrape les pages de catégories individuelles pour trouver plus de sites
        
        Args:
            max_categories: Nombre maximum de catégories à scraper
            
        Returns:
            Liste d'URLs de sites Shopify trouvés
        """
        all_urls = []
        
        try:
            # D'abord, obtenir la liste des catégories
            response = self.session.get(
                f"{self.base_url}/categories",
                timeout=TIMEOUT
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Trouver les liens vers les catégories
            category_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/categories/' in href or '/category/' in href:
                    if href.startswith('/'):
                        href = urljoin(self.base_url, href)
                    if href not in category_links:
                        category_links.append(href)
            
            print(f"Trouvé {len(category_links)} catégories, scraping des premières...")
            
            # Scraper chaque page de catégorie
            for i, category_url in enumerate(category_links[:max_categories]):
                try:
                    print(f"  Scraping catégorie {i+1}/{min(len(category_links), max_categories)}: {category_url}")
                    category_urls = self._scrape_category_page(category_url)
                    all_urls.extend(category_urls)
                    time.sleep(DELAY_BETWEEN_REQUESTS)
                except Exception as e:
                    print(f"    Erreur: {e}")
                    continue
            
        except Exception as e:
            print(f"Erreur lors du scraping des catégories: {e}")
        
        unique_urls = list(set(all_urls))
        print(f"  → {len(unique_urls)} URLs uniques trouvées dans les catégories")
        return unique_urls
    
    def _scrape_category_page(self, category_url: str) -> List[str]:
        """
        Scrape une page de catégorie spécifique
        
        Args:
            category_url: URL de la page de catégorie
            
        Returns:
            Liste d'URLs trouvées
        """
        urls = []
        
        try:
            response = self.session.get(category_url, timeout=TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Rechercher les liens vers les boutiques
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href.startswith('/'):
                    href = urljoin(self.base_url, href)
                
                # Ignorer les URLs d'images
                if self._is_image_url(href):
                    continue
                
                if 'shop.app' in href:
                    shop_url = self._extract_shop_url_from_link(href)
                    if shop_url and self._is_valid_shopify_url(shop_url) and not self._is_image_url(shop_url):
                        urls.append(shop_url)
                        self.found_urls.add(shop_url)
                elif self._is_valid_shopify_url(href) and not self._is_image_url(href):
                    urls.append(href)
                    self.found_urls.add(href)
            
            # Recherche par regex
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.(?:myshopify\.com|com|net|org|io)[^\s<>"{}|\\^`\[\]]*'
            found_urls = re.findall(url_pattern, response.text)
            for found_url in found_urls:
                clean_url = found_url.split('&')[0].split('"')[0].split("'")[0]
                if (self._is_valid_shopify_url(clean_url) and 'shop.app' not in clean_url 
                    and not self._is_image_url(clean_url)):
                    urls.append(clean_url)
                    self.found_urls.add(clean_url)
        
        except Exception as e:
            print(f"    Erreur lors du scraping de {category_url}: {e}")
        
        return urls
    
    def _extract_shop_url_from_link(self, shop_app_link: str) -> str:
        """
        Extrait l'URL réelle du site depuis un lien shop.app
        Les liens shop.app peuvent rediriger vers le vrai site
        
        Args:
            shop_app_link: Lien vers shop.app
            
        Returns:
            URL du site réel ou None
        """
        try:
            # Suivre la redirection
            response = self.session.get(shop_app_link, timeout=TIMEOUT, allow_redirects=True)
            final_url = response.url
            
            # Si la redirection nous mène vers un site externe, c'est bon
            if 'shop.app' not in final_url:
                return final_url
            
            # Sinon, essayer d'extraire depuis le HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Chercher des meta tags de redirection
            meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if meta_refresh:
                content = meta_refresh.get('content', '')
                url_match = re.search(r'url=([^\s]+)', content, re.I)
                if url_match:
                    return url_match.group(1)
            
            # Chercher un lien "Visit Store" ou similaire
            visit_links = soup.find_all('a', href=True, string=re.compile(r'visit|store|shop|boutique', re.I))
            for link in visit_links:
                href = link.get('href', '')
                if href and 'shop.app' not in href and self._is_valid_shopify_url(href):
                    return href
            
            # Chercher dans les scripts (données JSON)
            scripts = soup.find_all('script')
            for script in scripts:
                script_text = script.string or ''
                # Chercher des patterns d'URL dans les scripts
                url_matches = re.findall(r'https?://[^\s"\'<>\)]+', script_text)
                for url_match in url_matches:
                    if 'shop.app' not in url_match and self._is_valid_shopify_url(url_match):
                        # Nettoyer l'URL
                        clean_url = url_match.rstrip('.,;:!?)')
                        return clean_url
        
        except Exception as e:
            pass
        
        return None
    
    def _extract_urls_from_json(self, data: any, urls: List[str] = None) -> List[str]:
        """
        Extrait récursivement les URLs d'une structure JSON
        
        Args:
            data: Données JSON (dict, list, ou str)
            urls: Liste accumulée d'URLs
            
        Returns:
            Liste d'URLs trouvées
        """
        if urls is None:
            urls = []
        
        if isinstance(data, dict):
            for value in data.values():
                self._extract_urls_from_json(value, urls)
        elif isinstance(data, list):
            for item in data:
                self._extract_urls_from_json(item, urls)
        elif isinstance(data, str):
            # Vérifier si c'est une URL
            if data.startswith(('http://', 'https://')):
                if self._is_valid_shopify_url(data) and 'shop.app' not in data:
                    urls.append(data)
                    self.found_urls.add(data)
        
        return urls
    
    def _is_image_url(self, url: str) -> bool:
        """
        Vérifie si une URL pointe vers une image
        
        Args:
            url: URL à vérifier
            
        Returns:
            True si l'URL est une image
        """
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Extensions d'images courantes
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico', 
                           '.tiff', '.tif', '.heic', '.avif', '.jfif']
        if any(url_lower.endswith(ext) for ext in image_extensions):
            return True
        
        # Vérifier les paramètres d'image dans l'URL
        image_params = ['?width=', '?height=', '?format=', '?image=', '?img=', 
                       '&width=', '&height=', '&format=', '&image=', '&img=',
                       '/image/', '/images/', '/img/', '/photo/', '/photos/']
        if any(param in url_lower for param in image_params):
            return True
        
        # CDN d'images connus
        image_cdns = ['cdn.shopify.com', 'shopifycdn.com', 'cdn.shopifycdn.com',
                     'images.unsplash.com', 'i.imgur.com', 'cdn-images', 
                     'imagekit.io', 'cloudinary.com', 'imgix.net']
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if any(cdn in domain for cdn in image_cdns):
            return True
        
        # Patterns d'URLs d'images
        image_patterns = ['/media/', '/assets/images/', '/static/images/', 
                         '/uploads/', '/wp-content/uploads/']
        if any(pattern in url_lower for pattern in image_patterns):
            return True
        
        return False
    
    def _is_valid_shopify_url(self, url: str) -> bool:
        """
        Vérifie si une URL est une URL Shopify valide (et non une image)
        
        Args:
            url: URL à vérifier
            
        Returns:
            True si l'URL est valide et n'est pas une image
        """
        try:
            # D'abord vérifier si c'est une image
            if self._is_image_url(url):
                return False
            
            parsed = urlparse(url)
            if not parsed.netloc or not parsed.scheme:
                return False
            
            # Exclure les domaines internes
            excluded = ['shop.app', 'google.com', 'bing.com', 'facebook.com', 'twitter.com']
            domain = parsed.netloc.lower()
            if any(exc in domain for exc in excluded):
                return False
            
            # Accepter myshopify.com ou autres domaines (on vérifiera plus tard)
            return True
        except:
            return False
    
    def scrape_with_selenium(self, query: str = "", category: str = "", page: int = 1) -> List[str]:
        """
        Scrape shop.app en utilisant Selenium (si requests échoue)
        
        Args:
            query: Terme de recherche
            category: Catégorie à filtrer
            page: Numéro de page
            
        Returns:
            Liste d'URLs trouvées
        """
        urls = []
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException
            
            print("  Utilisation de Selenium pour contourner la protection...")
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                # Construire l'URL de recherche
                search_params = []
                if query:
                    search_params.append(f"q={quote_plus(query)}")
                if category:
                    search_params.append(f"category={quote_plus(category)}")
                if page > 1:
                    search_params.append(f"page={page}")
                
                search_url = f"{self.base_url}/search"
                if search_params:
                    search_url += "?" + "&".join(search_params)
                
                print(f"  Chargement de {search_url}...")
                driver.get(search_url)
                
                # Attendre que la page charge complètement
                time.sleep(5)  # Attendre que le JavaScript charge
                
                # Attendre que le contenu soit chargé
                try:
                    # Attendre qu'un élément de contenu soit présent (liens, boutiques, etc.)
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    # Attendre un peu plus pour que le JavaScript charge le contenu
                    time.sleep(3)
                except TimeoutException:
                    print("  Timeout lors du chargement de la page, continuation quand même...")
                
                # Faire défiler la page pour charger le contenu lazy-loaded
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
                # Extraire le HTML
                html = driver.page_source
                soup = BeautifulSoup(html, 'lxml')
                
                print(f"  HTML récupéré ({len(html)} caractères)")
                
                # Utiliser la méthode d'extraction standard
                extracted_urls = self._extract_shop_urls_from_page(soup)
                urls.extend(extracted_urls)
                
                print(f"  → {len(extracted_urls)} URLs extraites depuis la page")
                
            finally:
                driver.quit()
                
        except ImportError:
            print("  Selenium non disponible, utilisation de requests uniquement")
        except Exception as e:
            print(f"  Erreur avec Selenium: {e}")
        
        return urls
    
    def discover_all_pages(self, start_url: str = None, max_depth: int = 3, use_selenium: bool = False) -> List[str]:
        """
        Découvre automatiquement toutes les pages disponibles sur shop.app et extrait les URLs
        
        Args:
            start_url: URL de départ (par défaut: page principale)
            max_depth: Profondeur maximale d'exploration
            use_selenium: Si True, utilise Selenium pour les pages qui nécessitent JavaScript
            
        Returns:
            Liste d'URLs de sites Shopify trouvées
        """
        if start_url is None:
            start_url = self.base_url
        
        print(f"=== DÉCOUVERTE AUTOMATIQUE DES PAGES SUR SHOP.APP ===\n")
        print(f"URL de départ: {start_url}\n")
        
        visited_urls: Set[str] = set()
        pages_to_visit: List[tuple] = [(start_url, 0)]  # (url, depth)
        all_urls = []
        
        while pages_to_visit:
            current_url, depth = pages_to_visit.pop(0)
            
            # Éviter les boucles infinies
            if current_url in visited_urls or depth > max_depth:
                continue
            
            visited_urls.add(current_url)
            print(f"[Profondeur {depth}] Exploration de: {current_url}")
            
            try:
                # Scraper la page
                if use_selenium and USE_SELENIUM:
                    page_urls = self._scrape_page_with_selenium(current_url)
                else:
                    page_urls = self._scrape_page(current_url)
                
                # Extraire les URLs de sites depuis cette page
                shop_urls = [url for url in page_urls if self._is_valid_shopify_url(url) and not self._is_image_url(url)]
                all_urls.extend(shop_urls)
                print(f"  → {len(shop_urls)} URLs de sites trouvées sur cette page")
                
                # Trouver les liens vers d'autres pages de shop.app
                if depth < max_depth:
                    next_pages = self._find_shop_app_pages(current_url, use_selenium)
                    for next_url in next_pages:
                        if next_url not in visited_urls:
                            pages_to_visit.append((next_url, depth + 1))
                            print(f"  → Page suivante trouvée: {next_url}")
                
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
            except Exception as e:
                print(f"  Erreur lors du scraping de {current_url}: {e}")
                continue
        
        unique_urls = list(self.found_urls)
        print(f"\nTotal: {len(unique_urls)} URLs uniques trouvées")
        print(f"Pages visitées: {len(visited_urls)}")
        
        return unique_urls
    
    def _scrape_page(self, url: str) -> List[str]:
        """
        Scrape une page spécifique et retourne toutes les URLs trouvées
        
        Args:
            url: URL de la page à scraper
            
        Returns:
            Liste d'URLs trouvées
        """
        urls = []
        
        try:
            response = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            urls.extend(self._extract_shop_urls_from_page(soup))
            
        except Exception as e:
            print(f"    Erreur: {e}")
        
        return urls
    
    def _scrape_page_with_selenium(self, url: str) -> List[str]:
        """
        Scrape une page avec Selenium
        
        Args:
            url: URL de la page à scraper
            
        Returns:
            Liste d'URLs trouvées
        """
        urls = []
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                driver.get(url)
                time.sleep(5)
                
                # Scroll pour charger le contenu lazy-loaded
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
                html = driver.page_source
                soup = BeautifulSoup(html, 'lxml')
                urls.extend(self._extract_shop_urls_from_page(soup))
                
            finally:
                driver.quit()
                
        except Exception as e:
            print(f"    Erreur Selenium: {e}")
        
        return urls
    
    def _find_shop_app_pages(self, current_url: str, use_selenium: bool = False) -> List[str]:
        """
        Trouve tous les liens vers d'autres pages de shop.app depuis une page
        
        Args:
            current_url: URL de la page actuelle
            use_selenium: Si True, utilise Selenium pour charger la page
            
        Returns:
            Liste d'URLs de pages shop.app à explorer
        """
        pages = []
        
        try:
            if use_selenium and USE_SELENIUM:
                soup = self._get_page_soup_selenium(current_url)
            else:
                response = self.session.get(current_url, timeout=TIMEOUT, allow_redirects=True)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'lxml')
            
            # Trouver tous les liens vers shop.app
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').strip()
                if not href:
                    continue
                
                # Convertir en URL absolue
                if href.startswith('/'):
                    href = urljoin(self.base_url, href)
                elif not href.startswith(('http://', 'https://')):
                    continue
                
                # Filtrer seulement les pages shop.app (pas les images, pas les sites externes)
                if 'shop.app' in href and not self._is_image_url(href):
                    parsed = urlparse(href)
                    # Vérifier que c'est bien un lien vers shop.app (pas un lien externe)
                    if parsed.netloc in ['shop.app', 'www.shop.app'] or parsed.netloc.endswith('.shop.app'):
                        # Inclure les pages de navigation, catégories, recherche, etc.
                        # Exclure seulement les liens directs vers des boutiques externes
                        if '/shop/' in href:
                            # C'est un lien vers une boutique, on peut l'explorer pour trouver l'URL réelle
                            if href not in pages:
                                pages.append(href)
                        elif any(path in href for path in ['/categories', '/search', '/category', '/page', '/?page']):
                            # Pages de navigation
                            if href not in pages:
                                pages.append(href)
                        elif href.count('/') <= 2:  # Pages principales (/, /about, etc.)
                            if href not in pages:
                                pages.append(href)
            
            # Trouver les liens de pagination spécifiquement
            pagination_selectors = [
                ('a', {'class': re.compile(r'page|pagination|next|prev', re.I)}),
                ('a', {'aria-label': re.compile(r'page|next|previous', re.I)}),
                ('nav', {}),
            ]
            
            for tag, attrs in pagination_selectors:
                elements = soup.find_all(tag, attrs)
                for elem in elements:
                    links = elem.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '').strip()
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                        if 'shop.app' in href and href not in pages and not self._is_image_url(href):
                            pages.append(href)
            
        except Exception as e:
            print(f"    Erreur lors de la recherche de pages: {e}")
        
        return pages
    
    def _get_page_soup_selenium(self, url: str) -> BeautifulSoup:
        """Récupère le HTML d'une page avec Selenium et retourne un BeautifulSoup"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.get(url)
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            html = driver.page_source
            return BeautifulSoup(html, 'lxml')
        finally:
            driver.quit()
    
    def scrape_all(self, search_queries: List[str] = None, categories: List[str] = None, max_pages: int = 10, use_selenium_fallback: bool = True, auto_discover: bool = True) -> List[str]:
        """
        Scrape shop.app en utilisant les fonctionnalités de recherche et filtres
        
        Args:
            search_queries: Liste de termes de recherche (si None, recherche générale)
            categories: Liste de catégories à explorer
            max_pages: Nombre maximum de pages à scraper par recherche
            use_selenium_fallback: Si True, utilise Selenium si requests échoue
            
        Returns:
            Liste complète d'URLs trouvées
        """
        print("=== SCRAPING DE SHOP.APP ===\n")
        
        all_urls = []
        
        # Établir une session
        print(f"Établissement de la session avec {self.base_url}...")
        try:
            self.session.get(self.base_url, timeout=TIMEOUT, allow_redirects=True)
            time.sleep(1)
        except:
            pass
        
        # Si auto_discover est activé, explorer automatiquement toutes les pages
        if auto_discover:
            print("Mode découverte automatique activé - exploration de toutes les pages...\n")
            discovered_urls = self.discover_all_pages(
                start_url=self.base_url,
                max_depth=3,
                use_selenium=use_selenium_fallback and USE_SELENIUM
            )
            all_urls.extend(discovered_urls)
            print(f"\nDécouverte automatique terminée: {len(discovered_urls)} URLs trouvées\n")
        
        # Si aucune requête spécifique, faire une recherche générale
        if not search_queries:
            search_queries = [""]  # Recherche vide = toutes les boutiques
        
        # Rechercher avec chaque requête
        for query in search_queries:
            print(f"\nRecherche: '{query if query else 'toutes les boutiques'}'")
            
            # Scraper plusieurs pages
            for page in range(1, max_pages + 1):
                page_urls = self.search_shops(query=query, page=page)
                if not page_urls:
                    print(f"  Aucun résultat page {page}, arrêt de la pagination")
                    break
                all_urls.extend(page_urls)
                print(f"  Page {page}: {len(page_urls)} URLs trouvées")
        
        # Si des catégories sont spécifiées, les explorer aussi
        if categories:
            print(f"\nExploration des catégories: {', '.join(categories)}")
            for category in categories:
                for page in range(1, max_pages + 1):
                    page_urls = self.search_shops(category=category, page=page)
                    if not page_urls:
                        break
                    all_urls.extend(page_urls)
                    print(f"  Catégorie '{category}' page {page}: {len(page_urls)} URLs")
        
        # Si on n'a pas trouvé d'URLs et que Selenium est disponible, l'essayer
        if not all_urls and use_selenium_fallback and USE_SELENIUM:
            print("\n  Aucune URL trouvée avec requests, tentative avec Selenium...")
            # Essayer avec chaque requête de recherche
            for query in (search_queries or [""]):
                for page in range(1, min(3, max_pages) + 1):  # Limiter à 3 pages pour Selenium (plus lent)
                    print(f"  Selenium - Recherche '{query if query else 'toutes'}' page {page}...")
                    selenium_urls = self.scrape_with_selenium(query=query, page=page)
                    if selenium_urls:
                        all_urls.extend(selenium_urls)
                        print(f"    → {len(selenium_urls)} URLs trouvées")
                    else:
                        if page == 1:
                            break  # Pas de résultats page 1, arrêter cette requête
                        break  # Pas de résultats, arrêter la pagination
        
        # Retourner les URLs uniques
        unique_urls = list(self.found_urls)
        print(f"\nTotal: {len(unique_urls)} URLs uniques trouvées sur shop.app")
        
        return unique_urls

