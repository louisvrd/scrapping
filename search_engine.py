"""
Module de recherche de sites Shopify via différents moteurs
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Set
import time
import re
from urllib.parse import quote_plus, urlparse
from fake_useragent import UserAgent

from config import GOOGLE_DORK_QUERIES, DELAY_BETWEEN_REQUESTS, MAX_RESULTS_PER_SEARCH


class SearchEngine:
    """Classe pour rechercher des sites Shopify via les moteurs de recherche"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random
        })
        self.found_urls: Set[str] = set()
    
    def search_google_dork(self, query: str, max_results: int = 50) -> List[str]:
        """
        Recherche via Google Dork (méthode basique)
        Note: Google limite les requêtes automatisées, cette méthode est basique
        
        Args:
            query: Requête de recherche
            max_results: Nombre maximum de résultats
            
        Returns:
            Liste d'URLs trouvées
        """
        urls = []
        
        try:
            # Encoder la requête
            encoded_query = quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded_query}&num=50"
            
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.google.com/',
            }
            
            response = self.session.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Méthode 1: Recherche des liens avec /url?q=
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    
                    # Google utilise des URLs de redirection
                    if href.startswith('/url?q='):
                        actual_url = href.split('/url?q=')[1].split('&')[0]
                        actual_url = requests.utils.unquote(actual_url)
                        
                        if self._is_valid_url(actual_url):
                            urls.append(actual_url)
                            self.found_urls.add(actual_url)
                            
                            if len(urls) >= max_results:
                                break
                
                # Méthode 2: Recherche dans les divs de résultats (structure moderne)
                result_divs = soup.find_all('div', class_=['g', 'tF2Cxc'])
                for div in result_divs:
                    link = div.find('a', href=True)
                    if link:
                        href = link.get('href', '')
                        if href.startswith('/url?q='):
                            actual_url = href.split('/url?q=')[1].split('&')[0]
                            actual_url = requests.utils.unquote(actual_url)
                        else:
                            actual_url = href
                        
                        if self._is_valid_url(actual_url):
                            urls.append(actual_url)
                            self.found_urls.add(actual_url)
                            
                            if len(urls) >= max_results:
                                break
                
                # Méthode 3: Recherche par regex dans le HTML
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                found_urls = re.findall(url_pattern, response.text)
                for found_url in found_urls:
                    # Nettoyer l'URL
                    clean_url = found_url.split('&')[0].split('"')[0].split("'")[0]
                    if self._is_valid_url(clean_url) and 'google.com' not in clean_url:
                        if 'myshopify.com' in clean_url or 'shopify' in clean_url.lower():
                            urls.append(clean_url)
                            self.found_urls.add(clean_url)
                            
                            if len(urls) >= max_results:
                                break
                
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            print(f"Erreur lors de la recherche Google: {e}")
        
        return urls
    
    def search_duckduckgo(self, query: str, max_results: int = 50) -> List[str]:
        """
        Recherche via DuckDuckGo (plus permissif que Google)
        
        Args:
            query: Requête de recherche
            max_results: Nombre maximum de résultats
            
        Returns:
            Liste d'URLs trouvées
        """
        urls = []
        
        try:
            encoded_query = quote_plus(query)
            # Utiliser l'API DuckDuckGo qui est plus fiable
            search_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
            
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'application/json',
            }
            
            response = self.session.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Extraire les URLs des résultats
                    for result in data.get('Results', []):
                        url = result.get('FirstURL', '')
                        if url and self._is_valid_url(url):
                            urls.append(url)
                            self.found_urls.add(url)
                            if len(urls) >= max_results:
                                break
                except:
                    # Fallback sur HTML si JSON ne fonctionne pas
                    search_url_html = f"https://html.duckduckgo.com/html/?q={encoded_query}"
                    response = self.session.get(search_url_html, headers={'User-Agent': self.ua.random}, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'lxml')
                        
                        # Plusieurs sélecteurs possibles pour DuckDuckGo
                        selectors = [
                            ('a', {'class': 'result__a'}),
                            ('a', {'class': 'web-result__link'}),
                            ('a', {'class': 'result-link'}),
                        ]
                        
                        for tag, attrs in selectors:
                            result_links = soup.find_all(tag, attrs)
                            for link in result_links:
                                href = link.get('href', '')
                                if self._is_valid_url(href):
                                    urls.append(href)
                                    self.found_urls.add(href)
                                    if len(urls) >= max_results:
                                        break
                            if urls:
                                break
                        
                        # Recherche par regex si les sélecteurs ne fonctionnent pas
                        if not urls:
                            import re
                            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                            found_urls = re.findall(url_pattern, response.text)
                            for found_url in found_urls:
                                clean_url = found_url.split('&')[0].split('"')[0]
                                if self._is_valid_url(clean_url) and 'duckduckgo.com' not in clean_url:
                                    if 'myshopify.com' in clean_url or 'shopify' in clean_url.lower():
                                        urls.append(clean_url)
                                        self.found_urls.add(clean_url)
                                        if len(urls) >= max_results:
                                            break
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            print(f"Erreur lors de la recherche DuckDuckGo: {e}")
        
        return urls
    
    def search_bing(self, query: str, max_results: int = 50) -> List[str]:
        """
        Recherche via Bing
        
        Args:
            query: Requête de recherche
            max_results: Nombre maximum de résultats
            
        Returns:
            Liste d'URLs trouvées
        """
        urls = []
        
        try:
            encoded_query = quote_plus(query)
            search_url = f"https://www.bing.com/search?q={encoded_query}&count=50"
            
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            
            response = self.session.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Méthode 1: Recherche dans les résultats structurés
                result_items = soup.find_all('li', class_='b_algo')
                for item in result_items:
                    link = item.find('a', href=True)
                    if link:
                        href = link.get('href', '')
                        if self._is_valid_url(href) and 'bing.com' not in href:
                            urls.append(href)
                            self.found_urls.add(href)
                            if len(urls) >= max_results:
                                break
                
                # Méthode 2: Recherche générale des liens
                if len(urls) < max_results:
                    result_links = soup.find_all('a', href=True)
                    for link in result_links:
                        href = link.get('href', '')
                        
                        # Bing utilise parfois des URLs de redirection
                        if href.startswith('http') and 'bing.com' not in href:
                            if self._is_valid_url(href):
                                urls.append(href)
                                self.found_urls.add(href)
                                
                                if len(urls) >= max_results:
                                    break
                
                # Méthode 3: Recherche par regex
                if len(urls) < max_results:
                    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                    found_urls = re.findall(url_pattern, response.text)
                    for found_url in found_urls:
                        clean_url = found_url.split('&')[0].split('"')[0].split("'")[0]
                        if self._is_valid_url(clean_url) and 'bing.com' not in clean_url:
                            if 'myshopify.com' in clean_url or 'shopify' in clean_url.lower():
                                urls.append(clean_url)
                                self.found_urls.add(clean_url)
                                if len(urls) >= max_results:
                                    break
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            print(f"Erreur lors de la recherche Bing: {e}")
        
        return urls
    
    def search_all_engines(self, queries: List[str] = None) -> List[str]:
        """
        Recherche sur tous les moteurs avec toutes les requêtes
        
        Args:
            queries: Liste de requêtes (utilise GOOGLE_DORK_QUERIES par défaut)
            
        Returns:
            Liste unique d'URLs trouvées
        """
        if queries is None:
            queries = GOOGLE_DORK_QUERIES
        
        all_urls = []
        
        print(f"Recherche avec {len(queries)} requêtes sur plusieurs moteurs...")
        
        for query in queries:
            print(f"Recherche: {query}")
            
            # Recherche DuckDuckGo (généralement plus permissif)
            ddg_urls = self.search_duckduckgo(query, MAX_RESULTS_PER_SEARCH)
            all_urls.extend(ddg_urls)
            print(f"  DuckDuckGo: {len(ddg_urls)} résultats")
            
            # Recherche Bing
            bing_urls = self.search_bing(query, MAX_RESULTS_PER_SEARCH)
            all_urls.extend(bing_urls)
            print(f"  Bing: {len(bing_urls)} résultats")
            
            # Recherche Google (peut être limitée)
            try:
                google_urls = self.search_google_dork(query, MAX_RESULTS_PER_SEARCH)
                all_urls.extend(google_urls)
                print(f"  Google: {len(google_urls)} résultats")
            except Exception as e:
                print(f"  Google: Erreur - {e}")
        
        # Retourner les URLs uniques
        unique_urls = list(self.found_urls)
        print(f"\nTotal d'URLs uniques trouvées: {len(unique_urls)}")
        
        return unique_urls
    
    def generate_myshopify_urls(self, wordlist: List[str] = None, max_urls: int = 1000) -> List[str]:
        """
        Génère des URLs myshopify.com potentielles basées sur une wordlist
        
        Args:
            wordlist: Liste de mots à combiner (utilise une liste par défaut si None)
            max_urls: Nombre maximum d'URLs à générer
            
        Returns:
            Liste d'URLs myshopify.com potentielles
        """
        if wordlist is None:
            # Liste de mots communs pour les noms de shops
            wordlist = [
                'shop', 'store', 'boutique', 'market', 'mall', 'buy', 'sell',
                'fashion', 'style', 'trend', 'design', 'art', 'craft', 'gift',
                'home', 'decor', 'tech', 'gadget', 'book', 'music', 'sport',
                'health', 'beauty', 'food', 'drink', 'coffee', 'tea', 'wine',
                'jewelry', 'watch', 'shoe', 'bag', 'clothing', 'accessory'
            ]
        
        urls = []
        count = 0
        
        # Générer des combinaisons simples
        for word in wordlist:
            if count >= max_urls:
                break
            url = f"https://{word}.myshopify.com"
            urls.append(url)
            self.found_urls.add(url)
            count += 1
        
        # Générer des combinaisons avec nombres
        for word in wordlist[:50]:  # Limiter pour éviter trop d'URLs
            if count >= max_urls:
                break
            for num in range(1, 10):
                url = f"https://{word}{num}.myshopify.com"
                urls.append(url)
                self.found_urls.add(url)
                count += 1
                if count >= max_urls:
                    break
        
        return urls
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Vérifie si une URL est valide
        
        Args:
            url: URL à vérifier
            
        Returns:
            True si l'URL est valide
        """
        try:
            parsed = urlparse(url)
            if not bool(parsed.netloc) or not bool(parsed.scheme):
                return False
            # Filtrer les URLs de redirection et les URLs internes des moteurs
            excluded_domains = ['google.com', 'bing.com', 'duckduckgo.com', 'youtube.com']
            domain = parsed.netloc.lower()
            return not any(excluded in domain for excluded in excluded_domains)
        except:
            return False

