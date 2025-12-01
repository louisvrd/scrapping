#!/usr/bin/env node
/**
 * CLI pour le scan Shopify
 * Usage: 
 *   npm run shopify-scan -- "niche à chercher"  (scan ciblé)
 *   npm run shopify-scan -- --massive           (scan massif)
 */

import { scanNiche, ScanOutput } from '../pipeline/scanNiche.js';
import { scanMassive } from '../pipeline/scanMassive.js';
import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';

async function main() {
  // Récupérer les arguments
  const args = process.argv.slice(2);
  
  // Vérifier si c'est un scan massif
  if (args.includes('--massive') || args.includes('-m')) {
    console.log('🚀 Mode SCAN MASSIF activé\n');
    
    const maxResultsPerQuery = parseInt(process.env.MAX_RESULTS_PER_QUERY || '50', 10);
    
    try {
      const output = await scanMassive({
        maxResultsPerQuery,
        timeout: 10000,
        useGenericQueries: true,
        useShopifyQueries: true,
      });
      
      // Afficher les résultats
      if (output.shopifyUrls.length > 0) {
        console.log(`\n🎯 ${output.shopifyUrls.length} SITE(S) SHOPIFY TROUVÉ(S):\n`);
        output.shopifyUrls.forEach((url, index) => {
          const result = output.results.find((r) => r.url === url);
          const confidence = result?.confidence
            ? ` (confiance: ${(result.confidence * 100).toFixed(0)}%)`
            : '';
          console.log(`  ${index + 1}. ${url}${confidence}`);
        });
        console.log('');
      } else {
        console.log('\n⚠ Aucun site Shopify détecté\n');
      }

      // Sauvegarder
      try {
        const outputDir = join(process.cwd(), 'output');
        await mkdir(outputDir, { recursive: true });

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = join(outputDir, `shopify-massive-${timestamp}.json`);

        await writeFile(filename, JSON.stringify(output, null, 2), 'utf-8');
        console.log(`💾 Résultats sauvegardés dans: ${filename}\n`);
      } catch (error) {
        console.warn('⚠ Impossible de sauvegarder le fichier JSON:', error);
      }

      process.exit(output.shopifyCount > 0 ? 0 : 1);
    } catch (error: any) {
      console.error('\n❌ Erreur fatale:', error.message);
      console.error(error.stack);
      process.exit(1);
    }
    return;
  }
  
  // Mode scan ciblé (ancien comportement)
  if (args.length === 0) {
    console.error('❌ Erreur: Veuillez fournir une requête de recherche ou utiliser --massive');
    console.error('');
    console.error('Usage:');
    console.error('  npm run shopify-scan -- "votre requête"     (scan ciblé)');
    console.error('  npm run shopify-scan -- --massive           (scan massif - maximum d\'URLs)');
    console.error('');
    console.error('Exemples:');
    console.error('  npm run shopify-scan -- "bijoux artisanaux"');
    console.error('  npm run shopify-scan -- --massive');
    process.exit(1);
  }

  const query = args.join(' ');

  // Options (peut être étendu pour accepter des flags)
  const maxResults = parseInt(process.env.MAX_RESULTS || '20', 10);

  try {
    // Lancer le scan
    const output: ScanOutput = await scanNiche(query, {
      maxResults,
      timeout: 10000,
    });

    // Afficher les résultats Shopify
    if (output.shopifyUrls.length > 0) {
      console.log(`\n🎯 ${output.shopifyUrls.length} SITE(S) SHOPIFY TROUVÉ(S):\n`);
      output.shopifyUrls.forEach((url, index) => {
        const result = output.results.find((r) => r.url === url);
        const confidence = result?.confidence
          ? ` (confiance: ${(result.confidence * 100).toFixed(0)}%)`
          : '';
        console.log(`  ${index + 1}. ${url}${confidence}`);
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
      const filename = join(outputDir, `shopify-scan-${timestamp}.json`);

      await writeFile(filename, JSON.stringify(output, null, 2), 'utf-8');
      console.log(`💾 Résultats sauvegardés dans: ${filename}\n`);
    } catch (error) {
      console.warn('⚠ Impossible de sauvegarder le fichier JSON:', error);
    }

    // Code de sortie
    process.exit(output.shopifyCount > 0 ? 0 : 1);
  } catch (error: any) {
    console.error('\n❌ Erreur fatale:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

main();

