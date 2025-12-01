/**
 * Pipeline de scan basé sur Certificate Transparency
 * ⚠️ EXPÉRIMENTAL / SOURCE SECONDAIRE ⚠️
 * 
 * NOTE IMPORTANTE: Les sous-domaines individuels "xxx.myshopify.com" ne sont PAS
 * présents dans les CT logs de façon exploitable. CT n'est PAS une bonne source
 * pour énumérer les boutiques Shopify hébergées sur myshopify.com.
 * 
 * Ce pipeline est conservé à des fins expérimentales mais ne doit pas être utilisé
 * comme source primaire pour la découverte massive de shops Shopify.
 * 
 * Utilisez plutôt le pipeline Bing bulk (shopify-scan-bing-bulk) qui est plus fiable.
 */

import { fetchDomainsFromCT } from '../ct/ctScanner.js';
import { dnsLookup, resolveCname } from '../network/dnsCheck.js';
import { fetchHtml } from '../network/fetchHtml.js';
import { isShopifyHtml } from '../detect/isShopify.js';

export interface CtScanOptions {
  pattern: string; // ex: "%.myshopify.com"
  maxDomains?: number; // limite le nombre total de domaines à traiter
  concurrency?: number; // limite le nombre de requêtes parallèles
  timeout?: number; // timeout pour les requêtes HTTP
}

export interface CtScanResultItem {
  domain: string;
  url: string; // ex: "https://domain"
  dnsOk: boolean;
  cnames: string[];
  htmlFetched: boolean;
  isShopify: boolean;
  confidence?: number;
  error?: string;
}

export interface CtScanResult {
  pattern: string;
  totalDomainsFetched: number;
  scannedCount: number;
  shopifyCount: number;
  results: CtScanResultItem[];
  shopifyUrls: string[];
}

/**
 * Pool de concurrence simple
 */
class ConcurrencyPool {
  private running = 0;
  private queue: Array<() => Promise<void>> = [];

  constructor(private maxConcurrency: number) {}

  async add<T>(fn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        this.running++;
        try {
          const result = await fn();
          resolve(result);
        } catch (error) {
          reject(error);
        } finally {
          this.running--;
          this.processQueue();
        }
      });
      this.processQueue();
    });
  }

  private processQueue() {
    while (this.running < this.maxConcurrency && this.queue.length > 0) {
      const task = this.queue.shift();
      if (task) {
        task();
      }
    }
  }

  async waitAll(): Promise<void> {
    while (this.running > 0 || this.queue.length > 0) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
}

/**
 * Scanne des domaines depuis Certificate Transparency
 * @param options - Options de scan
 * @returns Résultats du scan
 */
export async function scanCT(options: CtScanOptions): Promise<CtScanResult> {
  const {
    pattern,
    maxDomains = 10000,
    concurrency = 10,
    timeout = 15000, // Augmenté à 15s pour améliorer le taux de récupération HTML
  } = options;

  console.log(`\n${'='.repeat(60)}`);
  console.log(`🔎 SCAN CERTIFICATE TRANSPARENCY`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Pattern: ${pattern}`);
  console.log(`Max domaines: ${maxDomains}`);
  console.log(`Concurrence: ${concurrency}`);
  console.log(`${'='.repeat(60)}\n`);

  // Étape 1: Récupérer les domaines depuis CT
  console.log(`📋 Étape 1: Récupération des domaines depuis CT...\n`);
  let domains: string[] = [];

  try {
    domains = await fetchDomainsFromCT(pattern, {
      limit: maxDomains,
      timeout: 60000,
    });
  } catch (error: any) {
    console.error(`✗ Erreur lors de la récupération CT:`, error.message);
    return {
      pattern,
      totalDomainsFetched: 0,
      scannedCount: 0,
      shopifyCount: 0,
      results: [],
      shopifyUrls: [],
    };
  }

  if (domains.length === 0) {
    console.log(`⚠ Aucun domaine trouvé`);
    return {
      pattern,
      totalDomainsFetched: 0,
      scannedCount: 0,
      shopifyCount: 0,
      results: [],
      shopifyUrls: [],
    };
  }

  console.log(`✓ ${domains.length} domaines récupérés\n`);
  console.log(`📋 Étape 2: Analyse des domaines (DNS → HTTP → Shopify)...\n`);

  // Étape 2: Analyser chaque domaine
  const results: CtScanResultItem[] = [];
  const shopifyUrls: string[] = [];
  const pool = new ConcurrencyPool(concurrency);
  let processed = 0;

  // Fonction pour traiter un domaine
  const processDomain = async (domain: string): Promise<void> => {
    const result: CtScanResultItem = {
      domain,
      url: `https://${domain}`,
      dnsOk: false,
      cnames: [],
      htmlFetched: false,
      isShopify: false,
    };

    try {
      // DNS Lookup
      const dnsResult = await dnsLookup(domain);
      result.dnsOk = dnsResult.ok;

      if (!dnsResult.ok) {
        result.error = `DNS: ${dnsResult.error || 'Échec'}`;
        results.push(result);
        processed++;
        if (processed % 100 === 0) {
          console.log(`  Progression: ${processed}/${domains.length} domaines analysés`);
        }
        return;
      }

      // CNAME Resolution
      const cnameResult = await resolveCname(domain);
      result.cnames = cnameResult.cnames || [];

      // Vérifier si le CNAME indique Shopify (bon indicateur)
      const hasShopifyCname = result.cnames.some((cname) =>
        cname.toLowerCase().includes('myshopify.com') ||
        cname.toLowerCase().includes('shopify')
      );

      // Fetch HTML avec retry (2 tentatives)
      let html: string | null = null;
      let fetchAttempts = 0;
      const maxFetchAttempts = 2;
      let lastFetchError: string | undefined;
      
      while (!html && fetchAttempts < maxFetchAttempts) {
        fetchAttempts++;
        html = await fetchHtml(result.url, { timeoutMs: timeout });
        if (!html && fetchAttempts < maxFetchAttempts) {
          // Attendre un peu avant de réessayer
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
      
      result.htmlFetched = html !== null;
      
      // Enregistrer l'erreur si HTML non récupéré après tous les essais
      if (!html && !result.error) {
        result.error = `HTML non récupéré après ${maxFetchAttempts} tentative(s)`;
      }

      // EXIGER HTML pour marquer comme Shopify (pas de fallback CNAME)
      if (!html) {
        result.error = 'HTML non récupéré';
        result.isShopify = false;
        results.push(result);
        processed++;
        if (processed % 100 === 0) {
          console.log(`  Progression: ${processed}/${domains.length} domaines analysés`);
        }
        return;
      }

      // Vérifier que le HTML n'est pas vide ou trop court (peut être une erreur)
      if (html.length < 100) {
        result.error = 'HTML trop court ou invalide';
        result.isShopify = false;
        results.push(result);
        processed++;
        if (processed % 100 === 0) {
          console.log(`  Progression: ${processed}/${domains.length} domaines analysés`);
        }
        return;
      }

      // Détection Shopify (STRICTE : exige HTML + vérification)
      result.isShopify = isShopifyHtml(html);

      // Vérification supplémentaire : si CNAME indique Shopify, c'est un bonus mais HTML est obligatoire
      // On ne marque comme Shopify QUE si HTML confirme (pas de fallback CNAME seul)
      if (result.isShopify) {
        shopifyUrls.push(result.url);
      }
    } catch (error: any) {
      result.error = error.message || 'Erreur inconnue';
    }

    results.push(result);
    processed++;

    // Log de progression
    if (processed % 100 === 0 || processed === domains.length) {
      const shopifyFound = results.filter((r) => r.isShopify).length;
      console.log(
        `  Progression: ${processed}/${domains.length} | DNS OK: ${results.filter((r) => r.dnsOk).length} | HTML: ${results.filter((r) => r.htmlFetched).length} | Shopify: ${shopifyFound}`
      );
    }
  };

  // Traiter tous les domaines avec le pool de concurrence
  const promises = domains.map((domain) => pool.add(() => processDomain(domain)));
  await Promise.all(promises);
  await pool.waitAll();

  // Résumé
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📊 RÉSUMÉ`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Pattern: ${pattern}`);
  console.log(`Domaines récupérés: ${domains.length}`);
  console.log(`Domaines analysés: ${results.length}`);
  console.log(`DNS OK: ${results.filter((r) => r.dnsOk).length}`);
  console.log(`HTML récupéré: ${results.filter((r) => r.htmlFetched).length}`);
  console.log(`🎯 Sites Shopify détectés: ${shopifyUrls.length}`);
  console.log(`${'='.repeat(60)}\n`);

  return {
    pattern,
    totalDomainsFetched: domains.length,
    scannedCount: results.length,
    shopifyCount: shopifyUrls.length,
    results,
    shopifyUrls,
  };
}

