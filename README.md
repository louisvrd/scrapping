# Outil de Scraping Shopify

Outil automatisé en Python pour identifier des sites web utilisant Shopify, scraper leurs pages de contact pour extraire les adresses e-mail et numéros de téléphone, puis stocker ces informations dans une base de données PostgreSQL.

## 📋 Structure du Projet

Le projet est organisé en deux phases distinctes :

- **Phase 1** : Découverte de sites Shopify (méthode gratuite ou via API BuiltWith)
- **Phase 2** : Scraping des pages de contact et stockage en base de données

## 🚀 Installation

### Prérequis

- Python 3.8 ou supérieur
- PostgreSQL 12 ou supérieur
- Clé API BuiltWith (obtenez-la sur [https://builtwith.com/api](https://builtwith.com/api))

### ⚠️ Important : Choix de l'API BuiltWith

BuiltWith propose plusieurs APIs selon votre plan :

**1. Catalog API** (Recommandé - Plans payants)
- Accès direct au **catalogue BuiltWith** des sites Shopify
- Idéal pour la Phase 1 du projet - méthode la plus efficace
- Nécessite un plan payant avec accès à cette fonctionnalité
- Configurez `BUILTWITH_API_METHOD=catalog` dans `.env`

**2. Technology Search API** (Plans payants)
- Permet de rechercher des sites par technologie avec filtres
- Alternative au catalogue si vous avez besoin de filtres spécifiques
- Configurez `BUILTWITH_API_METHOD=technology_search` dans `.env`

**2. Domain Lookup API** (Gratuit avec limites ou Payant)
- Permet d'**analyser** un domaine spécifique pour vérifier les technologies
- Ne permet PAS de découvrir des sites par technologie
- Utile si vous avez déjà une liste de domaines à vérifier
- Configurez `BUILTWITH_API_METHOD=domain_lookup` dans `.env`
- Nécessite un fichier `domains_to_check.txt` avec les domaines à vérifier

**3. Free API** (Gratuit mais très limité)
- Similaire à Domain Lookup mais avec des limites strictes
- Utile uniquement pour des tests

**Recommandation** : Si vous voulez découvrir des sites Shopify automatiquement, vous avez besoin d'un plan BuiltWith avec accès à la **Technology Search API**. Sinon, vous devrez générer une liste de domaines par d'autres moyens (recherche Google, listes publiques, etc.) et utiliser Domain Lookup pour les vérifier.

### Étapes d'installation

1. **Cloner ou télécharger le projet**

2. **Installer les dépendances Python**

```bash
pip install -r requirements.txt
```

3. **Configurer les variables d'environnement**

Copiez le fichier `env.example` vers `.env` et remplissez les valeurs :

```bash
cp env.example .env
```

Éditez le fichier `.env` avec vos informations :

```env
BUILTWITH_API_KEY=votre_cle_api_builtwith
BUILTWITH_API_METHOD=catalog
MAX_RESULTS=1000
DB_HOST=localhost
DB_PORT=5432
DB_NAME=shopify_scraper
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe
```

4. **Créer la base de données PostgreSQL**

Connectez-vous à PostgreSQL et créez la base de données :

```sql
CREATE DATABASE shopify_scraper;
```

5. **Créer les tables**

Exécutez le script SQL pour créer la structure de la base de données :

```bash
psql -U postgres -d shopify_scraper -f schema.sql
```

Ou depuis psql :

```sql
\c shopify_scraper
\i schema.sql
```

## 📖 Utilisation

### Phase 1 : Découverte de sites Shopify

Vous avez **deux options** pour découvrir des sites Shopify :

#### Option A : Méthode GRATUITE (Recommandée) 🆓

Le script `discover_free.py` utilise plusieurs méthodes gratuites pour découvrir des sites Shopify **sans aucune clé API payante**.

**⚠️ Important : Utilisation de Selenium (recommandé)**

Par défaut, le script utilise **Selenium** avec un navigateur réel (Chrome, Firefox ou Edge) pour contourner les blocages des moteurs de recherche comme Bing. Cela permet d'être beaucoup moins détectable qu'avec de simples requêtes HTTP.

**Configuration Selenium dans `.env` :**

```env
# Activer Selenium (recommandé pour éviter les blocages)
USE_SELENIUM=true

# Navigateur à utiliser: chrome, firefox, edge
# Chrome est recommandé pour la meilleure compatibilité
SELENIUM_BROWSER=chrome

# Mode headless (sans interface graphique) - true ou false
SELENIUM_HEADLESS=true
```

**Installation des drivers Selenium :**

Les drivers sont automatiquement téléchargés et gérés par `webdriver-manager`. Assurez-vous d'avoir installé les dépendances :

```bash
pip install -r requirements.txt
```

**Note :** Si Selenium n'est pas disponible ou échoue, le script basculera automatiquement sur `requests` (mais peut être bloqué par Bing).

Le script `discover_free.py` utilise plusieurs méthodes gratuites pour découvrir des sites Shopify :

- **Recherche DuckDuckGo** : Plus permissif que Google, permet de nombreuses requêtes
- **Scraping de shop.app** : Annuaire public de sites Shopify
- **Génération de patterns** : Teste des combinaisons possibles de noms de stores
- **Listes publiques** : Extrait depuis GitHub, forums, etc.

**Utilisation :**
```bash
python discover_free.py
```

**Configuration dans `.env` :**
```env
MAX_RESULTS=5000  # Nombre maximum de domaines à découvrir
DELAY_BETWEEN_REQUESTS=1.0  # Délai entre requêtes (secondes)
```

**Avantages :**
- ✅ 100% gratuit
- ✅ Aucune clé API requise
- ✅ Plusieurs méthodes combinées pour maximiser les résultats
- ✅ Contrôle total sur le nombre de requêtes

**Inconvénients :**
- ⚠️ Plus lent que l'API BuiltWith
- ⚠️ Peut être limité par les moteurs de recherche (Google bloque souvent)
- ⚠️ Nécessite plus de requêtes pour obtenir beaucoup de résultats

#### Option B : Méthode BuiltWith API (Payante)

Le script `discover.py` interroge l'API BuiltWith pour découvrir des sites Shopify.

**Exécution :**

```bash
# Méthode gratuite (recommandée)
python discover_free.py

# OU méthode BuiltWith (payante)
python discover.py
```

**Fonctionnement de discover_free.py :**

Le script utilise Selenium (par défaut) pour simuler un navigateur réel et éviter les blocages. Il parcourt exactement 100 pages pour chaque requête de recherche, ce qui permet de découvrir un grand nombre de sites Shopify.

Le script utilise plusieurs méthodes en parallèle :

**Mode Catalog** (`BUILTWITH_API_METHOD=catalog`) - **RECOMMANDÉ** :
- Accède directement au catalogue BuiltWith des sites Shopify
- Récupère la liste complète (ou paginée) des sites Shopify
- Méthode la plus efficace et rapide
- Nécessite un plan payant avec accès au catalogue
- Les domaines sont sauvegardés dans `domains_to_scrape.txt`
- Vous pouvez limiter le nombre de résultats avec `MAX_RESULTS` dans `.env`

**Mode Technology Search** (`BUILTWITH_API_METHOD=technology_search`) :
- Utilise l'API Technology Search de BuiltWith
- Recherche des sites utilisant Shopify avec possibilité de filtres
- Nécessite un plan payant avec accès à cette fonctionnalité
- Les domaines uniques sont sauvegardés dans `domains_to_scrape.txt`

**Mode Domain Lookup** (`BUILTWITH_API_METHOD=domain_lookup`) :
- Lit un fichier `domains_to_check.txt` (un domaine par ligne)
- Vérifie chaque domaine pour confirmer l'utilisation de Shopify
- Les domaines confirmés sont sauvegardés dans `domains_to_scrape.txt`
- Utile si vous avez déjà une liste de domaines à vérifier

**Personnalisation :**

Vous pouvez modifier la liste de mots-clés dans la fonction `main()` de `discover.py` :

```python
keywords = [
    "boutique de vêtements",
    "jewelry store",
    "fashion france",
    "votre mot-clé ici"
]
```

**Gestion des erreurs :**

- Le script gère automatiquement les limites de taux de l'API (429)
- Les erreurs d'authentification sont signalées
- Un mécanisme de retry est implémenté pour les erreurs temporaires

### Phase 2 : Scraping des pages de contact

Le script `scraper.py` lit le fichier `domains_to_scrape.txt`, visite chaque page de contact, extrait les informations et les stocke en base de données.

**Exécution :**

```bash
python scraper.py
```

**Fonctionnement :**

1. Lit le fichier `domains_to_scrape.txt` ligne par ligne
2. Pour chaque domaine :
   - Cherche la page de contact (essaie `/pages/contact` puis `/contact`)
   - Scrape le contenu HTML de la page
   - Extrait l'adresse e-mail (première trouvée)
   - Extrait le numéro de téléphone (premier trouvé, format international ou français)
   - Sauvegarde les données en base de données PostgreSQL

**Priorité des URLs de contact :**

1. `https://[domaine]/pages/contact`
2. `https://[domaine]/contact`
3. `https://[domaine]/pages/contact-us`
4. `https://[domaine]/contact-us`

**Gestion des erreurs :**

- Retry automatique en cas d'erreur serveur (5xx)
- Gestion des timeouts
- Gestion des erreurs réseau
- Les domaines sans page de contact sont quand même enregistrés (sans email/phone)

**Prévention des doublons :**

Le script utilise `ON CONFLICT (url) DO NOTHING` pour éviter les doublons si un domaine est traité plusieurs fois.

## 📊 Base de Données

### Structure de la table `shopify_contacts`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | SERIAL | Identifiant unique (clé primaire) |
| `url` | VARCHAR(255) | URL du domaine Shopify (unique) |
| `email` | VARCHAR(255) | Adresse e-mail extraite |
| `phone_number` | VARCHAR(50) | Numéro de téléphone extrait |
| `contact_page_url` | VARCHAR(255) | URL de la page de contact utilisée |
| `scraped_at` | TIMESTAMP WITH TIME ZONE | Date et heure du scraping |

### Requêtes utiles

**Voir tous les contacts extraits :**

```sql
SELECT * FROM shopify_contacts ORDER BY scraped_at DESC;
```

**Compter les contacts avec email :**

```sql
SELECT COUNT(*) FROM shopify_contacts WHERE email IS NOT NULL;
```

**Compter les contacts avec téléphone :**

```sql
SELECT COUNT(*) FROM shopify_contacts WHERE phone_number IS NOT NULL;
```

**Voir les statistiques :**

```sql
SELECT 
    COUNT(*) as total,
    COUNT(email) as avec_email,
    COUNT(phone_number) as avec_telephone,
    COUNT(*) FILTER (WHERE email IS NOT NULL AND phone_number IS NOT NULL) as avec_les_deux
FROM shopify_contacts;
```

## 🔧 Configuration Avancée

### Modifier les paramètres de scraping

Dans `scraper.py`, vous pouvez ajuster :

- `MAX_RETRIES` : Nombre de tentatives en cas d'erreur (défaut: 3)
- `RETRY_DELAY` : Délai entre les tentatives en secondes (défaut: 2)
- `REQUEST_TIMEOUT` : Timeout des requêtes HTTP en secondes (défaut: 10)
- `USER_AGENT` : User-Agent utilisé pour les requêtes

### Modifier les patterns d'extraction

Les expressions régulières pour l'extraction d'email et de téléphone sont définies dans `scraper.py` :

- `EMAIL_PATTERN` : Pattern pour les adresses e-mail
- `PHONE_PATTERN` : Pattern pour les numéros de téléphone (français et international)

## ⚠️ Notes Importantes

1. **Respect des robots.txt** : Ce script ne vérifie pas automatiquement les fichiers robots.txt. Assurez-vous de respecter les conditions d'utilisation des sites web que vous scrapez.

2. **Limites de taux** : L'API BuiltWith a des limites de taux. Le script gère automatiquement les erreurs 429, mais vous devrez peut-être ajuster les délais entre les requêtes.

3. **Performance** : Le scraping peut être lent pour un grand nombre de domaines. Le script inclut des pauses entre les requêtes pour éviter la surcharge.

4. **Données extraites** : Les patterns d'extraction peuvent ne pas capturer tous les formats d'email/téléphone. Vous pouvez les ajuster selon vos besoins.

## 🐛 Dépannage

### Erreur de connexion à la base de données

- Vérifiez que PostgreSQL est démarré
- Vérifiez les identifiants dans `.env`
- Vérifiez que la base de données existe

### Erreur d'API BuiltWith

- Vérifiez que votre clé API est correcte dans `.env`
- Vérifiez que vous n'avez pas dépassé les limites de votre plan API
- Attendez quelques minutes si vous recevez des erreurs 429 (limite de taux)

### Aucune donnée extraite

- Vérifiez que les pages de contact contiennent bien des emails/téléphones en texte brut
- Certains sites utilisent des formulaires JavaScript qui ne sont pas accessibles via BeautifulSoup
- Les emails/téléphones dans des images ne seront pas détectés

## 📝 Licence

Ce projet est fourni tel quel, sans garantie. Utilisez-le de manière responsable et respectez les conditions d'utilisation des sites web que vous scrapez.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.
