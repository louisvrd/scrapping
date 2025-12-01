/**
 * Pipeline de scan de niche avec Bing
 * Utilise Bing pour rechercher, puis analyse les résultats
 */

import { searchBing, SearchResult } from '../navigate/searchBing.js';
import { dnsLookup, resolveCname } from '../network/dnsCheck.js';
import { fetchHtml } from '../network/fetchHtml.js';
import { isShopifyHtml } from '../detect/isShopify.js';

export interface NicheScanResultItem {
  title: string;
  url: string;
  dnsOk: boolean;
  cnames: string[];
  htmlFetched: boolean;
  isShopify: boolean;
  error?: string;
}

export interface NicheScanResult {
  query: string;
  scannedCount: number;
  shopifyCount: number;
  results: NicheScanResultItem[];
  shopifyUrls: string[];
}

/**
 * Scanne une niche avec Bing
 * @param query - La requête de recherche
 * @param maxResults - Nombre maximum de résultats
 * @param concurrency - Nombre de requêtes parallèles
 * @returns Résultats du scan
 */
export async function scanNicheWithBing(
  query: string,
  maxResults: number = 50,
  concurrency: number = 5
): Promise<NicheScanResult> {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`🔎 SCAN NICHE AVEC BING: "${query}"`);
  console.log(`${'='.repeat(60)}\n`);

  // Étape 1: Recherche Bing
  let searchResults: SearchResult[] = [];
  try {
    searchResults = await searchBing(query, maxResults);
  } catch (error: any) {
    console.error(`✗ Erreur lors de la recherche Bing:`, error.message);
    return {
      query,
      scannedCount: 0,
      shopifyCount: 0,
      results: [],
      shopifyUrls: [],
    };
  }

  if (searchResults.length === 0) {
    console.log('⚠ Aucun résultat trouvé');
    return {
      query,
      scannedCount: 0,
      shopifyCount: 0,
      results: [],
      shopifyUrls: [],
    };
  }

  console.log(`✓ ${searchResults.length} URLs trouvées\n`);
  console.log(`📋 Analyse des sites...\n`);

  // Étape 2: Analyser chaque URL
  const results: NicheScanResultItem[] = [];
  const shopifyUrls: string[] = [];

  // Pool de concurrence simple
  let running = 0;
  const queue: Array<() => Promise<void>> = [];

  const processUrl = async (result: SearchResult, index: number): Promise<void> => {
    const item: NicheScanResultItem = {
      title: result.title,
      url: result.url,
      dnsOk: false,
      cnames: [],
      htmlFetched: false,
      isShopify: false,
    };

    try {
      console.log(`[${index + 1}/${searchResults.length}] ${result.url}`);

      // Extraire le domaine
      let domain: string;
      try {
        const urlObj = new URL(result.url);
        domain = urlObj.hostname;
      } catch (e) {
        item.error = 'URL invalide';
        results.push(item);
        console.log(`  ✗ URL invalide\n`);
        return;
      }

      // DNS Lookup
      const dnsResult = await dnsLookup(domain);
      item.dnsOk = dnsResult.ok;

      if (!dnsResult.ok) {
        item.error = `DNS: ${dnsResult.error || 'Échec'}`;
        results.push(item);
        console.log(`  ✗ DNS échoué\n`);
        return;
      }

      console.log(`  ✓ DNS OK (${dnsResult.address})`);

      // CNAME
      const cnameResult = await resolveCname(domain);
      item.cnames = cnameResult.cnames || [];

      // Fetch HTML
      const html = await fetchHtml(result.url, { timeoutMs: 10000 });
      item.htmlFetched = html !== null;

      if (!html) {
        item.error = 'HTML non récupéré';
        results.push(item);
        console.log(`  ✗ HTML non récupéré\n`);
        return;
      }

      console.log(`  ✓ HTML récupéré (${(html.length / 1024).toFixed(1)} KB)`);

      // Détection Shopify
      item.isShopify = isShopifyHtml(html);

      if (item.isShopify) {
        shopifyUrls.push(result.url);
        console.log(`  🎯 SHOPIFY DÉTECTÉ!\n`);
      } else {
        console.log(`  ✗ Pas Shopify\n`);
      }
    } catch (error: any) {
      item.error = error.message || 'Erreur inconnue';
      console.log(`  ✗ Erreur: ${item.error}\n`);
    }

    results.push(item);
  };

  // Traiter avec concurrence limitée
  for (let i = 0; i < searchResults.length; i++) {
    while (running >= concurrency) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    running++;
    processUrl(searchResults[i], i + 1).finally(() => {
      running--;
    });
  }

  // Attendre que tout soit terminé
  while (running > 0) {
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  // Résumé
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📊 RÉSUMÉ`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Requête: "${query}"`);
  console.log(`URLs analysées: ${results.length}`);
  console.log(`DNS OK: ${results.filter((r) => r.dnsOk).length}`);
  console.log(`HTML récupéré: ${results.filter((r) => r.htmlFetched).length}`);
  console.log(`🎯 Sites Shopify détectés: ${shopifyUrls.length}`);
  console.log(`${'='.repeat(60)}\n`);

  return {
    query,
    scannedCount: results.length,
    shopifyCount: shopifyUrls.length,
    results,
    shopifyUrls,
  };
}


