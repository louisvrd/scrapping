#!/usr/bin/env node
/**
 * CLI pour le scan Bing bulk
 * Lit un fichier queries.txt et scanne massivement des boutiques Shopify via Bing
 * 
 * Usage:
 *   npm run shopify-scan-bing-bulk
 *   npm run shopify-scan-bing-bulk -- queries.txt
 *   npm run shopify-scan-bing-bulk -- --config
 */

import { scanBingBulk, BingBulkScanResult } from '../pipeline/scanBingBulk.js';
import { ALL_SHOPIFY_QUERIES } from '../config/queries-shopify.js';
import { writeFile, mkdir, readFile } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';

/**
 * Lit les requêtes depuis un fichier texte (une requête par ligne)
 */
async function readQueriesFromFile(filePath: string): Promise<string[]> {
  try {
    const content = await readFile(filePath, 'utf-8');
    const queries = content
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0 && !line.startsWith('#')); // Ignorer les lignes vides et les commentaires
    
    return queries;
  } catch (error: any) {
    throw new Error(`Impossible de lire le fichier ${filePath}: ${error.message}`);
  }
}

async function main() {
  const args = process.argv.slice(2);
  
  let queries: string[] = [];
  let queriesFile: string | null = null;
  let useConfig = false;
  let maxResultsPerQuery = 50;
  let sleepMs = 3000;

  // Parser les arguments
  for (const arg of args) {
    if (arg === '--config' || arg === '-c') {
      useConfig = true;
    } else if (arg.startsWith('--maxResults=')) {
      const value = parseInt(arg.split('=')[1], 10);
      if (!isNaN(value) && value > 0) {
        maxResultsPerQuery = value;
      }
    } else if (arg.startsWith('--sleepMs=')) {
      const value = parseInt(arg.split('=')[1], 10);
      if (!isNaN(value) && value >= 0) {
        sleepMs = value;
      }
    } else if (!arg.startsWith('--')) {
      // C'est probablement le chemin du fichier
      queriesFile = arg;
    }
  }

  // Déterminer la source des requêtes
  if (useConfig) {
    // Utiliser les requêtes depuis le fichier de config
    queries = ALL_SHOPIFY_QUERIES.map((q) => q.query);
    console.log(`📋 Utilisation de ${queries.length} requêtes depuis config/queries-shopify.ts\n`);
  } else if (queriesFile) {
    // Lire depuis le fichier spécifié
    if (!existsSync(queriesFile)) {
      console.error(`❌ Erreur: Le fichier "${queriesFile}" n'existe pas`);
      process.exit(1);
    }
    queries = await readQueriesFromFile(queriesFile);
    console.log(`📋 ${queries.length} requêtes lues depuis "${queriesFile}"\n`);
  } else {
    // Essayer de lire queries.txt par défaut
    const defaultFile = 'queries.txt';
    if (existsSync(defaultFile)) {
      queries = await readQueriesFromFile(defaultFile);
      console.log(`📋 ${queries.length} requêtes lues depuis "${defaultFile}"\n`);
    } else {
      // Afficher l'aide
      console.error('❌ Erreur: Aucune source de requêtes spécifiée');
      console.error('');
      console.error('Usage: npm run shopify-scan-bing-bulk -- [options]');
      console.error('');
      console.error('Options:');
      console.error('  <fichier>              Chemin vers un fichier texte avec une requête par ligne');
      console.error('  --config, -c           Utiliser les requêtes depuis config/queries-shopify.ts');
      console.error('  --maxResults=N         Nombre max de résultats par requête (défaut: 50)');
      console.error('  --sleepMs=N           Pause en ms entre requêtes (défaut: 3000)');
      console.error('');
      console.error('Exemples:');
      console.error('  npm run shopify-scan-bing-bulk -- queries.txt');
      console.error('  npm run shopify-scan-bing-bulk -- --config');
      console.error('  npm run shopify-scan-bing-bulk -- queries.txt --maxResults=100 --sleepMs=5000');
      console.error('');
      console.error('Format du fichier queries.txt:');
      console.error('  Une requête par ligne, ex:');
      console.error('    site:myshopify.com "bracelets"');
      console.error('    site:myshopify.com "yoga"');
      console.error('    # Commentaire (lignes commençant par # sont ignorées)');
      console.error('');
      process.exit(1);
    }
  }

  if (queries.length === 0) {
    console.error('❌ Erreur: Aucune requête trouvée');
    process.exit(1);
  }

  try {
    // Lancer le scan Bing bulk
    const result: BingBulkScanResult = await scanBingBulk({
      queries,
      maxResultsPerQuery,
      sleepMsBetweenQueries: sleepMs,
      timeout: 15000,
      reuseBrowser: false, // searchBing gère déjà le navigateur
    });

    // Afficher les résultats Shopify
    if (result.shopifyUrls.length > 0) {
      console.log(`\n🎯 ${result.shopifyUrls.length} SITE(S) SHOPIFY TROUVÉ(S):\n`);
      result.shopifyUrls.forEach((url, index) => {
        const resultItem = result.results.find((r) => r.url === url);
        const titleInfo = resultItem?.title ? ` (${resultItem.title})` : '';
        console.log(`  ${index + 1}. ${url}${titleInfo}`);
      });
      console.log('');
    } else {
      console.log('\n⚠ Aucun site Shopify détecté\n');
    }

    // Sauvegarder en JSON
    try {
      const outputDir = join(process.cwd(), 'output');
      await mkdir(outputDir, { recursive: true });

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = join(outputDir, `shopify-bing-bulk-${timestamp}.json`);

      await writeFile(filename, JSON.stringify(result, null, 2), 'utf-8');
      console.log(`💾 Résultats sauvegardés dans: ${filename}\n`);
    } catch (error: any) {
      console.warn('⚠ Impossible de sauvegarder le fichier JSON:', error.message);
    }

    // Code de sortie
    process.exit(result.shopifyCount > 0 ? 0 : 1);
  } catch (error: any) {
    console.error('\n❌ Erreur fatale:', error.message);
    if (error.stack) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

main();


