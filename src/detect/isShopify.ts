/**
 * Module de détection Shopify
 * Analyse le HTML pour déterminer si un site utilise Shopify
 */

/**
 * Détecte si un site utilise Shopify en analysant le HTML
 * @param html - Le contenu HTML de la page
 * @returns true si le site est détecté comme Shopify, false sinon
 */
export function isShopify(html: string): boolean {
  return isShopifyHtml(html);
}

/**
 * Détecte si un site utilise Shopify en analysant le HTML
 * Alias pour isShopify (nom plus explicite)
 * @param html - Le contenu HTML de la page
 * @returns true si le site est détecté comme Shopify, false sinon
 */
export function isShopifyHtml(html: string): boolean {
  if (!html || html.length === 0) {
    return false;
  }

  const htmlLower = html.toLowerCase();

  // Patterns de HAUTE confiance (un seul suffit, très fiables)
  const highConfidencePatterns = [
    /cdn\.shopify\.com/i,           // CDN Shopify (très fiable)
    /shopifycdn\.com/i,              // CDN alternatif
    /window\.shopify/i,              // Variable JavaScript globale Shopify
    /shopify\.theme/i,               // Objet theme Shopify
    /shopify\.settings/i,            // Objet settings Shopify
    /shopify\.analytics/i,           // Analytics Shopify
    /Shopify\.checkout/i,            // Checkout Shopify
  ];

  // Vérifier d'abord les patterns de haute confiance
  for (const pattern of highConfidencePatterns) {
    if (pattern.test(htmlLower)) {
      return true;
    }
  }

  // Patterns de confiance MOYENNE (nécessitent au moins 2 correspondances)
  const mediumConfidencePatterns = [
    /\.myshopify\.com/i,             // Domaine myshopify.com dans le HTML
    /data-shopify/i,                 // Attribut data-shopify
    /shopify-section/i,              // Classe ou attribut shopify-section
    /shopify-section-id/i,           // ID de section Shopify
    /shopify\.js/i,                  // Script Shopify principal
    /shopify\.theme\.js/i,           // Script theme Shopify
    /\/collections\//i,              // URL collections (typique Shopify)
    /\/products\//i,                 // URL products (typique Shopify)
  ];

  // Patterns de confiance FAIBLE (nécessitent au moins 3 correspondances avec d'autres)
  const lowConfidencePatterns = [
    /\/cart/i,                       // URL cart (peut être autre CMS)
    /\/checkout/i,                    // URL checkout (peut être autre CMS)
    /shopify\.com/i,                  // Mention shopify.com (trop générique seul)
  ];

  // Compter les correspondances
  let highCount = 0;
  let mediumCount = 0;
  let lowCount = 0;

  for (const pattern of highConfidencePatterns) {
    if (pattern.test(htmlLower)) {
      highCount++;
    }
  }

  for (const pattern of mediumConfidencePatterns) {
    if (pattern.test(htmlLower)) {
      mediumCount++;
    }
  }

  for (const pattern of lowConfidencePatterns) {
    if (pattern.test(htmlLower)) {
      lowCount++;
    }
  }

  // Règles de détection STRICTES :
  // - Au moins 1 pattern haute confiance OU
  // - Au moins 2 patterns moyenne confiance OU
  // - Au moins 1 moyenne + 2 faibles OU
  // - Au moins 3 faibles (avec au moins 1 mention de .myshopify.com)
  
  if (highCount >= 1) {
    return true;
  }

  if (mediumCount >= 2) {
    return true;
  }

  if (mediumCount >= 1 && lowCount >= 2) {
    return true;
  }

  // Vérifier si .myshopify.com est présent avec d'autres patterns faibles
  const hasMyshopify = /\.myshopify\.com/i.test(htmlLower);
  if (hasMyshopify && (mediumCount + lowCount) >= 3) {
    return true;
  }

  return false;
}

/**
 * Calcule un score de confiance pour la détection Shopify
 * @param html - Le contenu HTML de la page
 * @returns Score entre 0 et 1 (1 = très confiant que c'est Shopify)
 */
export function getShopifyConfidence(html: string): number {
  if (!html || html.length === 0) {
    return 0;
  }

  const htmlLower = html.toLowerCase();
  let score = 0;

  // Patterns avec poids différents
  const weightedPatterns = [
    { pattern: /cdn\.shopify\.com/i, weight: 0.4 },
    { pattern: /\.myshopify\.com/i, weight: 0.4 },
    { pattern: /window\.shopify/i, weight: 0.3 },
    { pattern: /shopify\.theme/i, weight: 0.3 },
    { pattern: /shopifycdn\.com/i, weight: 0.3 },
    { pattern: /data-shopify/i, weight: 0.2 },
    { pattern: /shopify-section/i, weight: 0.2 },
    { pattern: /\/collections\//i, weight: 0.1 },
    { pattern: /\/products\//i, weight: 0.1 },
  ];

  for (const { pattern, weight } of weightedPatterns) {
    if (pattern.test(htmlLower)) {
      score += weight;
    }
  }

  return Math.min(score, 1.0);
}

