/**
 * Module de recherche via API tierce (alternative si tous les moteurs bloquent)
 * Utilise des APIs comme SerpAPI, ScraperAPI, etc.
 * 
 * NOTE: Nécessite une clé API (peut être configurée via variable d'environnement)
 */

import { SearchResult } from './searchGoogle.js';

/**
 * Recherche via API tierce (exemple avec SerpAPI)
 * @param query - La requête de recherche
 * @param maxResults - Nombre maximum de résultats
 * @returns Liste des résultats
 */
export async function searchWithAPI(
  query: string,
  maxResults: number = 20
): Promise<SearchResult[]> {
  const apiKey = process.env.SERP_API_KEY;
  
  if (!apiKey) {
    throw new Error('SERP_API_KEY non configurée. Utilisez une API tierce ou un autre moteur de recherche.');
  }

  console.log(`🔍 Recherche via API: "${query}" (max ${maxResults} résultats)`);

  try {
    // Exemple avec SerpAPI (peut être adapté pour d'autres APIs)
    const response = await fetch(
      `https://serpapi.com/search.json?engine=google&q=${encodeURIComponent(query)}&api_key=${apiKey}&num=${maxResults}`
    );

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json() as { organic_results?: Array<{ title?: string; link: string }> };
    const results: SearchResult[] = [];

    // Extraire les résultats organiques
    const organicResults = data.organic_results || [];
    
    for (const result of organicResults.slice(0, maxResults)) {
      if (result.link) {
        results.push({
          title: result.title || result.link,
          url: result.link,
        });
      }
    }

    console.log(`✓ ${results.length} URLs extraites via API`);
    return results;
  } catch (error: any) {
    console.error(`✗ Erreur lors de la recherche API:`, error.message);
    throw error;
  }
}

