# Authentification GitHub

Pour utiliser le scraper GitHub et augmenter les limites de rate, vous devez créer un token d'authentification.

## 📝 Créer un token GitHub

1. **Aller sur GitHub Settings** :
   - Connectez-vous à GitHub
   - Allez sur : https://github.com/settings/tokens
   - Ou : Settings → Developer settings → Personal access tokens → Tokens (classic)

2. **Créer un nouveau token** :
   - Cliquez sur "Generate new token" → "Generate new token (classic)"
   - Donnez un nom au token (ex: "Shopify Scraper")
   - Sélectionnez les permissions :
     - ✅ `public_repo` (pour accéder aux repositories publics)
     - ✅ `read:packages` (optionnel)
   - Cliquez sur "Generate token"

3. **Copier le token** :
   - ⚠️ **IMPORTANT** : Copiez le token immédiatement, vous ne pourrez plus le voir après !
   - Le token ressemble à : `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## 🔧 Configurer le token dans le projet

1. **Ouvrir le fichier `.env`** :
   ```bash
   # Éditez .env dans votre éditeur
   ```

2. **Ajouter le token** :
   ```env
   GITHUB_TOKEN=ghp_votre_token_ici
   ```

3. **Sauvegarder le fichier**

## 📊 Limites avec et sans authentification

- **Sans token** : 60 requêtes/heure (très limité)
- **Avec token** : 5000 requêtes/heure (beaucoup plus)

## ✅ Vérification

Après avoir ajouté le token, relancez le script :
```bash
python main.py
```

Vous devriez voir dans les logs :
```
Authentification GitHub activée avec token
```

Au lieu de :
```
Aucun token GitHub - limites de rate réduites (60 req/h)
```

## 🔒 Sécurité

- ⚠️ **Ne partagez JAMAIS votre token GitHub**
- ⚠️ **Ne commitez JAMAIS le fichier `.env`** (il est déjà dans `.gitignore`)
- ⚠️ Si votre token est compromis, révoquez-le immédiatement sur GitHub



