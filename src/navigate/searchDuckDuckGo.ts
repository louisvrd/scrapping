/**
 * Module de recherche DuckDuckGo avec Playwright
 * Alternative plus tolérante que Google/Bing
 */

import { chromium, Browser } from 'playwright';
import { SearchResult } from './searchGoogle.js';

/**
 * Recherche sur DuckDuckGo et récupère les résultats organiques
 * @param query - La requête de recherche
 * @param maxResults - Nombre maximum de résultats à récupérer
 * @returns Liste des résultats avec titre et URL
 */
export async function searchDuckDuckGo(
  query: string,
  maxResults: number = 20
): Promise<SearchResult[]> {
  console.log(`🔍 Recherche DuckDuckGo: "${query}" (max ${maxResults} résultats)`);

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
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
      ],
    });

    const context = await browser.newContext({
      userAgent:
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      viewport: { width: 1920, height: 1080 },
      locale: 'fr-FR',
      timezoneId: 'Europe/Paris',
      permissions: [],
    });

    const page = await context.newPage();
    
    // Masquer les propriétés d'automation
    await page.addInitScript(() => {
      // @ts-ignore - Ces objets existent dans le contexte du navigateur
      // Masquer webdriver
      Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
      });
      
      // Masquer chrome
      // @ts-ignore
      (window as any).chrome = {
        runtime: {},
      };
      
      // Permissions
      // @ts-ignore
      const originalQuery = (window.navigator as any).permissions.query;
      // @ts-ignore
      (window.navigator as any).permissions.query = (parameters: any) =>
        parameters.name === 'notifications'
          // @ts-ignore
          ? Promise.resolve({ state: Notification.permission } as PermissionStatus)
          : originalQuery(parameters);
      
      // Plugins
      // @ts-ignore
      Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
      });
      
      // Languages
      // @ts-ignore
      Object.defineProperty(navigator, 'languages', {
        get: () => ['fr-FR', 'fr', 'en-US', 'en'],
      });
    });

    // Aller sur DuckDuckGo
    await page.goto('https://html.duckduckgo.com/html/', {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    await page.waitForTimeout(1000 + Math.random() * 1000);

    // Remplir le champ de recherche
    const searchBox = page.locator('input[name="q"]').first();
    await searchBox.waitFor({ timeout: 5000 });
    
    // Taper avec délais aléatoires
    await searchBox.fill('');
    await page.waitForTimeout(200);
    await searchBox.type(query, { delay: 50 + Math.random() * 50 });
    await page.waitForTimeout(300);
    
    // Soumettre
    await searchBox.press('Enter');

    // Attendre les résultats
    await page.waitForSelector('div.result, div.web-result', { timeout: 15000 });
    await page.waitForTimeout(2000 + Math.random() * 1000);

    // Extraire les résultats
    const organicResults = page.locator('div.result, div.web-result');

    const count = await organicResults.count();
    console.log(`  → ${count} résultats trouvés sur la page`);

    for (let i = 0; i < Math.min(count, maxResults); i++) {
      try {
        const result = organicResults.nth(i);
        const link = result.locator('a.result__a').first();
        const url = await link.getAttribute('href');
        const title = await link.textContent();

        if (!url || !url.startsWith('http')) continue;

        results.push({
          title: (title || url).trim(),
          url: url.trim(),
        });
      } catch (e) {
        continue;
      }
    }

    console.log(`✓ ${results.length} URLs organiques extraites`);
  } catch (error) {
    console.error(`✗ Erreur lors de la recherche DuckDuckGo:`, error);
    throw error;
  } finally {
    if (browser) {
      await browser.close();
    }
  }

  return results;
}

