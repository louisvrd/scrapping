/**
 * Module de collecte via Certificate Transparency Logs
 * Source: crt.sh (API publique, très fiable, pas de blocage)
 * Cette source trouve des milliers d'URLs Shopify sans passer par les moteurs de recherche
 */

import { SearchResult } from '../navigate/searchGoogle.js';

/**
 * Récupère les domaines Shopify depuis Certificate Transparency Logs
 * @param maxResults - Nombre maximum de résultats (défaut: 10000)
 * @returns Liste des domaines Shopify trouvés
 */
export async function getShopifyDomainsFromCT(
  maxResults: number = 10000
): Promise<SearchResult[]> {
  console.log(`🔍 Collecte depuis Certificate Transparency (max ${maxResults} résultats)`);

  const results: SearchResult[] = [];
  const domains = new Set<string>();

  try {
    // Requête à l'API crt.sh pour trouver tous les domaines *.myshopify.com
    const apiUrl = `https://crt.sh/?q=%.myshopify.com&output=json`;

    console.log(`  → Requête à crt.sh...`);
    const response = await fetch(apiUrl, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      },
      signal: AbortSignal.timeout(60000), // 60s timeout
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json() as Array<{ name_value?: string }>;
    console.log(`  → ${data.length} certificats trouvés`);

    // Traiter les certificats
    let processed = 0;
    for (const cert of data) {
      if (processed >= maxResults) break;

      const nameValue = cert.name_value || '';
      if (!nameValue) continue;

      // name_value peut contenir plusieurs domaines séparés par \n
      const domainLines = nameValue.split('\n');
      for (const domainLine of domainLines) {
        const domain = domainLine.trim().toLowerCase();
        
        if (domain.endsWith('.myshopify.com')) {
          // Nettoyer le domaine
          let cleanDomain = domain
            .replace('*.', '')
            .replace('www.', '')
            .trim();

          // Filtrer les domaines invalides
          if (
            cleanDomain &&
            cleanDomain !== 'myshopify.com' &&
            !cleanDomain.startsWith('.')
          ) {
            // Vérifier que c'est un domaine valide (doit avoir un sous-domaine)
            const parts = cleanDomain.split('.');
            if (parts.length >= 2 && parts[0] && parts[0].length > 0) {
              const storeName = parts[0];
              
              // Filtrer les noms de stores invalides
              if (
                !['www', 'admin', 'cdn', 'login', 'api', 'app', 'mail', 'ftp', 'test'].includes(
                  storeName
                )
              ) {
                domains.add(cleanDomain);
              }
            }
          }
        }
      }
      processed++;
    }

    // Convertir en SearchResult
    for (const domain of domains) {
      results.push({
        title: domain,
        url: `https://${domain}`,
      });
    }

    console.log(`✓ ${results.length} domaines Shopify uniques trouvés`);
  } catch (error: any) {
    console.error(`✗ Erreur lors de la collecte CT:`, error.message);
    throw error;
  }

  return results;
}

