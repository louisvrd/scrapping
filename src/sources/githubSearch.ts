/**
 * Module de recherche GitHub pour trouver des URLs Shopify
 * Utilise l'API GitHub (si token disponible) ou recherche dans les repositories publics
 */

import { SearchResult } from '../navigate/searchGoogle.js';

/**
 * Recherche des URLs Shopify dans GitHub
 * @param maxResults - Nombre maximum de résultats
 * @returns Liste des URLs Shopify trouvées
 */
export async function getShopifyUrlsFromGitHub(
  maxResults: number = 100
): Promise<SearchResult[]> {
  const githubToken = process.env.GITHUB_TOKEN;
  
  if (!githubToken) {
    console.log(`⚠ GITHUB_TOKEN non configurée - skip GitHub`);
    return [];
  }

  console.log(`🔍 Recherche GitHub pour URLs Shopify (max ${maxResults} résultats)`);

  const results: SearchResult[] = [];
  const urls = new Set<string>();

  try {
    const queries = [
      'myshopify.com filename:.txt',
      'myshopify.com filename:.json',
      'myshopify.com filename:.csv',
      'myshopify.com filename:.md',
      '"myshopify.com" language:markdown',
    ];

    for (const query of queries) {
      try {
        const apiUrl = `https://api.github.com/search/code?q=${encodeURIComponent(query)}&per_page=30`;
        
        const response = await fetch(apiUrl, {
          headers: {
            Authorization: `token ${githubToken}`,
            Accept: 'application/vnd.github.v3+json',
            'User-Agent': 'Shopify-Scanner',
          },
          signal: AbortSignal.timeout(10000),
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            console.warn(`  ⚠ GitHub API error: ${response.status}`);
            break;
          }
          continue;
        }

        const data = await response.json() as { items?: Array<{ html_url?: string; url?: string; content?: string }> };
        const items = data.items || [];

        // Extraire les URLs depuis le contenu des fichiers
        for (const item of items) {
          try {
            // Récupérer le contenu du fichier
            const contentUrl = item.url || item.html_url;
            if (!contentUrl) continue;
            const contentResponse = await fetch(contentUrl, {
              headers: {
                Authorization: `token ${githubToken}`,
                Accept: 'application/vnd.github.v3.raw',
              },
              signal: AbortSignal.timeout(5000),
            });

            if (contentResponse.ok) {
              const content = await contentResponse.text();
              
              // Extraire les URLs myshopify.com
              const urlPattern = /https?:\/\/([a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.myshopify\.com[^\s]*/gi;
              const matches = content.matchAll(urlPattern);
              
              for (const match of matches) {
                const fullUrl = match[0];
                const storeName = match[1];
                
                if (storeName && !['www', 'admin', 'cdn', 'login', 'api'].includes(storeName)) {
                  urls.add(fullUrl);
                }
              }
            }
          } catch (e) {
            // Ignorer les erreurs individuelles
            continue;
          }
        }

        // Délai entre les requêtes
        await new Promise((resolve) => setTimeout(resolve, 2000));
      } catch (e) {
        // Continuer avec la prochaine requête
        continue;
      }
    }

    // Convertir en SearchResult
    for (const url of urls) {
      try {
        const urlObj = new URL(url);
        results.push({
          title: urlObj.hostname,
          url: url,
        });
      } catch (e) {
        // URL invalide, ignorer
      }
    }

    console.log(`✓ ${results.length} URLs Shopify trouvées sur GitHub`);
  } catch (error: any) {
    console.error(`✗ Erreur lors de la recherche GitHub:`, error.message);
  }

  return results;
}

