/**
 * Pipeline de scan massif pour trouver le maximum d'URLs Shopify
 * Utilise des requêtes génériques et des techniques de collecte massives
 */

import { SearchResult } from '../navigate/searchGoogle.js';
import { getShopifyDomainsFromCT } from '../sources/certificateTransparency.js';
import { getShopifyUrlsFromGitHub } from '../sources/githubSearch.js';
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
 * Sources de données pour trouver des URLs Shopify
 * Utilise des APIs publiques au lieu des moteurs de recherche qui bloquent
 */

/**
 * Scanne massivement pour trouver un maximum de sites Shopify
 * @param options - Options de scan
 * @returns Résultats du scan
 */
export async function scanMassive(options?: {
  maxResultsPerQuery?: number;
  timeout?: number;
  useGenericQueries?: boolean;
  useShopifyQueries?: boolean;
}): Promise<ScanOutput> {
  const maxResultsPerQuery = options?.maxResultsPerQuery || 50;
  const timeout = options?.timeout || 10000;
  const useGenericQueries = options?.useGenericQueries !== false;
  const useShopifyQueries = options?.useShopifyQueries !== false;

  console.log(`\n${'='.repeat(60)}`);
  console.log(`🔎 SCAN MASSIF SHOPIFY`);
  console.log(`${'='.repeat(60)}\n`);
  console.log(`📋 Utilisation de sources publiques (pas de moteurs de recherche)\n`);

  // Collecter toutes les URLs uniques depuis différentes sources
  const allUrls = new Set<string>();
  const urlToTitle = new Map<string, string>();

  // Source 1: Certificate Transparency (très fiable, milliers d'URLs)
  console.log(`[1/2] Certificate Transparency Logs (crt.sh)`);
  try {
    const ctResults = await getShopifyDomainsFromCT(maxResultsPerQuery * 10); // Plus de résultats depuis CT
    console.log(`  ✓ ${ctResults.length} URLs collectées depuis CT\n`);
    
    for (const result of ctResults) {
      allUrls.add(result.url);
      urlToTitle.set(result.url, result.title);
    }
  } catch (error: any) {
    console.error(`  ✗ Erreur CT: ${error.message}\n`);
  }

  // Source 2: GitHub (si token disponible)
  if (useGenericQueries) {
    console.log(`[2/2] GitHub (repositories publics)`);
    try {
      const githubResults = await getShopifyUrlsFromGitHub(maxResultsPerQuery);
      console.log(`  ✓ ${githubResults.length} URLs collectées depuis GitHub\n`);
      
      for (const result of githubResults) {
        allUrls.add(result.url);
        if (!urlToTitle.has(result.url)) {
          urlToTitle.set(result.url, result.title);
        }
      }
    } catch (error: any) {
      console.error(`  ✗ Erreur GitHub: ${error.message}\n`);
    }
  }

  console.log(`\n📊 Total: ${allUrls.size} URLs uniques collectées\n`);
  console.log(`🔍 Analyse des sites...\n`);

  // Analyser chaque URL
  const results: ScanResult[] = [];
  const shopifyUrls: string[] = [];
  const urlsArray = Array.from(allUrls);

  for (let i = 0; i < urlsArray.length; i++) {
    const url = urlsArray[i];
    const title = urlToTitle.get(url) || url;

    console.log(`[${i + 1}/${urlsArray.length}] ${url}`);

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
        console.log(`  ✗ DNS échoué\n`);
        continue;
      }

      // Fetch HTML
      const html = await fetchHtml(url, timeout);
      result.htmlFetched = html !== null;

      if (!html) {
        result.error = 'Impossible de récupérer le HTML';
        results.push(result);
        console.log(`  ✗ HTML non récupéré\n`);
        continue;
      }

      // Détection Shopify
      result.isShopify = isShopify(html);
      result.confidence = getShopifyConfidence(html);

      if (result.isShopify) {
        shopifyUrls.push(url);
        console.log(`  🎯 SHOPIFY! (confiance: ${(result.confidence! * 100).toFixed(0)}%)\n`);
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
  console.log(`📊 RÉSUMÉ FINAL`);
  console.log(`${'='.repeat(60)}`);
  console.log(`URLs collectées: ${allUrls.size}`);
  console.log(`URLs analysées: ${results.length}`);
  console.log(`DNS OK: ${results.filter((r) => r.dnsOk).length}`);
  console.log(`HTML récupéré: ${results.filter((r) => r.htmlFetched).length}`);
  console.log(`🎯 Sites Shopify détectés: ${shopifyUrls.length}`);
  console.log(`${'='.repeat(60)}\n`);

  return {
    query: 'SCAN MASSIF',
    scannedCount: results.length,
    results,
    shopifyUrls,
    shopifyCount: shopifyUrls.length,
  };
}

