#!/usr/bin/env node
/**
 * CLI pour le scan basé sur Certificate Transparency
 * Usage: npm run shopify-scan-ct -- "%.myshopify.com" [maxDomains]
 * 
 * Exemple:
 *   npm run shopify-scan-ct -- "%.myshopify.com"
 *   npm run shopify-scan-ct -- "%.myshopify.com" 5000
 */

import { scanCT, CtScanResult } from '../pipeline/scanCT.js';
import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.error('❌ Erreur: Veuillez fournir un pattern CT');
    console.error('');
    console.error('Usage: npm run shopify-scan-ct -- "<pattern>" [maxDomains]');
    console.error('');
    console.error('Exemples:');
    console.error('  npm run shopify-scan-ct -- "%.myshopify.com"');
    console.error('  npm run shopify-scan-ct -- "%.myshopify.com" 5000');
    console.error('  npm run shopify-scan-ct -- "%.shopify.com"');
    console.error('');
    console.error('Patterns courants:');
    console.error('  "%.myshopify.com"  - Tous les domaines myshopify.com');
    console.error('  "%.shopify.com"    - Tous les domaines shopify.com');
    process.exit(1);
  }

  const pattern = args[0];
  const maxDomains = args[1] ? parseInt(args[1], 10) : undefined;
  const concurrency = parseInt(process.env.CONCURRENCY || '10', 10);
  const timeout = parseInt(process.env.TIMEOUT || '10000', 10);

  if (maxDomains !== undefined && (isNaN(maxDomains) || maxDomains <= 0)) {
    console.error('❌ Erreur: maxDomains doit être un nombre positif');
    process.exit(1);
  }

  try {
    // Lancer le scan CT
    const output: CtScanResult = await scanCT({
      pattern,
      maxDomains: maxDomains || 10000,
      concurrency,
      timeout,
    });

    // Afficher les résultats Shopify
    if (output.shopifyUrls.length > 0) {
      console.log(`\n🎯 ${output.shopifyUrls.length} SITE(S) SHOPIFY TROUVÉ(S):\n`);
      output.shopifyUrls.forEach((url, index) => {
        const result = output.results.find((r) => r.url === url);
        const cnameInfo = result?.cnames.length
          ? ` (CNAME: ${result.cnames.join(', ')})`
          : '';
        console.log(`  ${index + 1}. ${url}${cnameInfo}`);
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
      const filename = join(outputDir, `shopify-ct-${timestamp}.json`);

      await writeFile(filename, JSON.stringify(output, null, 2), 'utf-8');
      console.log(`💾 Résultats sauvegardés dans: ${filename}\n`);
    } catch (error) {
      console.warn('⚠ Impossible de sauvegarder le fichier JSON:', error);
    }

    // Code de sortie
    process.exit(output.shopifyCount > 0 ? 0 : 1);
  } catch (error: any) {
    console.error('\n❌ Erreur fatale:', error.message);
    if (error.stack) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

main();


