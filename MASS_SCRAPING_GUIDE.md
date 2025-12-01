# Guide de Scraping Massif - 4 Millions de Sites Shopify

Ce guide explique comment utiliser le mode scraping massif pour découvrir le maximum de sites Shopify.

## 🚀 Utilisation Rapide

### Scraping Massif Complet (Recommandé)
```bash
python main.py --massive
```

Cette commande va :
- **Scraper shop.app** : Explorer toutes les catégories, combinaisons, pages
- **Rechercher sur le web** : Utiliser Google, Bing, DuckDuckGo avec des milliers de requêtes
- **Combiner les résultats** : shop.app + moteurs de recherche pour maximum de sites
- **Peut prendre plusieurs jours et générer des millions d'URLs**

### Stratégies Spécifiques

**Seulement les catégories** (plus rapide) :
```bash
python main.py --massive --strategy categories
```

**Seulement les combinaisons de recherche** :
```bash
python main.py --massive --strategy combinations
```

**Seulement la découverte automatique** :
```bash
python main.py --massive --strategy discovery
```

**Seulement la pagination agressive** :
```bash
python main.py --massive --strategy pagination
```

## 📊 Stratégies Disponibles

### 1. `comprehensive` (Par défaut)
- Combine toutes les stratégies
- Maximum de sites trouvés
- **Très long** (plusieurs jours)

### 2. `categories`
- Explore 50+ catégories
- 1000 pages par catégorie
- **Rapide et efficace**

### 3. `combinations`
- Recherches par lettres (a-z, aa-zz)
- Recherches par chiffres (0-99)
- Mots-clés courants
- **Bon compromis**

### 4. `discovery`
- Exploration récursive profonde (niveau 5)
- Découvre automatiquement toutes les pages
- **Moyennement rapide**

### 5. `pagination`
- Pagination agressive de la recherche générale
- Jusqu'à 5000 pages
- **Simple mais efficace**

### 6. `web`
- Recherche uniquement sur les moteurs de recherche web
- Google, Bing, DuckDuckGo
- **Bon pour trouver des sites non listés sur shop.app**

## ⚙️ Configuration

Dans `config.py`, vous pouvez ajuster :

```python
MASS_SCRAPE_MAX_PAGES = 1000  # Pages par recherche
MASS_SCRAPE_MAX_WORKERS = 10  # Threads parallèles
MASS_SCRAPE_MAX_DEPTH = 5     # Profondeur d'exploration
DELAY_BETWEEN_REQUESTS = 1    # Délai entre requêtes (secondes)
```

## 💾 Espace Disque Requis

Pour 4 millions de sites :
- **JSON** : ~2-4 GB
- **CSV** : ~500 MB - 1 GB
- **Total recommandé** : 10 GB d'espace libre

## ⏱️ Temps Estimé

- **Catégories seulement** : 2-5 heures
- **Combinaisons** : 5-10 heures  
- **Comprehensive** : 2-7 jours (selon votre connexion)

## 🔧 Optimisations

### Pour aller plus vite :
1. Réduire `DELAY_BETWEEN_REQUESTS` à 0.5 secondes
2. Augmenter `MASS_SCRAPE_MAX_WORKERS` à 20
3. Désactiver la vérification : ne pas utiliser `--verify-all`

### Pour plus de sites :
1. Augmenter `MASS_SCRAPE_MAX_PAGES` à 5000
2. Augmenter `MASS_SCRAPE_MAX_DEPTH` à 7
3. Utiliser `--strategy comprehensive`

## ⚠️ Avertissements

1. **Ressources** : Le scraping massif utilise beaucoup de CPU, RAM et bande passante
2. **Temps** : Peut prendre plusieurs jours pour 4 millions de sites
3. **Espace disque** : Assurez-vous d'avoir suffisamment d'espace
4. **Rate limiting** : shop.app peut limiter les requêtes si trop agressif

## 📝 Exemple de Sortie

```
=== SCRAPING MASSIF DE SHOP.APP ===

=== STRATÉGIE 1: EXPLORATION DES CATÉGORIES ===
Exploration de 50 catégories...
  Catégorie 'fashion': 1250 URLs
  Catégorie 'electronics': 890 URLs
  ...

=== STRATÉGIE 2: RECHERCHES PAR COMBINAISONS ===
Scraping parallèle de 1000 requêtes avec 10 workers...
  [1/1000] 'a' terminé: 45 URLs
  ...

TOTAL FINAL: 3,847,293 URLs UNIQUES TROUVÉES
```

## 🎯 Objectif : 4 Millions de Sites

Pour atteindre 4 millions de sites, utilisez :

```bash
# Commande optimale
python main.py --massive --strategy comprehensive
```

Et laissez tourner pendant plusieurs jours. Le script sauvegarde automatiquement les résultats au fur et à mesure.

