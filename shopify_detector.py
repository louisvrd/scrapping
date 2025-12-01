"""
Module de détection des sites Shopify
"""
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
from urllib.parse import urlparse, urljoin
import time
from fake_useragent import UserAgent

from config import SHOPIFY_PATTERNS, TIMEOUT, DELAY_BETWEEN_REQUESTS


class ShopifyDetector:
    """Classe pour détecter si un site utilise Shopify"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random
        })
    
    def is_shopify_site(self, url: str) -> Dict[str, any]:
        """
        Vérifie si un site utilise Shopify
        
        Args:
            url: URL du site à vérifier
            
        Returns:
            Dict avec 'is_shopify' (bool) et 'evidence' (list)
        """
        evidence = []
        is_shopify = False
        
        try:
            # Normaliser l'URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Vérification 1: Domaine myshopify.com
            if 'myshopify.com' in domain:
                is_shopify = True
                evidence.append('Domaine myshopify.com détecté')
                return {'is_shopify': True, 'evidence': evidence, 'url': url}
            
            # Vérification 2: Analyse du HTML
            try:
                response = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
                response.raise_for_status()
                
                html_content = response.text.lower()
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Recherche des patterns dans le HTML
                for pattern in SHOPIFY_PATTERNS:
                    if pattern.lower() in html_content:
                        is_shopify = True
                        evidence.append(f'Pattern "{pattern}" trouvé dans le HTML')
                
                # Recherche dans les balises meta
                meta_tags = soup.find_all('meta')
                for meta in meta_tags:
                    content = str(meta.get('content', '')).lower()
                    if any(pattern.lower() in content for pattern in SHOPIFY_PATTERNS):
                        is_shopify = True
                        evidence.append('Pattern Shopify trouvé dans meta tags')
                
                # Recherche dans les scripts
                scripts = soup.find_all('script')
                for script in scripts:
                    script_content = str(script.string or '').lower()
                    if 'shopify' in script_content:
                        is_shopify = True
                        evidence.append('Référence Shopify trouvée dans les scripts')
                
                # Recherche dans les liens
                links = soup.find_all('link', href=True)
                for link in links:
                    href = link.get('href', '').lower()
                    if any(pattern.lower() in href for pattern in SHOPIFY_PATTERNS):
                        is_shopify = True
                        evidence.append('Lien Shopify détecté')
                
                # Vérification des headers HTTP
                headers = response.headers
                for header_name, header_value in headers.items():
                    if 'shopify' in header_value.lower():
                        is_shopify = True
                        evidence.append(f'Header "{header_name}" contient Shopify')
                
            except requests.RequestException as e:
                evidence.append(f'Erreur lors de la requête: {str(e)}')
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            evidence.append(f'Erreur générale: {str(e)}')
        
        return {
            'is_shopify': is_shopify,
            'evidence': evidence,
            'url': url
        }
    
    def extract_shopify_info(self, url: str) -> Dict[str, any]:
        """
        Extrait des informations supplémentaires sur un site Shopify
        
        Args:
            url: URL du site Shopify
            
        Returns:
            Dict avec les informations extraites
        """
        info = {
            'url': url,
            'domain': None,
            'title': None,
            'description': None,
            'shop_name': None,
            'verified': False
        }
        
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            response = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extraction du domaine
            parsed = urlparse(url)
            info['domain'] = parsed.netloc
            
            # Extraction du titre
            title_tag = soup.find('title')
            if title_tag:
                info['title'] = title_tag.string.strip() if title_tag.string else None
            
            # Extraction de la description
            desc_meta = soup.find('meta', attrs={'name': 'description'})
            if desc_meta:
                info['description'] = desc_meta.get('content', '').strip()
            
            # Extraction du nom du shop (si disponible)
            shop_meta = soup.find('meta', attrs={'property': 'og:site_name'})
            if shop_meta:
                info['shop_name'] = shop_meta.get('content', '').strip()
            
            # Vérification si c'est un vrai site Shopify
            detection = self.is_shopify_site(url)
            info['verified'] = detection['is_shopify']
            
        except Exception as e:
            info['error'] = str(e)
        
        return info

