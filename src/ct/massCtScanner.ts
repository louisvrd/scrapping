/**
 * Module Mass Certificate Transparency Scanner
 * ⚠️ EXPÉRIMENTAL / SOURCE SECONDAIRE ⚠️
 * 
 * NOTE IMPORTANTE: Les sous-domaines individuels "xxx.myshopify.com" ne sont PAS
 * présents dans les CT logs de façon exploitable. CT n'est PAS une bonne source
 * pour énumérer les boutiques Shopify hébergées sur myshopify.com.
 * 
 * Ce module est conservé à des fins expérimentales mais ne doit pas être utilisé
 * comme source primaire pour la découverte massive de shops Shopify.
 * 
 * Utilisez plutôt le pipeline Bing bulk (shopify-scan-bing-bulk) qui est plus fiable.
 */

import { fetchDomainsFromCT, CtScannerOptions } from './ctScanner.js';

/**
 * Options pour le scan CT massif
 */
export interface MassCtOptions {
  patternDepth?: 1 | 2; // DEPRECATED: Les patterns alphabétiques ne fonctionnent pas
  includeDigits?: boolean; // DEPRECATED
  limitPerPattern?: number; // nbre max de domaines à garder par requête (optionnel)
  maxTotalDomains?: number; // couper proprement si on dépasse un certain total global
  sleepMsBetweenRequests?: number; // petite pause entre requêtes crt.sh, ex: 2000ms
  timeout?: number; // timeout pour chaque requête CT
  stopAfterConsecutiveErrors?: number; // Arrêter après N erreurs consécutives (défaut: pas de limite)
  useDateRanges?: boolean; // Utiliser des requêtes avec plages de dates (défaut: true)
  useDifferentEndpoints?: boolean; // Utiliser différents endpoints (défaut: true)
  daysBack?: number; // Nombre de jours en arrière pour les requêtes par date (défaut: 365)
}

/**
 * Résultat du scan CT massif
 */
export interface MassCtResult {
  patternsUsed: string[];
  totalDomains: number;
  domains: string[]; // liste unique dédupliquée
}

/**
 * Fonction utilitaire pour sleep
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Génère la liste de caractères à utiliser pour les patterns
 */
function generateAlphabet(includeDigits: boolean): string[] {
  const alphabet = 'abcdefghijklmnopqrstuvwxyz'.split('');
  if (includeDigits) {
    return [...alphabet, ...'0123456789'.split('')];
  }
  return alphabet;
}

/**
 * Génère des requêtes avec plages de dates différentes
 * pour contourner la limite de ~5000 certificats par requête
 */
function generateDateRangeQueries(daysBack: number = 365): Array<{ pattern: string; startDate?: string; endDate?: string }> {
  const queries: Array<{ pattern: string; startDate?: string; endDate?: string }> = [];
  const pattern = '%.myshopify.com';
  
  // Requête principale (sans date)
  queries.push({ pattern });
  
  // Générer des requêtes par plages de dates (par mois)
  const now = new Date();
  const monthsBack = Math.ceil(daysBack / 30);
  
  for (let i = 0; i < monthsBack; i++) {
    const endDate = new Date(now);
    endDate.setMonth(endDate.getMonth() - i);
    
    const startDate = new Date(endDate);
    startDate.setMonth(startDate.getMonth() - 1);
    
    // Format pour crt.sh: YYYYMMDD (sans tirets)
    const startStr = startDate.toISOString().slice(0, 10).replace(/-/g, '');
    const endStr = endDate.toISOString().slice(0, 10).replace(/-/g, '');
    
    queries.push({
      pattern,
      startDate: startStr,
      endDate: endStr,
    });
  }
  
  return queries;
}

/**
 * Génère des requêtes avec différents endpoints
 */
function generateEndpointQueries(): Array<{ pattern: string; endpoint: 'q' | 'Identity' }> {
  const pattern = '%.myshopify.com';
  
  return [
    { pattern, endpoint: 'q' }, // Endpoint standard
    { pattern, endpoint: 'Identity' }, // Endpoint alternatif
  ];
}

/**
 * Récupère des domaines depuis CT pour un pattern donné
 * Réutilise la fonction standard qui fonctionne sans rate limiting
 */
async function fetchDomainsFromCTSilent(
  pattern: string,
  options?: CtScannerOptions
): Promise<string[]> {
  // Réutiliser directement fetchDomainsFromCT qui fonctionne bien
  // On supprime juste les logs pour ne pas spammer
  const originalLog = console.log;
  const originalError = console.error;
  
  // Désactiver temporairement les logs
  console.log = () => {};
  console.error = () => {};
  
  try {
    const domains = await fetchDomainsFromCT(pattern, options);
    return domains;
  } finally {
    // Restaurer les logs
    console.log = originalLog;
    console.error = originalError;
  }
}

/**
 * Récupère des domaines depuis CT avec des paramètres de date
 */
async function fetchDomainsFromCTWithDate(
  pattern: string,
  startDate?: string,
  endDate?: string,
  options?: CtScannerOptions
): Promise<string[]> {
  const timeout = options?.timeout || 60000;
  const limit = options?.limit;
  
  const domains = new Set<string>();
  
  try {
    // Construire l'URL avec paramètres de date
    // crt.sh utilise notBefore et notAfter avec format YYYYMMDD
    let apiUrl = `https://crt.sh/?q=${encodeURIComponent(pattern)}&output=json`;
    
    if (startDate) {
      apiUrl += `&notBefore=${startDate}`;
    }
    if (endDate) {
      apiUrl += `&notAfter=${endDate}`;
    }
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    const response = await fetch(apiUrl, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        Accept: 'application/json',
      },
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      return [];
    }
    
    const data = await response.json() as Array<{ name_value?: string }>;
    
    // Traiter les certificats (même logique que fetchDomainsFromCT)
    for (const cert of data) {
      if (limit && domains.size >= limit) {
        break;
      }
      
      const nameValue = cert.name_value || '';
      if (!nameValue) continue;
      
      const domainLines = nameValue.split('\n');
      for (const domainLine of domainLines) {
        let domain = domainLine.trim().toLowerCase();
        domain = domain.replace(/\s+/g, '');
        if (domain.startsWith('*.')) {
          domain = domain.substring(2);
        }
        if (domain.startsWith('www.')) {
          domain = domain.substring(4);
        }
        
        if (
          domain &&
          domain.length > 0 &&
          !domain.startsWith('.') &&
          domain.includes('.') &&
          !domain.includes(' ') &&
          !domain.includes('\n') &&
          !domain.includes('\r')
        ) {
          domains.add(domain);
        }
      }
    }
    
    let resultArray = Array.from(domains);
    if (limit && resultArray.length > limit) {
      resultArray = resultArray.slice(0, limit);
    }
    
    return resultArray;
  } catch (error: any) {
    return [];
  }
}

/**
 * Récupère des domaines depuis CT avec un endpoint différent (Identity au lieu de q)
 */
async function fetchDomainsFromCTWithEndpoint(
  pattern: string,
  endpoint: 'q' | 'Identity',
  options?: CtScannerOptions
): Promise<string[]> {
  const timeout = options?.timeout || 60000;
  const limit = options?.limit;
  
  const domains = new Set<string>();
  
  try {
    // Construire l'URL avec endpoint différent
    const apiUrl = `https://crt.sh/?${endpoint}=${encodeURIComponent(pattern)}&output=json`;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    const response = await fetch(apiUrl, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        Accept: 'application/json',
      },
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      return [];
    }
    
    const data = await response.json() as Array<{ name_value?: string }>;
    
    // Traiter les certificats (même logique)
    for (const cert of data) {
      if (limit && domains.size >= limit) {
        break;
      }
      
      const nameValue = cert.name_value || '';
      if (!nameValue) continue;
      
      const domainLines = nameValue.split('\n');
      for (const domainLine of domainLines) {
        let domain = domainLine.trim().toLowerCase();
        domain = domain.replace(/\s+/g, '');
        if (domain.startsWith('*.')) {
          domain = domain.substring(2);
        }
        if (domain.startsWith('www.')) {
          domain = domain.substring(4);
        }
        
        if (
          domain &&
          domain.length > 0 &&
          !domain.startsWith('.') &&
          domain.includes('.') &&
          !domain.includes(' ') &&
          !domain.includes('\n') &&
          !domain.includes('\r')
        ) {
          domains.add(domain);
        }
      }
    }
    
    let resultArray = Array.from(domains);
    if (limit && resultArray.length > limit) {
      resultArray = resultArray.slice(0, limit);
    }
    
    return resultArray;
  } catch (error: any) {
    return [];
  }
}

/**
 * Récupère massivement des domaines depuis Certificate Transparency
 * en utilisant plusieurs patterns alphabétiques
 */
export async function massFetchDomainsFromCT(
  options?: MassCtOptions
): Promise<MassCtResult> {
  const {
    limitPerPattern,
    maxTotalDomains,
    sleepMsBetweenRequests = 2000,
    timeout = 60000,
    stopAfterConsecutiveErrors,
    useDateRanges = true,
    useDifferentEndpoints = true,
    daysBack = 365,
  } = options || {};

  console.log(`\n${'='.repeat(60)}`);
  console.log(`🔍 MASS CT SCAN (Nouvelle Approche)`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Stratégie: Requêtes avec dates + endpoints multiples`);
  console.log(`Plages de dates: ${useDateRanges ? `Oui (${daysBack} jours)` : 'Non'}`);
  console.log(`Endpoints multiples: ${useDifferentEndpoints ? 'Oui' : 'Non'}`);
  console.log(`Limite par requête: ${limitPerPattern || 'illimitée'}`);
  console.log(`Limite totale: ${maxTotalDomains || 'illimitée'}`);
  console.log(`Pause entre requêtes: ${sleepMsBetweenRequests}ms`);
  console.log(`${'='.repeat(60)}\n`);

  // Générer les requêtes selon les stratégies
  const queries: Array<{ pattern: string; startDate?: string; endDate?: string; endpoint?: 'q' | 'Identity'; description: string }> = [];
  
  // 1. Requête principale (sans date)
  queries.push({ pattern: '%.myshopify.com', description: 'Requête principale' });
  
  // 2. Requêtes avec plages de dates
  if (useDateRanges) {
    const dateQueries = generateDateRangeQueries(daysBack);
    for (const query of dateQueries.slice(1)) { // Skip la première (déjà ajoutée)
      queries.push({
        pattern: query.pattern,
        startDate: query.startDate,
        endDate: query.endDate,
        description: `Date: ${query.startDate} - ${query.endDate}`,
      });
    }
  }
  
  // 3. Requêtes avec endpoints différents
  if (useDifferentEndpoints) {
    const endpointQueries = generateEndpointQueries();
    for (const query of endpointQueries) {
      if (query.endpoint === 'Identity') {
        queries.push({
          pattern: query.pattern,
          endpoint: query.endpoint,
          description: `Endpoint: Identity`,
        });
      }
    }
  }
  
  console.log(`📋 ${queries.length} requêtes générées\n`);

  // Pause initiale modérée (le scan standard fonctionne sans pause, donc on en met une petite)
  if (sleepMsBetweenRequests > 0) {
    console.log(`⏳ Pause initiale de ${Math.round(sleepMsBetweenRequests/1000)}s avant de commencer...\n`);
    await sleep(sleepMsBetweenRequests);
  }

  // Set global pour déduplication
  const allDomains = new Set<string>();
  const patternsUsed: string[] = [];
  let queryIndex = 0;
  let consecutiveErrors = 0;
  const maxConsecutiveErrors = 5;

  // Traiter chaque requête
  for (const query of queries) {
    queryIndex++;

    // Vérifier si on a atteint la limite totale
    if (maxTotalDomains && allDomains.size >= maxTotalDomains) {
      console.log(
        `\n⚠ Arrêt anticipé: maxTotalDomains (${maxTotalDomains}) atteint`
      );
      break;
    }

    try {
      const ctOptions: CtScannerOptions = { timeout };
      if (limitPerPattern) {
        ctOptions.limit = limitPerPattern;
      }

      let domains: string[] = [];
      
      // Choisir la fonction selon le type de requête
      if (query.endpoint && query.endpoint === 'Identity') {
        domains = await fetchDomainsFromCTWithEndpoint(query.pattern, query.endpoint, ctOptions);
      } else if (query.startDate || query.endDate) {
        domains = await fetchDomainsFromCTWithDate(query.pattern, query.startDate, query.endDate, ctOptions);
      } else {
        domains = await fetchDomainsFromCTSilent(query.pattern, ctOptions);
      }

      // Réinitialiser le compteur d'erreurs en cas de succès
      if (domains.length > 0) {
        consecutiveErrors = 0;
      }

      // Ajouter les domaines au Set global (déduplication automatique)
      let newDomainsCount = 0;
      for (const domain of domains) {
        if (!allDomains.has(domain)) {
          allDomains.add(domain);
          newDomainsCount++;
        }
      }

      patternsUsed.push(query.description || query.pattern);
      const cumul = allDomains.size;
      console.log(
        `Requête ${queryIndex}/${queries.length}: ${query.description} → ${domains.length} domaines trouvés (${newDomainsCount} nouveaux, cumul: ${cumul})`
      );

      // Vérifier à nouveau la limite après ajout
      if (maxTotalDomains && allDomains.size >= maxTotalDomains) {
        console.log(
          `\n⚠ Arrêt anticipé: maxTotalDomains (${maxTotalDomains}) atteint`
        );
        break;
      }

      // Pause entre requêtes avec légère randomisation
      if (
        sleepMsBetweenRequests > 0 &&
        queryIndex < queries.length &&
        (!maxTotalDomains || allDomains.size < maxTotalDomains)
      ) {
        const randomFactor = 0.8 + Math.random() * 0.4;
        const actualDelay = Math.round(sleepMsBetweenRequests * randomFactor);
        await sleep(actualDelay);
      }
    } catch (error: any) {
      consecutiveErrors++;
      console.error(
        `✗ Erreur pour la requête ${query.description}: ${error.message || error}`
      );

      // Vérifier si on doit arrêter
      if (stopAfterConsecutiveErrors && consecutiveErrors >= stopAfterConsecutiveErrors) {
        console.log(
          `\n⚠ Arrêt automatique: ${consecutiveErrors} erreurs consécutives (limite: ${stopAfterConsecutiveErrors})`
        );
        break;
      }

      // Circuit breaker
      if (consecutiveErrors >= maxConsecutiveErrors) {
        const longPause = Math.min(sleepMsBetweenRequests * 10, 30000);
        console.log(
          `\n⚠ ${consecutiveErrors} erreurs consécutives. Pause de ${longPause}ms...`
        );
        await sleep(longPause);
        consecutiveErrors = 0;
      } else if (consecutiveErrors >= 3) {
        const moderatePause = Math.min(sleepMsBetweenRequests * 5, 15000);
        console.log(
          `⚠ ${consecutiveErrors} erreurs consécutives. Pause de ${moderatePause}ms...`
        );
        await sleep(moderatePause);
      } else {
        if (sleepMsBetweenRequests > 0) {
          await sleep(sleepMsBetweenRequests * 2);
        }
      }

      continue;
    }
  }

  // Convertir le Set en tableau trié
  const domainsArray = Array.from(allDomains).sort();

  console.log(`\n${'='.repeat(60)}`);
  console.log(`📊 RÉSUMÉ MASS CT SCAN`);
  console.log(`${'='.repeat(60)}`);
  console.log(`Patterns utilisés: ${patternsUsed.length}`);
  console.log(`Domaines uniques: ${domainsArray.length}`);
  console.log(`${'='.repeat(60)}\n`);

  return {
    patternsUsed,
    totalDomains: domainsArray.length,
    domains: domainsArray,
  };
}

