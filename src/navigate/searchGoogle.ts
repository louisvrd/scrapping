/**
 * Module de recherche Google avec Playwright
 * Récupère les URLs des résultats organiques (sans les publicités)
 */

import { chromium, Browser, Page } from 'playwright';

export interface SearchResult {
  title: string;
  url: string;
}

/**
 * Recherche sur Google et récupère les résultats organiques
 * @param query - La requête de recherche
 * @param maxResults - Nombre maximum de résultats à récupérer
 * @returns Liste des résultats avec titre et URL
 */
export async function searchGoogle(
  query: string,
  maxResults: number = 20
): Promise<SearchResult[]> {
  console.log(`🔍 Recherche Google: "${query}" (max ${maxResults} résultats)`);

  let browser: Browser | null = null;
  const results: SearchResult[] = [];

  try {
    // Lancer le navigateur Chrome (pas Chromium) pour supporter les extensions
    const headless = process.env.HEADLESS !== 'false';
    browser = await chromium.launch({
      channel: 'chrome', // Utiliser Chrome installé au lieu de Chromium (nécessaire pour les extensions)
      headless,
      args: [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
      ],
    });

    const context = await browser.newContext({
      userAgent:
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      viewport: { width: 1920, height: 1080 },
      locale: 'fr-FR',
      timezoneId: 'Europe/Paris',
    });

    // Masquer les propriétés webdriver
    const page = await context.newPage();
    await page.addInitScript(() => {
      // @ts-ignore - navigator existe dans le contexte du navigateur
      Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
      });
    });

    // Aller sur Google avec un délai aléatoire
    await page.goto('https://www.google.com', {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    // Attendre un peu pour paraître plus humain
    await page.waitForTimeout(1000 + Math.random() * 1000);

    // Vérifier si on est sur une page de captcha/sorry
    const currentUrl = page.url();
    if (currentUrl.includes('/sorry') || currentUrl.includes('captcha')) {
      throw new Error('Google a détecté le bot (captcha/sorry page). Essayez Bing ou attendez quelques minutes.');
    }

    // Accepter les cookies si nécessaire
    try {
      const acceptSelectors = [
        'button:has-text("Accept")',
        'button:has-text("J\'accepte")',
        'button:has-text("Accepter")',
        'button#L2AGLb', // Bouton accepter Google
        '[id*="accept"]',
      ];
      
      for (const selector of acceptSelectors) {
        try {
          const button = page.locator(selector).first();
          if (await button.isVisible({ timeout: 2000 })) {
            await button.click();
            await page.waitForTimeout(1000);
            break;
          }
        } catch (e) {
          // Continuer avec le prochain sélecteur
        }
      }
    } catch (e) {
      // Pas de popup de cookies, on continue
    }

    // Remplir le champ de recherche avec un délai pour paraître humain
    const searchBox = page.locator('textarea[name="q"], input[name="q"]').first();
    await searchBox.waitFor({ timeout: 5000 });
    
    // Taper caractère par caractère pour paraître plus humain
    await searchBox.fill('');
    await page.waitForTimeout(200);
    await searchBox.type(query, { delay: 50 + Math.random() * 50 });
    await page.waitForTimeout(300);
    
    // Appuyer sur Enter
    await searchBox.press('Enter');

    // Attendre que les résultats se chargent
    try {
      await page.waitForSelector('div#search, div#rso, div[data-async-context]', { 
        timeout: 15000 
      });
      
      // Vérifier à nouveau si on est sur une page de captcha
      const urlAfterSearch = page.url();
      if (urlAfterSearch.includes('/sorry') || urlAfterSearch.includes('captcha')) {
        throw new Error('Google a détecté le bot après la recherche (captcha/sorry page).');
      }
      
      await page.waitForTimeout(2000 + Math.random() * 1000); // Attendre un peu pour que tout se charge
    } catch (e: any) {
      // Vérifier si c'est un timeout ou un captcha
      const currentUrl = page.url();
      if (currentUrl.includes('/sorry') || currentUrl.includes('captcha')) {
        throw new Error('Google a détecté le bot (captcha/sorry page). Essayez Bing ou attendez quelques minutes.');
      }
      throw e;
    }

    // Extraire les résultats organiques
    // Sélecteurs pour les résultats organiques (pas les ads)
    const organicResults = page.locator(
      'div#search div.g:not([data-ved]):not(.g-blk), div#rso > div:not([data-ved]):not(.g-blk), div[data-async-context] div.g'
    );

    const count = await organicResults.count();
    console.log(`  → ${count} résultats trouvés sur la page`);

    for (let i = 0; i < Math.min(count, maxResults); i++) {
      try {
        const result = organicResults.nth(i);
        
        // Récupérer le lien - essayer plusieurs sélecteurs
        let link = result.locator('a[href^="http"]').first();
        let url = await link.getAttribute('href');
        
        // Si pas trouvé, essayer avec h3 > a
        if (!url) {
          link = result.locator('h3 a, h2 a').first();
          url = await link.getAttribute('href');
        }
        
        if (!url) continue;

        // Nettoyer l'URL (enlever les paramètres Google)
        let cleanUrl = url;
        if (url.startsWith('/url?q=')) {
          const match = url.match(/\/url\?q=([^&]+)/);
          if (match) {
            cleanUrl = decodeURIComponent(match[1]);
          }
        } else if (url.startsWith('/url?')) {
          // Autre format d'URL Google
          const match = url.match(/[?&]q=([^&]+)/);
          if (match) {
            cleanUrl = decodeURIComponent(match[1]);
          }
        }

        // Ignorer les URLs Google (images, maps, etc.)
        if (
          cleanUrl.includes('google.com') ||
          cleanUrl.includes('googleusercontent.com') ||
          !cleanUrl.startsWith('http')
        ) {
          continue;
        }

        // Récupérer le titre
        const titleElement = result.locator('h3, h2').first();
        const title = (await titleElement.textContent()) || cleanUrl;

        results.push({
          title: title.trim(),
          url: cleanUrl,
        });
      } catch (e) {
        // Ignorer les erreurs sur un résultat individuel
        continue;
      }
    }

    console.log(`✓ ${results.length} URLs organiques extraites`);
  } catch (error) {
    console.error(`✗ Erreur lors de la recherche Google:`, error);
    throw error;
  } finally {
    if (browser) {
      await browser.close();
    }
  }

  return results;
}

