/**
 * Pipeline de scan Bing bulk pour découvrir massivement des boutiques Shopify
 * SOURCE PRIMAIRE RECOMMANDÉE pour la découverte de shops Shopify
 * 
 * Utilise des requêtes de recherche Bing avec l'opérateur site:myshopify.com
 * pour découvrir des boutiques Shopify de manière fiable.
 */

import { searchBing, SearchResult } from '../navigate/searchBing.js';
import { dnsLookup, resolveCname } from '../network/dnsCheck.js';
import { fetchHtml } from '../network/fetchHtml.js';
import { isShopifyHtml } from '../detect/isShopify.js';

export interface BingBulkScanOptions {
  queries: string[]; // Liste de requêtes de recherche
  maxResultsPerQuery?: number; // Nombre max de résultats par requête (défaut: 50)
  sleepMsBetweenQueries?: number; // Pause entre chaque requête (défaut: 3000ms)
  timeout?: number; // Timeout pour les requêtes HTTP (défaut: 15000ms)
  reuseBrowser?: boolean; // Réutiliser le même navigateur pour toutes les requêtes (défaut: true)
}

export interface BingBulkScanResultItem {
  query: string;
  url: string;
  title?: string;
  dnsOk: boolean;
  cnames: string[];
  htmlFetched: boolean;
  isShopify: boolean;
  confidence?: number;
  error?: string;
}

export interface BingBulkScanResult {
  queries: string[];
  totalUrls: number;
  shopifyUrls: string[];
  shopifyCount: number;
  results: BingBulkScanResultItem[];
  generatedAt: string;
}

/**
 * Scanne massivement des boutiques Shopify via Bing avec une liste de requêtes
 */
export async function scanBingBulk(
  options: BingBulkScanOptions
): Promise<BingBulkScanResult> {
  const {
    queries,
    maxResultsPerQuery = 50,
    sleepMsBetweenQueries = 3000,
    timeout = 15000,
    reuseBrowser = true,
  } = options;

  console.log(`\n${'='.repeat(60)}`);
  console.log(`🔍 SCAN BING BULK - DÉCOUVERTE MASSIVE SHOPIFY`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Requêtes: ${queries.length}`);
  console.log(`Max résultats par requête: ${maxResultsPerQuery}`);
  console.log(`Pause entre requêtes: ${sleepMsBetweenQueries}ms`);
  console.log(`${'='.repeat(60)}\n`);

  // Set global pour déduplication des URLs
  const allUrls = new Set<string>();
  const urlToTitle = new Map<string, string>();
  const urlToQuery = new Map<string, string>(); // Pour savoir quelle requête a trouvé chaque URL
  const results: BingBulkScanResultItem[] = [];
  const shopifyUrls: string[] = [];

  try {

    // Traiter chaque requête
    for (let i = 0; i < queries.length; i++) {
      const query = queries[i];
      console.log(`\n[${i + 1}/${queries.length}] Requête: "${query}"`);

      try {
        // Recherche Bing
        let searchResults: SearchResult[] = [];
        
        // Utiliser searchBing (crée son propre navigateur à chaque fois)
        // Note: On pourrait optimiser en réutilisant le navigateur, mais searchBing
        // gère déjà bien la création/fermeture du navigateur
        searchResults = await searchBing(query, maxResultsPerQuery);

        console.log(`  → ${searchResults.length} résultats trouvés`);

        // Ajouter les URLs au Set global (déduplication)
        for (const result of searchResults) {
          if (!allUrls.has(result.url)) {
            allUrls.add(result.url);
            urlToTitle.set(result.url, result.title);
            urlToQuery.set(result.url, query);
          }
        }

        // Pause entre requêtes (sauf pour la dernière)
        if (i < queries.length - 1 && sleepMsBetweenQueries > 0) {
          const randomFactor = 0.8 + Math.random() * 0.4; // ±20% randomisation
          const actualDelay = Math.round(sleepMsBetweenQueries * randomFactor);
          console.log(`  ⏳ Pause de ${Math.round(actualDelay / 1000)}s...`);
          await new Promise((resolve) => setTimeout(resolve, actualDelay));
        }
      } catch (error: any) {
        console.error(`  ✗ Erreur pour la requête "${query}": ${error.message || error}`);
        // Continuer avec la requête suivante
        continue;
      }
    }

    // Note: searchBing gère déjà la fermeture du navigateur

    // Analyser toutes les URLs collectées
    console.log(`\n${'='.repeat(60)}`);
    console.log(`📊 Analyse des ${allUrls.size} URLs collectées...`);
    console.log(`${'='.repeat(60)}\n`);

    const urlsArray = Array.from(allUrls);
    for (let i = 0; i < urlsArray.length; i++) {
      const url = urlsArray[i];
      const title = urlToTitle.get(url) || url;

      console.log(`[${i + 1}/${urlsArray.length}] ${url}`);

      const result: BingBulkScanResultItem = {
        query: urlToQuery.get(url) || queries[0],
        url,
        title,
        dnsOk: false,
        cnames: [],
        htmlFetched: false,
        isShopify: false,
      };

      try {
        // Extraire le domaine
        let domain: string;
        try {
          const urlObj = new URL(url);
          domain = urlObj.hostname;
        } catch (e) {
          result.error = 'URL invalide';
          results.push(result);
          console.log(`  ✗ URL invalide\n`);
          continue;
        }

        // Vérification DNS
        const dnsResult = await dnsLookup(domain);
        result.dnsOk = dnsResult.ok || false;

        if (!dnsResult.ok) {
          result.error = `DNS: ${dnsResult.error || 'Échec'}`;
          results.push(result);
          console.log(`  ✗ DNS échoué\n`);
          continue;
        }

        // Résolution CNAME
        const cnameResult = await resolveCname(domain);
        result.cnames = cnameResult.cnames || [];

        // Fetch HTML
        const html = await fetchHtml(url, { timeoutMs: timeout });

        if (!html) {
          result.error = 'HTML non récupéré';
          results.push(result);
          console.log(`  ✗ HTML non récupéré\n`);
          continue;
        }

        result.htmlFetched = true;

        // Vérifier que le HTML n'est pas trop court
        if (html.length < 100) {
          result.error = 'HTML trop court ou invalide';
          results.push(result);
          console.log(`  ✗ HTML trop court\n`);
          continue;
        }

        // Détection Shopify
        result.isShopify = isShopifyHtml(html);

        if (result.isShopify) {
          shopifyUrls.push(url);
          console.log(`  🎯 SHOPIFY DÉTECTÉ!\n`);
        } else {
          console.log(`  ✗ Pas Shopify\n`);
        }
      } catch (error: any) {
        result.error = error.message || 'Erreur inconnue';
        console.log(`  ✗ Erreur: ${result.error}\n`);
      }

      results.push(result);

      // Petit délai entre les analyses
      if (i < urlsArray.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }

    // Résumé
    console.log(`\n${'='.repeat(60)}`);
    console.log(`📊 RÉSUMÉ SCAN BING BULK`);
    console.log(`${'='.repeat(60)}`);
    console.log(`Requêtes traitées: ${queries.length}`);
    console.log(`URLs collectées: ${allUrls.size}`);
    console.log(`URLs analysées: ${results.length}`);
    console.log(`DNS OK: ${results.filter((r) => r.dnsOk).length}`);
    console.log(`HTML récupéré: ${results.filter((r) => r.htmlFetched).length}`);
    console.log(`🎯 Sites Shopify détectés: ${shopifyUrls.length}`);
    console.log(`${'='.repeat(60)}\n`);

    return {
      queries,
      totalUrls: allUrls.size,
      shopifyUrls,
      shopifyCount: shopifyUrls.length,
      results,
      generatedAt: new Date().toISOString(),
    };
  } catch (error: any) {
    throw error;
  }
}

