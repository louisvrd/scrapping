"""
Configuration centralisée pour le scraper Shopify.
Les valeurs peuvent être surchargées par des variables d'environnement.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ==================== CHEMINS ====================
BASE_DIR = Path(__file__).parent

# Charger les variables d'environnement depuis .env
# Utiliser override=True pour forcer le rechargement et dotenv_path pour être explicite
# Convertir le Path en string pour compatibilité avec load_dotenv sur tous les systèmes
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path), override=True)
else:
    # Essayer de charger depuis le répertoire courant
    load_dotenv(override=True)
OUTPUT_DIR = BASE_DIR / os.getenv('OUTPUT_DIR', 'output')
LOGS_DIR = BASE_DIR / os.getenv('LOGS_DIR', 'logs')

# Créer les dossiers s'ils n'existent pas
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ==================== SOURCES DE DONNÉES ====================
# Sources légales pour découvrir des sites Shopify

# 1. Certificate Transparency Logs (crt.sh) - API publique
CT_LOGS_ENABLED = os.getenv('CT_LOGS_ENABLED', 'true').lower() == 'true'
CT_LOGS_URL = os.getenv('CT_LOGS_URL', 'https://crt.sh')
CT_LOGS_MAX_RESULTS = int(os.getenv('CT_LOGS_MAX_RESULTS', '50000'))  # Augmenté pour obtenir plus de résultats (20000+ URLs)
CT_LOGS_USE_VARIANTS = os.getenv('CT_LOGS_USE_VARIANTS', 'true').lower() == 'true'  # Utiliser plusieurs variantes de requêtes

# 2. Annuaires publics (shop.app, etc.)
# Note: Certains annuaires peuvent bloquer les requêtes automatisées (403 Forbidden)
# C'est normal et légal - le site protège ses ressources
ANNUAIRES_ENABLED = os.getenv('ANNUAIRES_ENABLED', 'true').lower() == 'true'
ANNUAIRES_SOURCES = [
    {
        'name': 'shop.app',
        'base_url': 'https://shop.app',
        'enabled': os.getenv('SHOP_APP_ENABLED', 'false').lower() == 'true',  # Désactivé par défaut (bloque souvent)
        'pagination_type': 'infinite_scroll',  # ou 'numbered', 'next_button'
    },
    # Vous pouvez ajouter d'autres annuaires ici
    # Exemple:
    # {
    #     'name': 'autre_annuaire',
    #     'base_url': 'https://example.com',
    #     'enabled': os.getenv('AUTRE_ANNUAIRE_ENABLED', 'false').lower() == 'true',
    #     'pagination_type': 'next_button',
    # },
]

# 3. URLs personnalisées (liste de pages à scraper)
CUSTOM_URLS_ENABLED = os.getenv('CUSTOM_URLS_ENABLED', 'false').lower() == 'true'
CUSTOM_URLS_FILE = os.getenv('CUSTOM_URLS_FILE', 'custom_urls.txt')  # Fichier avec une URL par ligne

# 4. GitHub (recherche dans les repositories publics)
GITHUB_ENABLED = os.getenv('GITHUB_ENABLED', 'true').lower() == 'true'

# 5. Listes publiques (forums, blogs, etc.)
PUBLIC_LISTS_ENABLED = os.getenv('PUBLIC_LISTS_ENABLED', 'true').lower() == 'true'

# 6. Générateur de domaines (génère des combinaisons possibles - DÉSACTIVÉ car génère des URLs non vérifiées)
DOMAIN_GENERATOR_ENABLED = os.getenv('DOMAIN_GENERATOR_ENABLED', 'false').lower() == 'true'
DOMAIN_GENERATOR_MAX = int(os.getenv('DOMAIN_GENERATOR_MAX', '20000'))  # Nombre de domaines à générer

# 7. CT Alternatif (autres endpoints de Certificate Transparency)
CT_ALTERNATIVE_ENABLED = os.getenv('CT_ALTERNATIVE_ENABLED', 'true').lower() == 'true'

# 8. Internet Archive / Wayback Machine
WEB_ARCHIVE_ENABLED = os.getenv('WEB_ARCHIVE_ENABLED', 'true').lower() == 'true'

# 9. ProjectDiscovery Sonar (découverte de sous-domaines)
SONAR_ENABLED = os.getenv('SONAR_ENABLED', 'true').lower() == 'true'
SONAR_URL = os.getenv('SONAR_URL', 'https://chaos.projectdiscovery.io')
SONAR_MAX_RESULTS = int(os.getenv('SONAR_MAX_RESULTS', '100000'))  # Nombre max de résultats

# 10. GitHub Authentication (optionnel - pour augmenter les limites de rate)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '').strip()  # Token GitHub pour authentification (optionnel)
# Enlever les guillemets si présents
if GITHUB_TOKEN and (GITHUB_TOKEN.startswith('"') or GITHUB_TOKEN.startswith("'")):
    GITHUB_TOKEN = GITHUB_TOKEN.strip('"\'')

# ==================== PARAMÈTRES DE SCRAPING ====================
# Délais et limites
DELAY_BETWEEN_REQUESTS = float(os.getenv('DELAY_BETWEEN_REQUESTS', '2.0'))  # Secondes
DELAY_BETWEEN_PAGES = float(os.getenv('DELAY_BETWEEN_PAGES', '3.0'))  # Secondes entre pages
MAX_PAGES_PER_SOURCE = int(os.getenv('MAX_PAGES_PER_SOURCE', '100'))  # Nombre max de pages à scraper
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))  # Nombre de tentatives en cas d'erreur
TIMEOUT = int(os.getenv('TIMEOUT', '30'))  # Timeout des requêtes en secondes

# User-Agent
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# ==================== DÉTECTION SHOPIFY ====================
# Patterns pour identifier les sites Shopify
SHOPIFY_PATTERNS = [
    r'\.myshopify\.com',  # Domaines myshopify.com
    r'cdn\.shopify\.com',  # CDN Shopify
    r'shopifycdn\.com',
    r'Shopify\.theme',
    r'window\.Shopify',
    r'data-shopify',
    r'shopify-section',
]

# Vérification approfondie (nécessite une requête supplémentaire)
DEEP_VERIFICATION = os.getenv('DEEP_VERIFICATION', 'false').lower() == 'true'  # Vérifier le contenu HTML pour détecter Shopify

# ==================== RESPECT ROBOTS.TXT ====================
RESPECT_ROBOTS_TXT = os.getenv('RESPECT_ROBOTS_TXT', 'true').lower() == 'true'

# ==================== LOGGING ====================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = LOGS_DIR / 'scraper.log'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ==================== FORMAT DE SORTIE ====================
OUTPUT_FORMAT = os.getenv('OUTPUT_FORMAT', 'json').lower()  # 'json' ou 'csv'
OUTPUT_FILE_JSON = OUTPUT_DIR / 'shopify_urls.json'
OUTPUT_FILE_CSV = OUTPUT_DIR / 'shopify_urls.csv'

# ==================== SELENIUM/PLAYWRIGHT (optionnel) ====================
USE_SELENIUM = os.getenv('USE_SELENIUM', 'false').lower() == 'true'  # Pour sites très dynamiques
SELENIUM_BROWSER = os.getenv('SELENIUM_BROWSER', 'chrome').lower()
SELENIUM_HEADLESS = os.getenv('SELENIUM_HEADLESS', 'true').lower() == 'true'

USE_PLAYWRIGHT = os.getenv('USE_PLAYWRIGHT', 'false').lower() == 'true'  # Alternative à Selenium
PLAYWRIGHT_BROWSER = os.getenv('PLAYWRIGHT_BROWSER', 'chromium').lower()
PLAYWRIGHT_HEADLESS = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
