/**
 * Module de recherche Bing avec Playwright
 * Alternative à Google si celui-ci bloque
 */

/**
 * Module de recherche Bing avec Playwright
 * Version robuste qui construit directement l'URL de recherche
 */

import { chromium, Browser, Page } from 'playwright';
import { SearchResult } from './searchGoogle.js';
import { config } from '../config/env.js';

// Ré-exporter SearchResult pour que d'autres modules puissent l'importer
export type { SearchResult };

/**
 * Détecte et résout automatiquement les captchas sur la page
 * Utilise une extension de navigateur installée qui résout les captchas
 * @param page - Page Playwright
 */
async function detectAndSolveCaptcha(page: Page): Promise<void> {
  try {
    // Attendre un peu pour que la page se charge complètement
    await page.waitForTimeout(2000);

    // Obtenir le HTML de la page pour détecter un captcha
    const html = await page.content();
    const htmlLower = html.toLowerCase();

    // Détecter la présence d'un captcha via plusieurs méthodes
    const captchaIndicators = [
      'captcha',
      'challenge',
      'verify you are human',
      'verify you\'re human',
      'i\'m not a robot',
      'recaptcha',
      'hcaptcha',
      'cloudflare challenge',
      'bing captcha',
      'security check',
      'vérification de sécurité',
      'please verify',
      'verify yourself',
    ];

    // Vérifier dans le HTML
    const hasCaptchaInHtml = captchaIndicators.some((indicator) => 
      htmlLower.includes(indicator)
    );

    // Vérifier visuellement avec des sélecteurs spécifiques à Bing
    let hasCaptchaVisually = false;
    try {
      // Sélecteurs spécifiques aux captchas Bing
      const captchaSelectors = [
        '#b_captcha',
        '.b_captcha',
        '[id*="captcha"]',
        '[class*="captcha"]',
        'iframe[src*="captcha"]',
        'iframe[src*="recaptcha"]',
        'iframe[src*="hcaptcha"]',
        'div[id*="challenge"]',
        'div[class*="challenge"]',
      ];

      for (const selector of captchaSelectors) {
        try {
          const element = page.locator(selector).first();
          if (await element.isVisible({ timeout: 1000 })) {
            hasCaptchaVisually = true;
            break;
          }
        } catch (e) {
          continue;
        }
      }
    } catch (e) {
      // Erreur lors de la vérification visuelle, continuer
    }

    // Vérifier l'URL pour des indicateurs de captcha
    const currentUrl = page.url().toLowerCase();
    const hasCaptchaInUrl = currentUrl.includes('captcha') || 
                            currentUrl.includes('challenge') ||
                            currentUrl.includes('verify');

    const hasCaptcha = hasCaptchaInHtml || hasCaptchaVisually || hasCaptchaInUrl;

    if (!hasCaptcha) {
      // Pas de captcha détecté
      return;
    }

    console.log('  ⚠️ Captcha détecté sur la page');

    // Chercher un bouton de résolution de captcha (ajouté par l'extension)
    // Patterns communs pour les boutons de résolution de captcha:
    // - Bouton avec texte "Solve", "Resolve", "Résoudre", etc.
    // - Bouton avec ID/class contenant "solve", "resolve", "captcha-solve", etc.
    // - Bouton ajouté par l'extension de navigateur
    
    const solveButtonSelectors = [
      // Sélecteurs génériques pour les extensions de résolution de captcha
      'button[class*="solve"]',
      'button[class*="resolve"]',
      'button[class*="captcha"]',
      'button[id*="solve"]',
      'button[id*="resolve"]',
      'button[id*="captcha"]',
      'button:has-text("Solve")',
      'button:has-text("Resolve")',
      'button:has-text("Résoudre")',
      'button:has-text("Solve Captcha")',
      'button:has-text("Resolve Captcha")',
      'button:has-text("Auto Solve")',
      'button:has-text("Auto Resolve")',
      // Sélecteurs spécifiques pour certaines extensions populaires
      '[data-captcha-solver]',
      '[data-solve-captcha]',
      '[data-resolve-captcha]',
      '.captcha-solver-button',
      '.solve-captcha-btn',
      '.resolve-captcha-btn',
      '#captcha-solver',
      '#solve-captcha',
      '#resolve-captcha',
      // Sélecteurs pour les extensions qui ajoutent des boutons dans le DOM
      'a[class*="solve"]',
      'a[id*="solve"]',
      'div[class*="solve"][role="button"]',
      'div[id*="solve"][role="button"]',
      // Sélecteurs avec attributs onclick ou data-action
      '[onclick*="solve"]',
      '[onclick*="resolve"]',
      '[data-action*="solve"]',
      '[data-action*="resolve"]',
    ];

    let captchaSolved = false;
    const maxAttempts = 10;
    const waitTime = 3000; // Attendre 3 secondes entre chaque vérification

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      // Essayer de trouver et cliquer sur le bouton de résolution
      let buttonFound = false;
      for (const selector of solveButtonSelectors) {
        try {
          const button = page.locator(selector).first();
          if (await button.isVisible({ timeout: 1000 })) {
            console.log(`  🔧 Bouton de résolution trouvé avec "${selector}"`);
            console.log(`  🔧 Tentative de résolution du captcha (tentative ${attempt + 1}/${maxAttempts})...`);
            
            // Essayer de cliquer sur le bouton
            try {
              await button.click({ timeout: 2000 });
              buttonFound = true;
              await page.waitForTimeout(2000); // Attendre que l'extension commence à résoudre
              break;
            } catch (clickError) {
              // Si le click échoue, essayer avec JavaScript
              try {
                await button.evaluate((el: any) => el.click());
                buttonFound = true;
                await page.waitForTimeout(2000);
                break;
              } catch (jsError) {
                // Les deux méthodes ont échoué, essayer le sélecteur suivant
                continue;
              }
            }
          }
        } catch (e) {
          // Ce sélecteur n'a pas fonctionné, essayer le suivant
          continue;
        }
      }

      // Si aucun bouton n'a été trouvé, attendre un peu au cas où l'extension résout automatiquement
      if (!buttonFound && attempt === 0) {
        console.log('  ⏳ Aucun bouton de résolution trouvé, attente que l\'extension résolve automatiquement...');
      }

      // Attendre un peu pour que le captcha soit résolu
      await page.waitForTimeout(waitTime);

      // Vérifier si le captcha a été résolu
      const currentHtml = await page.content();
      const currentHtmlLower = currentHtml.toLowerCase();
      
      // Vérifier si les indicateurs de captcha ont disparu
      const stillHasCaptcha = captchaIndicators.some((indicator) => 
        currentHtmlLower.includes(indicator)
      );

      // Vérifier si les résultats de recherche sont maintenant présents
      const hasResults = await page.locator('ol#b_results li.b_algo, main[role="main"] li.b_algo').count() > 0;

      if (!stillHasCaptcha || hasResults) {
        console.log('  ✓ Captcha résolu (ou page chargée)');
        captchaSolved = true;
        break;
      }

      // Vérifier aussi l'URL pour voir si on a été redirigé vers les résultats
      const currentUrl = page.url();
      if (currentUrl.includes('/search') && !currentUrl.includes('captcha') && !currentUrl.includes('challenge')) {
        console.log('  ✓ Redirection vers les résultats détectée');
        captchaSolved = true;
        break;
      }
    }

    if (!captchaSolved) {
      console.log('  ⚠️ Captcha détecté mais non résolu automatiquement après plusieurs tentatives');
      console.log('  💡 Assurez-vous que votre extension de résolution de captcha est installée et active');
    } else {
      // Attendre un peu plus pour que la page se stabilise après résolution
      await page.waitForTimeout(2000);
    }
  } catch (error: any) {
    // Ne pas faire planter le processus si la détection/résolution échoue
    console.log(`  ⚠️ Erreur lors de la détection/résolution du captcha: ${error.message || error}`);
  }
}

/**
 * Recherche sur Bing via URL directe (plus robuste)
 * @param query - La requête de recherche
 * @param maxResults - Nombre maximum de résultats à récupérer
 * @returns Liste des résultats avec titre et URL
 */
export async function searchBing(
  query: string,
  maxResults: number = 20
): Promise<SearchResult[]> {
  console.log(`🔍 Recherche Bing: "${query}" (max ${maxResults} résultats)`);

  let browser: Browser | null = null;
  const results: SearchResult[] = [];

  try {
    // Lancer le navigateur Chrome (pas Chromium) pour supporter les extensions
    // Note: headless peut être désactivé via HEADLESS=false pour permettre aux extensions de fonctionner
    // Les extensions de résolution de captcha nécessitent généralement le mode non-headless
    const headless = config.headless;
    const launchOptions: any = {
      channel: 'chrome', // Utiliser Chrome installé au lieu de Chromium (nécessaire pour les extensions)
      headless,
      args: [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
      ],
    };

    // Si un profil Chrome est spécifié, l'utiliser pour charger les extensions
    if (config.chromeUserDataDir) {
      launchOptions.args.push(`--user-data-dir=${config.chromeUserDataDir}`);
      console.log(`  📁 Utilisation du profil Chrome: ${config.chromeUserDataDir}`);
    }

    browser = await chromium.launch(launchOptions);

    const context = await browser.newContext({
      userAgent:
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      viewport: { width: 1920, height: 1080 },
      locale: 'fr-FR',
    });

    const page = await context.newPage();
    
    // Masquer les propriétés d'automation
    await page.addInitScript(() => {
      // @ts-ignore - Ces objets existent dans le contexte du navigateur
      Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
      });
      // @ts-ignore
      (window as any).chrome = { runtime: {} };
    });

    // Construire directement l'URL de recherche (plus robuste)
    const searchUrl = `https://www.bing.com/search?q=${encodeURIComponent(query)}&count=${Math.min(maxResults, 50)}`;
    
    console.log(`  → Navigation directe vers: ${searchUrl.substring(0, 80)}...`);
    
    await page.goto(searchUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    await page.waitForTimeout(2000 + Math.random() * 1000);

    // Accepter les cookies si nécessaire
    try {
      const acceptButton = page.locator('button#bnp_btn_accept, button:has-text("Accept"), button:has-text("Accepter")').first();
      if (await acceptButton.isVisible({ timeout: 2000 })) {
        await acceptButton.click();
        await page.waitForTimeout(1000);
      }
    } catch (e) {
      // Pas de popup de cookies
    }

    // Détecter et résoudre les captchas
    await detectAndSolveCaptcha(page);

    // Attendre les résultats
    try {
      await page.waitForSelector('ol#b_results li.b_algo, main[role="main"] li.b_algo', { 
        timeout: 10000 
      });
      await page.waitForTimeout(1000);
    } catch (e) {
      // Peut-être que les résultats sont déjà là
    }

    // Extraire les résultats organiques
    const organicResults = page.locator('ol#b_results li.b_algo, main[role="main"] li.b_algo');

    const count = await organicResults.count();
    console.log(`  → ${count} résultats trouvés sur la page`);

    for (let i = 0; i < Math.min(count, maxResults); i++) {
      try {
        const result = organicResults.nth(i);
        const link = result.locator('h2 a, h3 a').first();
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
    console.error(`✗ Erreur lors de la recherche Bing:`, error);
    throw error;
  } finally {
    if (browser) {
      await browser.close();
    }
  }

  return results;
}

/**
 * Recherche Bing avec une page Playwright existante (pour réutilisation)
 * @param page - Page Playwright
 * @param query - La requête de recherche
 * @param maxResults - Nombre maximum de résultats
 * @returns Liste des résultats
 */
export async function searchBingWithPage(
  page: Page,
  query: string,
  maxResults: number = 20
): Promise<SearchResult[]> {
  const results: SearchResult[] = [];

  try {
    const searchUrl = `https://www.bing.com/search?q=${encodeURIComponent(query)}&count=${Math.min(maxResults, 50)}`;
    await page.goto(searchUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    await page.waitForTimeout(2000);

    // Détecter et résoudre les captchas
    await detectAndSolveCaptcha(page);

    const organicResults = page.locator('ol#b_results li.b_algo, main[role="main"] li.b_algo');
    const count = await organicResults.count();

    for (let i = 0; i < Math.min(count, maxResults); i++) {
      try {
        const result = organicResults.nth(i);
        const link = result.locator('h2 a, h3 a').first();
        const url = await link.getAttribute('href');
        const title = await link.textContent();

        if (url && url.startsWith('http')) {
          results.push({
            title: (title || url).trim(),
            url: url.trim(),
          });
        }
      } catch (e) {
        continue;
      }
    }
  } catch (error) {
    // Retourner les résultats collectés jusqu'à présent
  }

  return results;
}

