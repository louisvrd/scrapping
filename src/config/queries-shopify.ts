/**
 * Configuration des requêtes de recherche pour découvrir des boutiques Shopify
 * Utilisé par le pipeline Bing bulk
 */

export interface ShopifyQuery {
  query: string; // Requête de recherche (ex: 'site:myshopify.com "bracelets"')
  description?: string; // Description optionnelle de la niche
}

/**
 * Liste de requêtes par niches pour découvrir des boutiques Shopify
 * Format: site:myshopify.com + mot-clé ou phrase
 */
export const SHOPIFY_QUERIES: ShopifyQuery[] = [
  // Mode de vie & Accessoires
  { query: 'site:myshopify.com "bracelets"', description: 'Bracelets' },
  { query: 'site:myshopify.com "yoga"', description: 'Yoga' },
  { query: 'site:myshopify.com "bijoux"', description: 'Bijoux' },
  { query: 'site:myshopify.com "accessoires"', description: 'Accessoires' },
  
  // Mode & Vêtements
  { query: 'site:myshopify.com "vêtements"', description: 'Vêtements' },
  { query: 'site:myshopify.com "mode"', description: 'Mode' },
  { query: 'site:myshopify.com "chaussures"', description: 'Chaussures' },
  
  // Beauté & Soins
  { query: 'site:myshopify.com "cosmétiques"', description: 'Cosmétiques' },
  { query: 'site:myshopify.com "soins"', description: 'Soins' },
  { query: 'site:myshopify.com "parfum"', description: 'Parfum' },
  
  // Maison & Décoration
  { query: 'site:myshopify.com "décoration"', description: 'Décoration' },
  { query: 'site:myshopify.com "maison"', description: 'Maison' },
  { query: 'site:myshopify.com "meubles"', description: 'Meubles' },
  
  // Électronique & Tech
  { query: 'site:myshopify.com "électronique"', description: 'Électronique' },
  { query: 'site:myshopify.com "gadgets"', description: 'Gadgets' },
  
  // Alimentation & Boissons
  { query: 'site:myshopify.com "alimentation"', description: 'Alimentation' },
  { query: 'site:myshopify.com "bio"', description: 'Bio' },
  
  // Sport & Fitness
  { query: 'site:myshopify.com "sport"', description: 'Sport' },
  { query: 'site:myshopify.com "fitness"', description: 'Fitness' },
  
  // Enfants & Bébés
  { query: 'site:myshopify.com "enfants"', description: 'Enfants' },
  { query: 'site:myshopify.com "bébé"', description: 'Bébé' },
  
  // Artisanat & Création
  { query: 'site:myshopify.com "artisanat"', description: 'Artisanat' },
  { query: 'site:myshopify.com "création"', description: 'Création' },
  
  // Livres & Médias
  { query: 'site:myshopify.com "livres"', description: 'Livres' },
  
  // Requêtes génériques
  { query: 'site:myshopify.com "boutique"', description: 'Boutique générique' },
  { query: 'site:myshopify.com "shop"', description: 'Shop générique' },
  { query: 'site:myshopify.com "store"', description: 'Store générique' },
];

/**
 * Requêtes en anglais (pour plus de résultats)
 */
export const SHOPIFY_QUERIES_EN: ShopifyQuery[] = [
  { query: 'site:myshopify.com "jewelry"', description: 'Jewelry' },
  { query: 'site:myshopify.com "clothing"', description: 'Clothing' },
  { query: 'site:myshopify.com "accessories"', description: 'Accessories' },
  { query: 'site:myshopify.com "home decor"', description: 'Home decor' },
  { query: 'site:myshopify.com "beauty"', description: 'Beauty' },
  { query: 'site:myshopify.com "fitness"', description: 'Fitness' },
  { query: 'site:myshopify.com "yoga"', description: 'Yoga' },
  { query: 'site:myshopify.com "organic"', description: 'Organic' },
  { query: 'site:myshopify.com "handmade"', description: 'Handmade' },
  { query: 'site:myshopify.com "artisan"', description: 'Artisan' },
];

/**
 * Toutes les requêtes combinées
 */
export const ALL_SHOPIFY_QUERIES: ShopifyQuery[] = [
  ...SHOPIFY_QUERIES,
  ...SHOPIFY_QUERIES_EN,
];


