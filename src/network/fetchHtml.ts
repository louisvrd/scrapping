/**
 * Module de récupération HTML
 * Fait des requêtes HTTP pour récupérer le contenu HTML des pages
 */

export interface FetchHtmlOptions {
  timeoutMs?: number;
  method?: 'GET' | 'HEAD';
  followRedirects?: boolean;
}

/**
 * Récupère le HTML d'une URL
 * @param url - L'URL à récupérer
 * @param timeoutOrOptions - Timeout en ms (défaut: 10000) ou options complètes
 * @param options - Options de requête (si timeoutOrOptions est un nombre)
 * @returns Le HTML en string ou null en cas d'erreur
 */
export async function fetchHtml(
  url: string,
  timeoutOrOptions?: number | FetchHtmlOptions,
  options?: FetchHtmlOptions
): Promise<string | null> {
  // Support de l'ancienne signature (timeout) et nouvelle (options)
  let opts: FetchHtmlOptions;
  if (typeof timeoutOrOptions === 'number') {
    opts = { timeoutMs: timeoutOrOptions, ...options };
  } else {
    opts = timeoutOrOptions || {};
  }
  
  const timeoutMs = opts.timeoutMs || 10000;
  const method = opts.method || 'GET';
  const followRedirects = opts.followRedirects !== false;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const response = await fetch(url, {
      method: method,
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        Accept:
          'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
      },
      signal: controller.signal,
      redirect: followRedirects ? 'follow' : 'manual',
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      return null;
    }

    // Pour HEAD, on ne récupère pas le body
    if (method === 'HEAD') {
      return '';
    }

    const html = await response.text();
    return html;
  } catch (error: any) {
    if (error.name === 'AbortError') {
      // Timeout
      return null;
    }
    // Autre erreur (réseau, etc.)
    return null;
  }
}

