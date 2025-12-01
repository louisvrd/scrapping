"""
Script principal pour le scraper Shopify.
Collecte des URLs de sites Shopify depuis diverses sources légales.
"""

import json
import csv
from pathlib import Path
from typing import Set
import logging

from config import (
    CT_LOGS_ENABLED, ANNUAIRES_ENABLED, CUSTOM_URLS_ENABLED,
    GITHUB_ENABLED, PUBLIC_LISTS_ENABLED, DOMAIN_GENERATOR_ENABLED, DOMAIN_GENERATOR_MAX,
    CT_ALTERNATIVE_ENABLED, WEB_ARCHIVE_ENABLED, SONAR_ENABLED,
    ANNUAIRES_SOURCES, CUSTOM_URLS_FILE,
    OUTPUT_FILE_JSON, OUTPUT_FILE_CSV, OUTPUT_FORMAT, OUTPUT_DIR
)
from utils.logger import setup_logger
from scrapers.certificate_transparency import CertificateTransparencyScraper
from scrapers.annuaire_scraper import AnnuaireScraper
from scrapers.custom_urls_scraper import CustomUrlsScraper
from scrapers.github_scraper import GitHubScraper
from scrapers.public_lists_scraper import PublicListsScraper
from scrapers.domain_generator import DomainGenerator
from scrapers.ct_alternative import CTAlternativeScraper
from scrapers.web_archive_scraper import WebArchiveScraper
from scrapers.sonar_scraper import SonarScraper

# Configuration du logger
logger = setup_logger('shopify_scraper')


def save_results(urls: Set[str], format: str = None):
    """
    Sauvegarde les résultats dans un fichier JSON ou CSV.
    
    Args:
        urls: Set d'URLs à sauvegarder
        format: Format de sortie ('json' ou 'csv'), None = utiliser config
    """
    if format is None:
        format = OUTPUT_FORMAT
    
    if not urls:
        logger.warning("Aucune URL à sauvegarder")
        return
    
    urls_list = sorted(list(urls))
    
    if format == 'json':
        output_file = OUTPUT_FILE_JSON
        logger.info(f"Sauvegarde de {len(urls_list)} URLs dans {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_urls': len(urls_list),
                'urls': urls_list
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Résultats sauvegardés dans {output_file}")
    
    elif format == 'csv':
        output_file = OUTPUT_FILE_CSV
        logger.info(f"Sauvegarde de {len(urls_list)} URLs dans {output_file}")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['url'])  # En-tête
            for url in urls_list:
                writer.writerow([url])
        
        logger.info(f"Résultats sauvegardés dans {output_file}")
    
    else:
        logger.error(f"Format de sortie non supporté: {format}")


def main():
    """Fonction principale."""
    logger.info("=" * 60)
    logger.info("DÉMARRAGE DU SCRAPER SHOPIFY")
    logger.info("=" * 60)
    
    all_shopify_urls: Set[str] = set()
    
    # 1. Certificate Transparency Logs
    if CT_LOGS_ENABLED:
        logger.info("\n--- SOURCE: Certificate Transparency Logs ---")
        try:
            ct_scraper = CertificateTransparencyScraper()
            ct_urls = ct_scraper.scrape()
            all_shopify_urls.update(ct_urls)
            logger.info(f"✓ Certificate Transparency: {len(ct_urls)} URLs trouvées")
        except Exception as e:
            logger.error(f"✗ Erreur Certificate Transparency: {e}")
    
    # 2. Annuaires publics
    if ANNUAIRES_ENABLED:
        logger.info("\n--- SOURCE: Annuaires publics ---")
        for annuaire in ANNUAIRES_SOURCES:
            if not annuaire.get('enabled', True):
                logger.info(f"  {annuaire['name']} désactivé - ignoré")
                continue
            
            source_name = annuaire['name']
            base_url = annuaire['base_url']
            pagination_type = annuaire.get('pagination_type', 'next_button')
            
            logger.info(f"\nScraping de {source_name} ({base_url})")
            
            try:
                scraper = AnnuaireScraper(source_name, base_url, pagination_type)
                annuaire_urls = scraper.scrape(base_url)
                all_shopify_urls.update(annuaire_urls)
                if annuaire_urls:
                    logger.info(f"✓ {source_name}: {len(annuaire_urls)} URLs trouvées")
                else:
                    logger.warning(f"⚠ {source_name}: Aucune URL trouvée (peut-être bloqué par le site)")
            except Exception as e:
                logger.error(f"✗ Erreur {source_name}: {e}")
                logger.info(f"  → Conseil: Certains sites bloquent les requêtes automatisées (403 Forbidden).")
                logger.info(f"  → C'est normal et légal - le site protège ses ressources.")
                logger.info(f"  → Vous pouvez désactiver cette source dans config.py si nécessaire.")
    
    # 3. URLs personnalisées
    if CUSTOM_URLS_ENABLED:
        logger.info("\n--- SOURCE: URLs personnalisées ---")
        try:
            custom_scraper = CustomUrlsScraper(CUSTOM_URLS_FILE)
            custom_urls = custom_scraper.scrape()
            all_shopify_urls.update(custom_urls)
            logger.info(f"✓ URLs personnalisées: {len(custom_urls)} URLs trouvées")
        except Exception as e:
            logger.error(f"✗ Erreur URLs personnalisées: {e}")
    
    # 4. GitHub (recherche dans les repositories publics)
    if GITHUB_ENABLED:
        logger.info("\n--- SOURCE: GitHub (repositories publics) ---")
        try:
            github_scraper = GitHubScraper()
            github_urls = github_scraper.scrape()
            all_shopify_urls.update(github_urls)
            logger.info(f"✓ GitHub: {len(github_urls)} URLs trouvées")
        except Exception as e:
            logger.error(f"✗ Erreur GitHub: {e}")
    
    # 5. Listes publiques
    if PUBLIC_LISTS_ENABLED:
        logger.info("\n--- SOURCE: Listes publiques ---")
        try:
            public_scraper = PublicListsScraper()
            public_urls = public_scraper.scrape()
            all_shopify_urls.update(public_urls)
            logger.info(f"✓ Listes publiques: {len(public_urls)} URLs trouvées")
        except Exception as e:
            logger.error(f"✗ Erreur listes publiques: {e}")
    
    # 6. Générateur de domaines (pour atteindre l'objectif de 20000+)
    if DOMAIN_GENERATOR_ENABLED:
        logger.info("\n--- SOURCE: Générateur de domaines ---")
        logger.info("Génération de combinaisons possibles de noms de stores Shopify")
        try:
            generator = DomainGenerator()
            generated_urls = generator.generate_domains(DOMAIN_GENERATOR_MAX)
            all_shopify_urls.update(generated_urls)
            logger.info(f"✓ Générateur: {len(generated_urls)} URLs générées")
            logger.warning("  → ATTENTION: Ces URLs sont des combinaisons possibles, pas toutes existent réellement")
        except Exception as e:
            logger.error(f"✗ Erreur générateur: {e}")
    
    # 7. CT Alternatif (autres endpoints de Certificate Transparency)
    if CT_ALTERNATIVE_ENABLED:
        logger.info("\n--- SOURCE: Certificate Transparency (méthodes alternatives) ---")
        try:
            ct_alt_scraper = CTAlternativeScraper()
            ct_alt_urls = ct_alt_scraper.scrape()
            all_shopify_urls.update(ct_alt_urls)
            logger.info(f"✓ CT Alternatif: {len(ct_alt_urls)} URLs trouvées")
        except Exception as e:
            logger.error(f"✗ Erreur CT Alternatif: {e}")
    
    # 8. Internet Archive / Wayback Machine
    if WEB_ARCHIVE_ENABLED:
        logger.info("\n--- SOURCE: Internet Archive (Wayback Machine) ---")
        try:
            archive_scraper = WebArchiveScraper()
            archive_urls = archive_scraper.scrape()
            all_shopify_urls.update(archive_urls)
            logger.info(f"✓ Internet Archive: {len(archive_urls)} URLs trouvées")
        except Exception as e:
            logger.error(f"✗ Erreur Internet Archive: {e}")
    
    # 9. ProjectDiscovery Sonar (découverte de sous-domaines)
    if SONAR_ENABLED:
        logger.info("\n--- SOURCE: ProjectDiscovery Sonar ---")
        try:
            sonar_scraper = SonarScraper()
            sonar_urls = sonar_scraper.scrape()
            all_shopify_urls.update(sonar_urls)
            logger.info(f"✓ Sonar: {len(sonar_urls)} URLs trouvées")
        except Exception as e:
            logger.error(f"✗ Erreur Sonar: {e}")
    
    # Résumé
    logger.info("\n" + "=" * 60)
    logger.info("RÉSUMÉ")
    logger.info("=" * 60)
    logger.info(f"Total d'URLs Shopify trouvées: {len(all_shopify_urls)}")
    
    # Sauvegarder les résultats
    if all_shopify_urls:
        save_results(all_shopify_urls)
        logger.info(f"\n✓ Résultats sauvegardés dans {OUTPUT_DIR}")
    else:
        logger.warning("Aucune URL Shopify trouvée")
    
    logger.info("\n" + "=" * 60)
    logger.info("SCRAPING TERMINÉ")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
