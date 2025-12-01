# Scraper Shopify - Architecture Légale

Outil de collecte d'URLs de boutiques Shopify utilisant uniquement des sources légales et publiques.

## 🎯 Objectifs

- **Légalité** : Respect de robots.txt, conditions d'utilisation, rate limiting
- **Robustesse** : Gestion d'erreurs, retry, logging complet
- **Modularité** : Architecture claire avec scrapers séparés
- **Pagination** : Gestion automatique de la pagination
- **Détection Shopify** : Filtrage intelligent des URLs Shopify

## 📁 Structure du Projet

```
.
├── main.py                 # Script principal
├── config.py              # Configuration centralisée
├── requirements.txt        # Dépendances Python
├── .env.example           # Exemple de configuration
├── scrapers/              # Modules de scraping
│   ├── __init__.py
│   ├── base_scraper.py    # Classe de base pour tous les scrapers
│   ├── certificate_transparency.py  # Scraper CT Logs
│   ├── annuaire_scraper.py          # Scraper annuaires publics
│   └── custom_urls_scraper.py        # Scraper URLs personnalisées
├── utils/                 # Utilitaires
│   ├── __init__.py
│   ├── logger.py          # Configuration du logging
│   ├── robots_checker.py  # Vérification robots.txt
│   └── shopify_detector.py # Détection Shopify
├── output/                # Fichiers de sortie
│   ├── shopify_urls.json
│   └── shopify_urls.csv
└── logs/                  # Fichiers de log
    └── scraper.log
```

## 🚀 Installation

1. **Installer les dépendances** :
```bash
pip install -r requirements.txt
```

2. **Configurer l'environnement** :
```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

## ⚙️ Configuration

### Sources de données

Le scraper supporte plusieurs sources légales :

1. **Certificate Transparency Logs** (`crt.sh`)
   - API publique et légale
   - Trouve tous les domaines `*.myshopify.com`
   - Aucune pagination nécessaire

2. **Annuaires publics**
   - `shop.app` (annuaire de sites Shopify) - **Note**: Peut bloquer les requêtes automatisées (403)
   - Gestion automatique de la pagination
   - **Recommandation**: Désactivé par défaut car certains sites bloquent les scrapers

3. **URLs personnalisées**
   - Liste de pages à scraper (fichier texte)
   - Une URL par ligne

### Paramètres principaux

Dans `.env` :

```env
# Activer/désactiver les sources
CT_LOGS_ENABLED=true
ANNUAIRES_ENABLED=true
SHOP_APP_ENABLED=false  # Désactivé par défaut (bloque souvent avec 403)
CUSTOM_URLS_ENABLED=false

# Délais (secondes)
DELAY_BETWEEN_REQUESTS=2.0
DELAY_BETWEEN_PAGES=3.0

# Limites
MAX_PAGES_PER_SOURCE=100
MAX_RETRIES=3

# Respect robots.txt
RESPECT_ROBOTS_TXT=true

# Format de sortie
OUTPUT_FORMAT=json  # ou 'csv'
```

## 📖 Utilisation

### Utilisation basique

```bash
python main.py
```

Le script va :
1. Scraper les sources activées
2. Extraire toutes les URLs de chaque page
3. Filtrer pour ne garder que les URLs Shopify
4. Sauvegarder les résultats dans `output/shopify_urls.json` (ou `.csv`)

### Utiliser des URLs personnalisées

1. Créer un fichier `custom_urls.txt` :
```
https://example.com/shopify-stores
https://another-site.com/listings
```

2. Activer dans `.env` :
```env
CUSTOM_URLS_ENABLED=true
CUSTOM_URLS_FILE=custom_urls.txt
```

3. Lancer le script :
```bash
python main.py
```

## 🔍 Détection Shopify

Le scraper détecte les sites Shopify via :

1. **Vérification rapide** (sans requête HTTP) :
   - Domaines `*.myshopify.com`
   - Patterns dans l'URL (cdn.shopify.com, etc.)

2. **Vérification approfondie** (optionnelle) :
   - Analyse du contenu HTML
   - Détection de patterns Shopify dans le code
   - Activée avec `DEEP_VERIFICATION=true` dans `.env`

## 📊 Logs

Les logs sont sauvegardés dans :
- Console : niveau INFO
- Fichier `logs/scraper.log` : niveau DEBUG

Exemple de log :
```
2024-01-15 10:30:00 - shopify_scraper - INFO - Début du scraping Certificate Transparency
2024-01-15 10:30:05 - shopify_scraper - INFO - 1500 URLs Shopify trouvées
```

## 🛡️ Respect de la légalité

Le scraper respecte :

- ✅ **robots.txt** : Vérification automatique avant chaque requête
- ✅ **Rate limiting** : Délais configurables entre requêtes
- ✅ **User-Agent** : Identification claire du bot
- ✅ **Conditions d'utilisation** : Utilisation uniquement de sources publiques
- ❌ **Pas de contournement** : Aucun bypass de captcha, paywall, ou anti-bot

## 🔧 Personnalisation

### Ajouter une nouvelle source

1. Créer un nouveau scraper dans `scrapers/` :
```python
from scrapers.base_scraper import BaseScraper

class MyCustomScraper(BaseScraper):
    def get_next_page_url(self, current_url, html):
        # Logique de pagination
        pass
    
    def scrape(self, start_url):
        # Logique de scraping
        pass
```

2. L'ajouter dans `main.py` :
```python
from scrapers.my_custom_scraper import MyCustomScraper

scraper = MyCustomScraper()
urls = scraper.scrape("https://example.com")
```

### Modifier la détection Shopify

Éditer `config.py` pour ajouter/modifier les patterns :
```python
SHOPIFY_PATTERNS = [
    r'\.myshopify\.com',
    r'votre_pattern_ici',
]
```

## 📝 Format de sortie

### JSON
```json
{
  "total_urls": 1500,
  "urls": [
    "https://store1.myshopify.com",
    "https://store2.myshopify.com",
    ...
  ]
}
```

### CSV
```csv
url
https://store1.myshopify.com
https://store2.myshopify.com
...
```

## ⚠️ Limitations

- Les annuaires avec scroll infini nécessitent Selenium/Playwright (non implémenté par défaut)
- La vérification approfondie (`DEEP_VERIFICATION`) augmente le temps de scraping
- Certains sites peuvent bloquer les requêtes automatisées (normal et légal)

## 🤝 Contribution

Pour ajouter une nouvelle source légale :
1. Créer un nouveau scraper dans `scrapers/`
2. Respecter l'interface `BaseScraper`
3. Ajouter la configuration dans `config.py`
4. Documenter dans le README

## 📄 Licence

Ce projet est destiné à un usage légal et éthique. Respectez toujours les conditions d'utilisation des sites scrapés.

