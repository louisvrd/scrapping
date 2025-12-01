/**
 * Configuration et gestion des variables d'environnement
 */

export interface Config {
  maxResults: number;
  timeout: number;
  headless: boolean;
  chromeUserDataDir?: string; // Chemin vers le profil Chrome (pour charger les extensions)
}

export const config: Config = {
  maxResults: parseInt(process.env.MAX_RESULTS || '20', 10),
  timeout: parseInt(process.env.TIMEOUT || '10000', 10),
  headless: process.env.HEADLESS !== 'false',
  chromeUserDataDir: process.env.CHROME_USER_DATA_DIR, // Optionnel: chemin vers le profil Chrome
};

