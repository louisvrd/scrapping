/**
 * Pipeline principal de scan
 * Orchestre la recherche, la vérification DNS, le fetch HTML et la détection Shopify
 */

import { searchGoogle, SearchResult } from '../navigate/searchGoogle.js';
import { searchBing } from '../navigate/searchBing.js';
import { searchDuckDuckGo } from '../navigate/searchDuckDuckGo.js';
import { searchWithAPI } from '../navigate/searchWithAPI.js';
import { dnsCheck } from '../network/dnsCheck.js';
import { fetchHtml } from '../network/fetchHtml.js';
import { isShopify, getShopifyConfidence } from '../detect/isShopify.js';
import { URL } from 'url';

export interface ScanResult {
  title: string;
  url: string;
  dnsOk: boolean;
  htmlFetched: boolean;
  isShopify: boolean;
  confidence?: number;
  error?: string;
}

export interface ScanOutput {
  query: string;
  scannedCount: number;
  results: ScanResult[];
  shopifyUrls: string[];
  shopifyCount: number;
}

/**
 * Scanne une niche/recherche pour trouver des sites Shopify
 * @param query - La requête de recherche
 * @param options - Options de scan (maxResults, timeout)
 * @returns Résultats du scan
 */
export async function scanNiche(
  query: string,
  options?: {
    maxResults?: number;
    timeout?: number;
  }
): Promise<ScanOutput> {
  const maxResults = options?.maxResults || 20;
  const timeout = options?.timeout || 10000;

  console.log(`\n${'='.repeat(60)}`);
  console.log(`🔎 SCAN SHOPIFY: "${query}"`);
  console.log(`${'='.repeat(60)}\n`);

  // Étape 1: Recherche (essayer plusieurs moteurs en cascade)
  let searchResults: SearchResult[] = [];
  let searchEngine = 'Aucun';
  
  // Stratégie: Essayer Google -> DuckDuckGo -> Bing -> API
  const searchEngines = [
    { name: 'Google', fn: searchGoogle },
    { name: 'DuckDuckGo', fn: searchDuckDuckGo },
    { name: 'Bing', fn: searchBing },
  ];
  
  // Essayer chaque moteur jusqu'à ce qu'un fonctionne
  for (const engine of searchEngines) {
    try {
      console.log(`🔄 Tentative avec ${engine.name}...\n`);
      searchResults = await engine.fn(query, maxResults);
      searchEngine = engine.name;
      break;
    } catch (error: any) {
      console.warn(`⚠ ${engine.name} a échoué: ${error.message}`);
      if (engine.name !== searchEngines[searchEngines.length - 1].name) {
        console.log(`🔄 Passage au moteur suivant...\n`);
      }
    }
  }
  
  // Si tous les moteurs ont échoué, essayer l'API si disponible
  if (searchResults.length === 0 && process.env.SERP_API_KEY) {
    try {
      console.log('🔄 Tentative avec API tierce...\n');
      searchResults = await searchWithAPI(query, maxResults);
      searchEngine = 'API';
    } catch (apiError: any) {
      console.warn(`⚠ API a échoué: ${apiError.message}`);
    }
  }
  
  if (searchResults.length === 0) {
    console.error('✗ Tous les moteurs de recherche ont échoué');
    console.error('  → Options:');
    console.error('    1. Attendre quelques minutes et réessayer');
    console.error('    2. Configurer SERP_API_KEY pour utiliser une API tierce');
    console.error('    3. Utiliser le mode non-headless: HEADLESS=false npm run shopify-scan');
    return {
      query,
      scannedCount: 0,
      results: [],
      shopifyUrls: [],
      shopifyCount: 0,
    };
  }
  
  console.log(`✓ Recherche effectuée avec ${searchEngine}\n`);

  if (searchResults.length === 0) {
    console.log('⚠ Aucun résultat trouvé');
    return {
      query,
      scannedCount: 0,
      results: [],
      shopifyUrls: [],
      shopifyCount: 0,
    };
  }

  console.log(`\n📋 Analyse de ${searchResults.length} URLs...\n`);

  // Étape 2: Pour chaque URL, vérifier DNS, fetch HTML, détecter Shopify
  const results: ScanResult[] = [];
  const shopifyUrls: string[] = [];

  for (let i = 0; i < searchResults.length; i++) {
    const { title, url } = searchResults[i];
    console.log(`[${i + 1}/${searchResults.length}] ${url}`);

    const result: ScanResult = {
      title,
      url,
      dnsOk: false,
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
      const dnsResult = await dnsCheck(domain);
      result.dnsOk = dnsResult.ok;

      if (!dnsResult.ok) {
        result.error = `DNS: ${dnsResult.error || 'Échec'}`;
        results.push(result);
        console.log(`  ✗ DNS échoué: ${dnsResult.error || 'Domaine introuvable'}\n`);
        continue;
      }

      console.log(`  ✓ DNS OK (${dnsResult.address})`);

      // Fetch HTML
      const html = await fetchHtml(url, timeout);
      result.htmlFetched = html !== null;

      if (!html) {
        result.error = 'Impossible de récupérer le HTML';
        results.push(result);
        console.log(`  ✗ HTML non récupéré\n`);
        continue;
      }

      console.log(`  ✓ HTML récupéré (${(html.length / 1024).toFixed(1)} KB)`);

      // Détection Shopify
      result.isShopify = isShopify(html);
      result.confidence = getShopifyConfidence(html);

      if (result.isShopify) {
        shopifyUrls.push(url);
        console.log(`  🎯 SHOPIFY DÉTECTÉ! (confiance: ${(result.confidence! * 100).toFixed(0)}%)\n`);
      } else {
        console.log(`  ✗ Pas Shopify\n`);
      }
    } catch (error: any) {
      result.error = error.message || 'Erreur inconnue';
      console.log(`  ✗ Erreur: ${result.error}\n`);
    }

    results.push(result);
  }

  // Résumé
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📊 RÉSUMÉ`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Requête: "${query}"`);
  console.log(`URLs analysées: ${results.length}`);
  console.log(`DNS OK: ${results.filter((r) => r.dnsOk).length}`);
  console.log(`HTML récupéré: ${results.filter((r) => r.htmlFetched).length}`);
  console.log(`Sites Shopify détectés: ${shopifyUrls.length}`);
  console.log(`${'='.repeat(60)}\n`);

  return {
    query,
    scannedCount: results.length,
    results,
    shopifyUrls,
    shopifyCount: shopifyUrls.length,
  };
}

