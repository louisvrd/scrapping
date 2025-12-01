#!/usr/bin/env node
/**
 * CLI pour le scan CT massif avec patterns alphabétiques
 * Usage: npm run shopify-ct-mass -- --depth=1 --digits=true --maxTotalDomains=50000
 * 
 * Exemples:
 *   npm run shopify-ct-mass -- --depth=1
 *   npm run shopify-ct-mass -- --depth=2 --digits=true
 *   npm run shopify-ct-mass -- --depth=1 --maxTotalDomains=100000 --limitPerPattern=5000
 */

import { massFetchDomainsFromCT, MassCtOptions } from '../ct/massCtScanner.js';
import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';

/**
 * Parse les arguments de la ligne de commande
 */
function parseArgs(): MassCtOptions {
  const args = process.argv.slice(2);
  const options: MassCtOptions = {};

  // Format avec flags
  for (const arg of args) {
    if (arg.startsWith('--limitPerPattern=')) {
      const value = parseInt(arg.split('=')[1], 10);
      if (!isNaN(value) && value > 0) {
        options.limitPerPattern = value;
      }
    } else if (arg.startsWith('--maxTotalDomains=')) {
      const value = parseInt(arg.split('=')[1], 10);
      if (!isNaN(value) && value > 0) {
        options.maxTotalDomains = value;
      }
    } else if (arg.startsWith('--sleepMs=')) {
      const value = parseInt(arg.split('=')[1], 10);
      if (!isNaN(value) && value >= 0) {
        options.sleepMsBetweenRequests = value;
      }
    } else if (arg.startsWith('--timeout=')) {
      const value = parseInt(arg.split('=')[1], 10);
      if (!isNaN(value) && value > 0) {
        options.timeout = value;
      }
    } else if (arg.startsWith('--stopAfterErrors=')) {
      const value = parseInt(arg.split('=')[1], 10);
      if (!isNaN(value) && value > 0) {
        options.stopAfterConsecutiveErrors = value;
      }
    } else if (arg.startsWith('--useDateRanges=')) {
      const value = arg.split('=')[1].toLowerCase();
      options.useDateRanges = value === 'true' || value === '1' || value === 'yes';
    } else if (arg.startsWith('--useDifferentEndpoints=')) {
      const value = arg.split('=')[1].toLowerCase();
      options.useDifferentEndpoints = value === 'true' || value === '1' || value === 'yes';
    } else if (arg.startsWith('--daysBack=')) {
      const value = parseInt(arg.split('=')[1], 10);
      if (!isNaN(value) && value > 0) {
        options.daysBack = value;
      }
    }
  }

  return options;
}

/**
 * Affiche l'aide
 */
function showHelp() {
  console.error('Usage: npm run shopify-ct-mass -- [options]');
  console.error('');
  console.error('Options:');
  console.error('  --limitPerPattern=N      Nombre max de domaines par requête (défaut: illimité)');
  console.error('  --maxTotalDomains=N      Nombre max total de domaines (défaut: illimité)');
  console.error('  --sleepMs=N              Pause en ms entre requêtes (défaut: 2000)');
  console.error('  --timeout=N             Timeout en ms pour chaque requête (défaut: 60000)');
  console.error('  --stopAfterErrors=N     Arrêter après N erreurs consécutives (défaut: pas de limite)');
  console.error('  --useDateRanges=true|false  Utiliser des requêtes avec plages de dates (défaut: true)');
  console.error('  --useDifferentEndpoints=true|false  Utiliser différents endpoints (défaut: true)');
  console.error('  --daysBack=N            Nombre de jours en arrière pour les requêtes par date (défaut: 365)');
  console.error('');
  console.error('Exemples:');
  console.error('  npm run shopify-ct-mass -- --useDateRanges=true --daysBack=730');
  console.error('  npm run shopify-ct-mass -- --maxTotalDomains=50000 --sleepMs=2000');
  console.error('  npm run shopify-ct-mass -- --useDateRanges=true --useDifferentEndpoints=true');
  console.error('');
}

async function main() {
  const options = parseArgs();

  // Valeurs par défaut si non spécifiées
  const finalOptions: MassCtOptions = {
    limitPerPattern: options.limitPerPattern,
    maxTotalDomains: options.maxTotalDomains,
    sleepMsBetweenRequests: options.sleepMsBetweenRequests ?? 2000,
    timeout: options.timeout || 60000,
    useDateRanges: options.useDateRanges ?? true,
    useDifferentEndpoints: options.useDifferentEndpoints ?? true,
    daysBack: options.daysBack || 365,
    stopAfterConsecutiveErrors: options.stopAfterConsecutiveErrors,
  };

  try {
    // Lancer le scan CT massif
    const result = await massFetchDomainsFromCT(finalOptions);

    // Préparer les données pour la sauvegarde
    const outputData = {
      generatedAt: new Date().toISOString(),
      useDateRanges: finalOptions.useDateRanges,
      useDifferentEndpoints: finalOptions.useDifferentEndpoints,
      daysBack: finalOptions.daysBack,
      limitPerPattern: finalOptions.limitPerPattern || null,
      maxTotalDomains: finalOptions.maxTotalDomains || null,
      sleepMsBetweenRequests: finalOptions.sleepMsBetweenRequests,
      patternsUsed: result.patternsUsed,
      totalDomains: result.totalDomains,
      domains: result.domains,
    };

    // Sauvegarder en JSON
    try {
      const outputDir = join(process.cwd(), 'output');
      await mkdir(outputDir, { recursive: true });

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = join(outputDir, `ct-mass-domains-${timestamp}.json`);

      await writeFile(filename, JSON.stringify(outputData, null, 2), 'utf-8');
      console.log(`💾 Domaines sauvegardés dans: ${filename}\n`);
    } catch (error: any) {
      console.warn('⚠ Impossible de sauvegarder le fichier JSON:', error.message);
    }

    // Afficher un résumé final
    console.log(`✅ Scan terminé avec succès`);
    console.log(`   - ${result.patternsUsed.length} patterns traités`);
    console.log(`   - ${result.totalDomains} domaines uniques collectés\n`);

    process.exit(0);
  } catch (error: any) {
    console.error('\n❌ Erreur fatale:', error.message);
    if (error.stack) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

// Si --help est demandé, afficher l'aide
if (process.argv.includes('--help') || process.argv.includes('-h')) {
  showHelp();
  process.exit(0);
}

main();

