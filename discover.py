"""
Script de découverte de sites Shopify via l'API BuiltWith.

BuiltWith propose un CATALOGUE de sites Shopify accessible via leur API.
Ce script permet d'accéder directement à ce catalogue.

IMPORTANT - Choix de l'API BuiltWith :
---------------------------------------
BuiltWith propose plusieurs APIs selon votre plan :

1. **Website Lists API / Catalog API** (RECOMMANDÉ - Plans payants)
   - Accès direct au catalogue des sites Shopify
   - URL: https://api.builtwith.com/v20/api.json
   - Paramètres: KEY, TECHNOLOGY (Shopify), etc.
   - Permet de récupérer la liste complète ou paginée des sites Shopify
   - C'est la méthode la plus efficace pour découvrir des sites Shopify

2. **Technology Search API** (Plans payants)
   - Permet de rechercher des sites par technologie avec filtres
   - URL: https://api.builtwith.com/v20/api.json
   - Paramètres: KEY, TECHNOLOGY, etc.

3. **Domain Lookup API** (Gratuit avec limites ou Payant)
   - Permet d'analyser UN domaine spécifique
   - URL: https://api.builtwith.com/v20/api.json
   - Ne permet PAS de découvrir des sites, seulement de vérifier
   - Utile pour filtrer une liste existante

Ce script supporte l'accès au catalogue Shopify. Configurez
BUILTWITH_API_METHOD='catalog' pour utiliser cette fonctionnalité.
"""

import os
import time
import requests
from dotenv import load_dotenv
from typing import List, Set, Optional
from pathlib import Path

# Charger les variables d'environnement
BASE_DIR = Path(__file__).parent
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path), override=True)
else:
    load_dotenv(override=True)

# Configuration
BUILTWITH_API_KEY = os.getenv('BUILTWITH_API_KEY', 'YOUR_API_KEY_HERE')
BUILTWITH_API_METHOD = os.getenv('BUILTWITH_API_METHOD', 'catalog')  # 'catalog', 'technology_search' ou 'domain_lookup'
OUTPUT_FILE = 'domains_to_scrape.txt'
TECHNOLOGY = 'Shopify'
MAX_RETRIES = 3
RETRY_DELAY = 2  # secondes
MAX_RESULTS = int(os.getenv('MAX_RESULTS', '1000'))  # Nombre maximum de résultats à récupérer

# URLs des différentes APIs BuiltWith
API_URLS = {
    'catalog': 'https://api.builtwith.com/v20/api.json',  # Catalogue des sites par technologie
    'technology_search': 'https://api.builtwith.com/v20/api.json',  # Recherche par technologie
    'domain_lookup': 'https://api.builtwith.com/v20/api.json',  # Analyse d'un domaine
    'free_api': 'https://api.builtwith.com/free1/api.json'  # API gratuite (limite)
}


def get_shopify_domains_from_catalog(limit: Optional[int] = None) -> Set[str]:
    """
    Récupère les domaines Shopify depuis le catalogue BuiltWith.
    Cette méthode accède directement au catalogue des sites Shopify.
    
    Args:
        limit: Nombre maximum de domaines à récupérer (None = tous disponibles)
        
    Returns:
        Un ensemble de domaines uniques
    """
    domains = set()
    api_url = API_URLS['catalog']
    max_results = limit or MAX_RESULTS
    page = 0
    page_size = 100  # Nombre de résultats par page (ajustez selon votre plan)
    
    print(f"  Accès au catalogue Shopify (max {max_results} résultats)...")
    
    while len(domains) < max_results:
        page_domains = 0  # Initialiser avant la boucle de retry
        for attempt in range(MAX_RETRIES):
            try:
                # Paramètres pour accéder au catalogue Shopify
                # NOTE: La structure exacte dépend de votre plan BuiltWith
                # Consultez la documentation BuiltWith pour votre plan spécifique
                params = {
                    'KEY': BUILTWITH_API_KEY,
                    'TECHNOLOGY': TECHNOLOGY,  # Catalogue des sites Shopify
                    'HIDETEXT': 'yes',
                    'HIDEDL': 'yes'
                }
                
                # Pagination si supportée par votre plan
                if page > 0:
                    params['START'] = page * page_size
                    params['LIMIT'] = page_size
                
                response = requests.get(api_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Parser la réponse - structure peut varier selon l'API
                page_domains = 0
                if 'Results' in data:
                    for result in data['Results']:
                        if 'Result' in result:
                            for domain_info in result['Result']:
                                domain = domain_info.get('Domain', '')
                                if domain and len(domains) < max_results:
                                    domains.add(domain)
                                    page_domains += 1
                                    if len(domains) % 100 == 0:
                                        print(f"    → {len(domains)} domaines récupérés...")
                
                # Si aucune nouvelle donnée, on a atteint la fin
                if page_domains == 0:
                    break
                
                # Si on a récupéré moins que la taille de page, c'est la dernière page
                if page_domains < page_size:
                    break
                
                page += 1
                time.sleep(0.5)  # Pause entre les pages
                break
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f"  ⚠ Limite de taux atteinte. Attente de {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 401:
                    print(f"  ✗ Erreur d'authentification. Vérifiez votre clé API.")
                    return domains
                elif response.status_code == 400:
                    # Peut-être que la pagination n'est pas supportée, essayer sans
                    if page > 0:
                        print(f"  ⚠ Pagination non supportée, récupération terminée.")
                        break
                    print(f"  ✗ Requête invalide. Vérifiez les paramètres de l'API.")
                    print(f"     Réponse: {response.text[:200]}")
                    return domains
                else:
                    print(f"  ✗ Erreur HTTP {response.status_code}: {e}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    return domains
                    
            except requests.exceptions.RequestException as e:
                print(f"  ✗ Erreur de requête: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                return domains
                
            except Exception as e:
                print(f"  ✗ Erreur inattendue: {e}")
                return domains
        
        # Si aucune nouvelle donnée, sortir de la boucle
        if page_domains == 0:
            break
    
    return domains


def get_shopify_domains_technology_search(keyword: str) -> Set[str]:
    """
    Récupère les domaines Shopify via l'API Technology Search de BuiltWith.
    Cette méthode nécessite un plan payant avec accès à la recherche par technologie.
    
    Args:
        keyword: Le mot-clé de recherche (peut être un terme de recherche ou filtre)
        
    Returns:
        Un ensemble de domaines uniques
    """
    domains = set()
    api_url = API_URLS['technology_search']
    
    for attempt in range(MAX_RETRIES):
        try:
            # Paramètres pour Technology Search API
            # NOTE: La structure exacte dépend de votre plan BuiltWith
            # Consultez la documentation BuiltWith pour votre plan spécifique
            params = {
                'KEY': BUILTWITH_API_KEY,
                'TECHNOLOGY': TECHNOLOGY,  # Recherche par technologie Shopify
                'HIDETEXT': 'yes',
                'HIDEDL': 'yes'
            }
            
            # Si votre API supporte des filtres par mot-clé, ajoutez-les
            # Exemple: params['KEYWORD'] = keyword
            
            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Parser la réponse - structure peut varier selon l'API
            if 'Results' in data:
                for result in data['Results']:
                    if 'Result' in result:
                        for domain_info in result['Result']:
                            domain = domain_info.get('Domain', '')
                            if domain:
                                domains.add(domain)
                                print(f"  ✓ Trouvé: {domain}")
            
            # Si on a des résultats, pas besoin de réessayer
            break
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                # Limite de taux atteinte
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"  ⚠ Limite de taux atteinte. Attente de {wait_time}s...")
                time.sleep(wait_time)
                continue
            elif response.status_code == 401:
                print(f"  ✗ Erreur d'authentification. Vérifiez votre clé API.")
                break
            elif response.status_code == 400:
                print(f"  ✗ Requête invalide. Vérifiez les paramètres de l'API.")
                print(f"     Réponse: {response.text[:200]}")
                break
            else:
                print(f"  ✗ Erreur HTTP {response.status_code}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                break
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Erreur de requête: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            break
            
        except Exception as e:
            print(f"  ✗ Erreur inattendue: {e}")
            break
    
    return domains


def verify_domain_is_shopify(domain: str) -> bool:
    """
    Vérifie si un domaine utilise Shopify via l'API Domain Lookup.
    Utile si vous avez une liste de domaines et voulez les filtrer.
    
    Args:
        domain: Le domaine à vérifier
        
    Returns:
        True si le domaine utilise Shopify, False sinon
    """
    api_url = API_URLS['domain_lookup']
    
    for attempt in range(MAX_RETRIES):
        try:
            params = {
                'KEY': BUILTWITH_API_KEY,
                'LOOKUP': domain,
                'HIDETEXT': 'yes',
                'HIDEDL': 'yes'
            }
            
            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Vérifier si Shopify est dans les technologies
            if 'Results' in data:
                for result in data['Results']:
                    if 'Result' in result:
                        for domain_info in result['Result']:
                            if 'Technologies' in domain_info:
                                for tech in domain_info['Technologies']:
                                    if TECHNOLOGY.lower() in str(tech).lower():
                                        return True
            
            return False
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
                continue
            else:
                return False
                
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            return False
    
    return False


def discover_shopify_sites(keywords: List[str]) -> None:
    """
    Découvre les sites Shopify selon la méthode configurée.
    
    Args:
        keywords: Liste de mots-clés (utilisée uniquement pour technology_search)
    """
    all_domains = set()
    
    print(f"Clé API BuiltWith: {'✓ Configurée' if BUILTWITH_API_KEY != 'YOUR_API_KEY_HERE' else '✗ Non configurée'}")
    print(f"Méthode API: {BUILTWITH_API_METHOD}\n")
    
    if BUILTWITH_API_METHOD == 'catalog':
        print("✓ MODE: Catalogue Shopify (Recommandé)")
        print("   Accès direct au catalogue BuiltWith des sites Shopify.\n")
        
        domains = get_shopify_domains_from_catalog()
        all_domains.update(domains)
        print(f"\n  → {len(domains)} domaine(s) récupéré(s) depuis le catalogue")
    
    elif BUILTWITH_API_METHOD == 'technology_search':
        print("⚠ MODE: Technology Search API")
        print("   Assurez-vous d'avoir un plan BuiltWith avec accès à cette fonctionnalité.\n")
        
        for i, keyword in enumerate(keywords, 1):
            print(f"[{i}/{len(keywords)}] Recherche pour: '{keyword}'")
            domains = get_shopify_domains_technology_search(keyword)
            all_domains.update(domains)
            print(f"  → {len(domains)} domaine(s) trouvé(s) pour ce mot-clé\n")
            
            # Pause entre les requêtes pour éviter les limites de taux
            if i < len(keywords):
                time.sleep(1)
    
    elif BUILTWITH_API_METHOD == 'domain_lookup':
        print("⚠ MODE: Domain Lookup API")
        print("   Ce mode nécessite une liste de domaines pré-existante.")
        print("   Les domaines seront vérifiés pour confirmer l'utilisation de Shopify.\n")
        print("   Pour utiliser ce mode, créez un fichier 'domains_to_check.txt' avec un domaine par ligne.")
        
        input_file = 'domains_to_check.txt'
        if not os.path.exists(input_file):
            print(f"\n✗ Fichier {input_file} introuvable!")
            print("   Créez ce fichier avec une liste de domaines à vérifier.")
            return
        
        with open(input_file, 'r', encoding='utf-8') as f:
            domains_to_check = [line.strip() for line in f if line.strip()]
        
        print(f"Vérification de {len(domains_to_check)} domaine(s)...\n")
        
        for i, domain in enumerate(domains_to_check, 1):
            print(f"[{i}/{len(domains_to_check)}] Vérification: {domain}")
            if verify_domain_is_shopify(domain):
                all_domains.add(domain)
                print(f"  ✓ {domain} utilise Shopify")
            else:
                print(f"  ✗ {domain} n'utilise pas Shopify")
            
            if i < len(domains_to_check):
                time.sleep(1)
    
    # Sauvegarder les domaines uniques
    if all_domains:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for domain in sorted(all_domains):
                f.write(f"{domain}\n")
        print(f"\n✓ {len(all_domains)} domaine(s) unique(s) sauvegardé(s) dans {OUTPUT_FILE}")
    else:
        print("\n✗ Aucun domaine trouvé. Vérifiez votre clé API et la méthode utilisée.")


def main():
    """Point d'entrée principal du script."""
    # Liste de mots-clés par défaut (peut être modifiée)
    default_keywords = [
        "boutique de vêtements",
        "jewelry store",
        "fashion france"
    ]
    
    # Vous pouvez personnaliser cette liste ou la charger depuis un fichier
    keywords = default_keywords
    
    # Vérification de la clé API
    if BUILTWITH_API_KEY == 'YOUR_API_KEY_HERE':
        print("⚠ ATTENTION: Clé API BuiltWith non configurée!")
        print("   Veuillez définir BUILTWITH_API_KEY dans votre fichier .env")
        print("   Le script continuera mais échouera probablement.\n")
    
    # Afficher des informations sur les APIs disponibles
    print("=" * 70)
    print("INFORMATIONS SUR LES APIs BUILTWITH")
    print("=" * 70)
    print("\n1. CATALOG API (Recommandé - Accès au catalogue Shopify)")
    print("   - Nécessite un plan payant BuiltWith")
    print("   - Accès direct au catalogue des sites Shopify")
    print("   - Configurez BUILTWITH_API_METHOD='catalog' dans .env")
    print("   - C'est la méthode la plus efficace!")
    print("\n2. TECHNOLOGY SEARCH API (Recherche avec filtres)")
    print("   - Nécessite un plan payant BuiltWith")
    print("   - Permet de rechercher des sites par technologie avec filtres")
    print("   - Configurez BUILTWITH_API_METHOD='technology_search' dans .env")
    print("\n3. DOMAIN LOOKUP API (Pour vérifier des domaines)")
    print("   - Disponible avec l'API gratuite (limite) ou payante")
    print("   - Analyse un domaine spécifique pour vérifier les technologies")
    print("   - Configurez BUILTWITH_API_METHOD='domain_lookup' dans .env")
    print("   - Nécessite un fichier 'domains_to_check.txt' avec les domaines")
    print("\nPour plus d'infos: https://api.builtwith.com")
    print("=" * 70)
    print()
    
    discover_shopify_sites(keywords)


if __name__ == '__main__':
    main()

