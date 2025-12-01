/**
 * Module Certificate Transparency Scanner
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

/**
 * Options pour fetchDomainsFromCT
 */
export interface CtScannerOptions {
  limit?: number;
  timeout?: number;
}

/**
 * Récupère des domaines depuis Certificate Transparency Logs
 * @param pattern - Pattern de recherche (ex: "%.myshopify.com")
 * @param options - Options (limit, timeout)
 * @returns Tableau de domaines nettoyés et uniques
 */
export async function fetchDomainsFromCT(
  pattern: string,
  options?: CtScannerOptions
): Promise<string[]> {
  const limit = options?.limit;
  const timeout = options?.timeout || 60000;

  console.log(`🔍 CT Scan: pattern="${pattern}"${limit ? `, limit=${limit}` : ''}`);

  const domains = new Set<string>();

  try {
    // Construire l'URL de l'API crt.sh
    const encodedPattern = encodeURIComponent(pattern);
    const apiUrl = `https://crt.sh/?q=${encodedPattern}&output=json`;

    console.log(`  → Requête à crt.sh...`);

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
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json() as Array<{ name_value?: string }>;
    console.log(`  → ${data.length} certificats trouvés`);

    // Traiter les certificats
    for (const cert of data) {
      // Si limit est défini et qu'on a atteint la limite, arrêter
      if (limit && domains.size >= limit) {
        break;
      }

      const nameValue = cert.name_value || '';
      if (!nameValue) continue;

      // name_value peut contenir plusieurs domaines séparés par \n
      const domainLines = nameValue.split('\n');
      for (const domainLine of domainLines) {
        // Nettoyer le domaine
        let domain = domainLine.trim().toLowerCase();

        // Enlever les espaces
        domain = domain.replace(/\s+/g, '');

        // Enlever *. devant
        if (domain.startsWith('*.')) {
          domain = domain.substring(2);
        }

        // Enlever www. devant
        if (domain.startsWith('www.')) {
          domain = domain.substring(4);
        }

        // Valider le domaine
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

    // Convertir en tableau et appliquer la limite finale si nécessaire
    let resultArray = Array.from(domains);
    if (limit && resultArray.length > limit) {
      resultArray = resultArray.slice(0, limit);
    }

    console.log(`✓ ${resultArray.length} domaines uniques extraits`);
    return resultArray;
  } catch (error: any) {
    if (error.name === 'AbortError') {
      console.error(`✗ Timeout lors de la requête CT`);
    } else {
      console.error(`✗ Erreur lors de la collecte CT:`, error.message);
    }
    // Retourner les domaines collectés jusqu'à présent même en cas d'erreur
    return Array.from(domains);
  }
}

