# Shopify Scanner - Node.js/TypeScript

Système de détection de sites Shopify via recherche web avec Playwright.

## 🚀 Installation

```bash
# Installer les dépendances
npm install

# Installer les navigateurs Playwright
npx playwright install chromium
```

## 📖 Usage

### ⚠️ IMPORTANT : Certificate Transparency n'est PAS une source fiable

**Les sous-domaines individuels "xxx.myshopify.com" ne sont PAS présents dans les CT logs de façon exploitable.**
CT n'est **PAS une bonne source** pour énumérer les boutiques Shopify hébergées sur myshopify.com.

Les modules CT sont conservés à des fins expérimentales mais ne doivent **PAS être utilisés comme source primaire**.

### Mode scan Bing Bulk (RECOMMANDÉ - source primaire fiable)

```bash
# Utiliser les requêtes depuis le fichier de config
npm run shopify-scan-bing-bulk -- --config

# Utiliser un fichier queries.txt personnalisé
npm run shopify-scan-bing-bulk -- queries.txt

# Avec options personnalisées
npm run shopify-scan-bing-bulk -- queries.txt --maxResults=100 --sleepMs=5000
```

Ce mode utilise des requêtes de recherche Bing avec l'opérateur `site:myshopify.com` pour découvrir des boutiques Shopify de manière fiable.

**Format du fichier queries.txt :**
```
site:myshopify.com "bracelets"
site:myshopify.com "yoga"
site:myshopify.com "bijoux"
# Commentaires (lignes commençant par # sont ignorées)
```

**Exemples :**
```bash
# Utiliser le fichier de config (requêtes prédéfinies)
npm run shopify-scan-bing-bulk -- --config

# Utiliser un fichier personnalisé
npm run shopify-scan-bing-bulk -- queries.txt

# Avec plus de résultats par requête
npm run shopify-scan-bing-bulk -- --config --maxResults=100
```

### Mode scan Certificate Transparency (EXPÉRIMENTAL - ne pas utiliser comme source primaire)

```bash
npm run shopify-scan-ct -- "%.myshopify.com"
```

⚠️ **EXPÉRIMENTAL** : Ce mode utilise Certificate Transparency (crt.sh) mais **ne trouve PAS les sous-domaines myshopify.com de façon exploitable**.

Les modules CT sont conservés à des fins expérimentales mais ne doivent **PAS être utilisés comme source primaire** pour la découverte de shops Shopify.

**Utilisez plutôt `shopify-scan-bing-bulk` qui est la source primaire recommandée.**

### Mode scan massif (sources publiques)

```bash
npm run shopify-scan -- --massive
```

Ce mode utilise plusieurs sources publiques (CT, GitHub) pour trouver le maximum de sites Shopify.

### Mode scan ciblé (pour une niche spécifique)

```bash
npm run shopify-scan -- "votre requête de recherche"
```

### Exemples complets

```bash
# Scan CT - RECOMMANDÉ pour trouver des milliers d'URLs
npm run shopify-scan-ct -- "%.myshopify.com"

# Scan CT avec limite
npm run shopify-scan-ct -- "%.myshopify.com" 10000

# Scan massif - sources publiques
npm run shopify-scan -- --massive

# Scan ciblé - recherche des sites de bijoux
npm run shopify-scan -- "bijoux artisanaux"
```

## 🔧 Configuration

Les options peuvent être configurées via des variables d'environnement :

- `MAX_RESULTS` : Nombre maximum de résultats à analyser (défaut: 20)
- `TIMEOUT` : Timeout pour les requêtes HTTP en ms (défaut: 10000)
- `HEADLESS` : Mode headless du navigateur (défaut: true, mettre à "false" pour voir le navigateur)
- `CHROME_USER_DATA_DIR` : Chemin vers le profil Chrome (optionnel, pour charger les extensions)
- `SERP_API_KEY` : Clé API pour SerpAPI (optionnel, utilisé si tous les moteurs bloquent)

### 🌐 Navigateur utilisé : Chrome

Le système utilise **Chrome** (pas Chromium) pour supporter les extensions de navigateur, notamment les extensions de résolution de captcha.

**Vérifier que Chrome est installé :**
```bash
# Windows
where chrome

# Linux/Mac
which google-chrome
```

**Charger un profil Chrome avec extensions :**
Si vous avez installé une extension de résolution de captcha dans Chrome, vous pouvez charger votre profil Chrome :

**⚠️ IMPORTANT : Fermez Chrome avant de lancer le scan !**

```powershell
# Windows PowerShell - Méthode 1 (recommandée)
Set-Item -Path env:CHROME_USER_DATA_DIR -Value "C:\Users\VotreNom\AppData\Local\Google\Chrome\User Data"
Set-Item -Path env:HEADLESS -Value "false"
npm run shopify-scan-bing-bulk -- --config

# Windows PowerShell - Méthode 2 (alternative)
$env:CHROME_USER_DATA_DIR = "C:\Users\VotreNom\AppData\Local\Google\Chrome\User Data"
$env:HEADLESS = "false"
npm run shopify-scan-bing-bulk -- --config
```

```cmd
REM Windows CMD (utiliser des guillemets pour les espaces)
set "CHROME_USER_DATA_DIR=C:\Users\VotreNom\AppData\Local\Google\Chrome\User Data"
set HEADLESS=false
npm run shopify-scan-bing-bulk -- --config
```

```bash
# Linux/Mac
export CHROME_USER_DATA_DIR=~/.config/google-chrome
export HEADLESS=false
npm run shopify-scan-bing-bulk -- --config
```

**Exemple complet pour votre système :**
```powershell
# 1. Fermez Chrome d'abord !
# 2. Configurez les variables (méthode recommandée)
Set-Item -Path env:CHROME_USER_DATA_DIR -Value "C:\Users\Philippe\AppData\Local\Google\Chrome\User Data"
Set-Item -Path env:HEADLESS -Value "false"

# 3. Lancez le scan
npm run shopify-scan-bing-bulk -- --config
```

**Ou en une seule fois :**
```powershell
Set-Item -Path env:CHROME_USER_DATA_DIR -Value "C:\Users\Philippe\AppData\Local\Google\Chrome\User Data"; Set-Item -Path env:HEADLESS -Value "false"; npm run shopify-scan-bing-bulk -- --config
```

**Note importante :** 
- Le profil Chrome doit être fermé avant de lancer le scan (Playwright ne peut pas utiliser un profil déjà ouvert)
- Pour trouver le chemin de votre profil Chrome :
  - Windows : `%LOCALAPPDATA%\Google\Chrome\User Data` (ex: `C:\Users\VotreNom\AppData\Local\Google\Chrome\User Data`)
  - Linux : `~/.config/google-chrome`
  - Mac : `~/Library/Application Support/Google/Chrome`

**Syntaxe PowerShell vs CMD/Bash :**

En PowerShell, utilisez `$env:VARIABLE="valeur"` au lieu de `VARIABLE=valeur` :

```powershell
# PowerShell (Windows)
$env:HEADLESS="false"
$env:CHROME_USER_DATA_DIR="C:\Users\VotreNom\AppData\Local\Google\Chrome\User Data"
npm run shopify-scan-bing-bulk -- --config
```

```cmd
# CMD (Windows)
set HEADLESS=false
set CHROME_USER_DATA_DIR=C:\Users\VotreNom\AppData\Local\Google\Chrome\User Data
npm run shopify-scan-bing-bulk -- --config
```

```bash
# Bash (Linux/Mac)
export HEADLESS=false
export CHROME_USER_DATA_DIR=~/.config/google-chrome
npm run shopify-scan-bing-bulk -- --config
```

### Gestion des captchas

Le système essaie automatiquement plusieurs moteurs de recherche dans cet ordre :
1. **Google** (peut être bloqué)
2. **DuckDuckGo** (généralement plus tolérant)
3. **Bing** (peut être bloqué)
4. **API tierce** (si `SERP_API_KEY` est configurée)

Si tous les moteurs échouent :
- Attendez quelques minutes avant de réessayer
- Utilisez `$env:HEADLESS="false"` (PowerShell) ou `set HEADLESS=false` (CMD) pour voir ce qui se passe
- Configurez une API tierce (SerpAPI, ScraperAPI, etc.)

## 📁 Structure du projet

```
src/
├── config/          # Configuration
├── navigate/        # Navigation avec Playwright (recherche Google)
├── network/         # Vérifications réseau (DNS, fetch HTML)
├── detect/          # Détection Shopify
├── pipeline/        # Pipeline principal (orchestration)
└── cli/             # Interface en ligne de commande
```

## 🎯 Fonctionnalités

1. **Recherche Google** : Utilise Playwright pour rechercher sur Google et extraire les URLs organiques
2. **Vérification DNS** : Vérifie que chaque domaine existe avant de continuer
3. **Récupération HTML** : Télécharge le contenu HTML de chaque page
4. **Détection Shopify** : Analyse le HTML pour détecter les sites Shopify avec un score de confiance
5. **Export JSON** : Sauvegarde les résultats dans `output/shopify-scan-<timestamp>.json`

## 📊 Format de sortie

Le fichier JSON contient :

```json
{
  "query": "votre requête",
  "scannedCount": 20,
  "shopifyCount": 5,
  "results": [
    {
      "title": "Titre du site",
      "url": "https://example.com",
      "dnsOk": true,
      "htmlFetched": true,
      "isShopify": true,
      "confidence": 0.9
    }
  ],
  "shopifyUrls": [
    "https://shop1.com",
    "https://shop2.com"
  ]
}
```

## 🛠️ Développement

```bash
# Compiler TypeScript
npm run build

# Mode développement (watch)
npm run dev
```

## ⚠️ Notes importantes

- Le système utilise un navigateur headless (Playwright) pour éviter la détection
- Les résultats sont basés sur l'analyse du HTML (patterns Shopify)
- Le score de confiance varie de 0 à 1 (1 = très confiant)
- Les erreurs individuelles (DNS, timeout) n'interrompent pas le scan complet

## 🚀 Scan Bing Bulk (RECOMMANDÉ - Source Primaire)

Le scan Bing bulk est la méthode la plus fiable pour découvrir des boutiques Shopify :

```bash
# Utiliser les requêtes depuis config/queries-shopify.ts
npm run shopify-scan-bing-bulk -- --config

# Utiliser un fichier queries.txt personnalisé
npm run shopify-scan-bing-bulk -- queries.txt

# Avec options personnalisées
npm run shopify-scan-bing-bulk -- queries.txt --maxResults=100 --sleepMs=5000
```

**Avantages du scan Bing bulk :**
- ✅ Source fiable : utilise les résultats de recherche réels
- ✅ Découvre des boutiques Shopify actives et indexées
- ✅ Pas de limite artificielle comme CT
- ✅ Détection Shopify via HTML (très fiable)
- ✅ Support de requêtes personnalisées par niche

**Format du fichier queries.txt :**
- Une requête par ligne
- Format recommandé : `site:myshopify.com "mot-clé"`
- Les lignes commençant par `#` sont ignorées (commentaires)

**Exemple de queries.txt :**
```
site:myshopify.com "bracelets"
site:myshopify.com "yoga"
site:myshopify.com "bijoux"
# Commentaire
site:myshopify.com "jewelry"
```

**Options disponibles :**
- `--config, -c` : Utiliser les requêtes depuis `config/queries-shopify.ts`
- `--maxResults=N` : Nombre max de résultats par requête (défaut: 50)
- `--sleepMs=N` : Pause en ms entre requêtes (défaut: 3000)

## ⚠️ Scan Certificate Transparency (EXPÉRIMENTAL - Ne pas utiliser comme source primaire)

⚠️ **IMPORTANT** : Les sous-domaines individuels "xxx.myshopify.com" ne sont **PAS présents dans les CT logs** de façon exploitable. CT n'est **PAS une bonne source** pour énumérer les boutiques Shopify.

Les modules CT sont conservés à des fins expérimentales mais ne doivent **PAS être utilisés comme source primaire**.

```bash
# Scan CT standard (expérimental)
npm run shopify-scan-ct -- "%.myshopify.com"
```

### Mode scan CT massif (EXPÉRIMENTAL)

Le scan CT massif utilise des patterns alphabétiques pour récupérer massivement des domaines Shopify depuis Certificate Transparency.

```bash
# Scan avec patterns de profondeur 1 (a%, b%, c%, ..., z%)
npm run shopify-ct-mass -- --depth=1

# Scan avec profondeur 1 + chiffres (a%, b%, ..., z%, 0%, ..., 9%)
npm run shopify-ct-mass -- --depth=1 --digits=true

# Scan avec profondeur 2 (aa%, ab%, ac%, ..., zz%) - BEAUCOUP plus de patterns
npm run shopify-ct-mass -- --depth=2

# Avec limite totale de domaines
npm run shopify-ct-mass -- --depth=1 --maxTotalDomains=50000

# Avec limite par pattern et pause personnalisée
npm run shopify-ct-mass -- --depth=1 --limitPerPattern=5000 --sleepMs=1000

# Format simple (depth uniquement)
npm run shopify-ct-mass -- 1  # depth=1
npm run shopify-ct-mass -- 2  # depth=2
```

**Options disponibles :**
- `--depth=1|2` : Profondeur des patterns (1: a%, b%, ... | 2: aa%, ab%, ...)
- `--digits=true|false` : Inclure les chiffres 0-9 dans l'alphabet (défaut: false)
- `--limitPerPattern=N` : Nombre max de domaines par pattern (défaut: illimité)
- `--maxTotalDomains=N` : Nombre max total de domaines (défaut: illimité)
- `--sleepMs=N` : Pause en ms entre requêtes (défaut: 500)
- `--timeout=N` : Timeout en ms pour chaque requête (défaut: 60000)

**Résultat :**
Le scan génère un fichier JSON dans `output/ct-mass-domains-<timestamp>.json` contenant :
- Tous les domaines uniques collectés
- Les patterns utilisés
- Les métadonnées du scan

**Exemple de sortie :**
```json
{
  "generatedAt": "2025-11-29T18:00:00.000Z",
  "patternDepth": 1,
  "includeDigits": true,
  "patternsUsed": ["a%.myshopify.com", "b%.myshopify.com", ...],
  "totalDomains": 45231,
  "domains": ["example1.myshopify.com", "example2.myshopify.com", ...]
}
```

**Note :** Ce module collecte uniquement les domaines. Pour vérifier qu'ils sont vraiment Shopify (DNS + HTTP + HTML), utilisez ensuite le pipeline `scanCT` existant ou créez un pipeline personnalisé qui lit le fichier JSON généré.

**Gestion du rate limiting :**
- Le module détecte automatiquement les réponses HTML (rate limiting) et réessaie avec un backoff exponentiel
- Délai par défaut entre requêtes : 1 seconde (augmentable avec `--sleepMs`)
- En cas d'erreurs répétées, augmentez `--sleepMs` (ex: `--sleepMs=2000` pour 2 secondes)
- Pour la profondeur 2 (676 patterns), prévoyez un temps d'exécution plus long

