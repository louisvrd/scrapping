"""
Générateur de domaines Shopify possibles basé sur des patterns.
Méthode légale : génère des combinaisons possibles de noms de stores.
"""

import string
import random
from typing import Set
import logging
import itertools

logger = logging.getLogger(__name__)


class DomainGenerator:
    """
    Génère des domaines Shopify possibles basés sur des patterns.
    Vérifie ensuite si le domaine existe réellement.
    """
    
    def __init__(self):
        self.generated_domains = set()
    
    def _generate_common_patterns(self) -> Set[str]:
        """
        Génère des domaines basés sur des patterns communs.
        
        Returns:
            Set de domaines générés
        """
        domains = set()
        
        # Patterns communs pour les noms de stores
        common_words = [
            'shop', 'store', 'boutique', 'market', 'mall', 'bazar',
            'fashion', 'style', 'trend', 'design', 'art', 'craft',
            'home', 'house', 'life', 'world', 'global', 'local',
            'best', 'top', 'premium', 'luxury', 'elite', 'pro',
            'tech', 'digital', 'online', 'web', 'net', 'hub',
            'plus', 'max', 'super', 'mega', 'ultra', 'prime',
            'new', 'fresh', 'modern', 'vintage', 'classic', 'retro',
        ]
        
        # Générer des combinaisons simples
        for word in common_words[:50]:  # Limiter pour éviter trop de combinaisons
            # Mot seul
            domains.add(word)
            # Mot + nombre
            for num in range(1, 100):
                domains.add(f"{word}{num}")
                domains.add(f"{word}-{num}")
            # Préfixes communs
            for prefix in ['my', 'the', 'best', 'top', 'new']:
                domains.add(f"{prefix}{word}")
                domains.add(f"{prefix}-{word}")
        
        logger.info(f"Génération de {len(domains)} domaines basés sur des patterns communs")
        return domains
    
    def _generate_random_combinations(self, count: int = 10000) -> Set[str]:
        """
        Génère des combinaisons aléatoires de caractères.
        
        Args:
            count: Nombre de combinaisons à générer
        
        Returns:
            Set de domaines générés
        """
        domains = set()
        
        # Caractères valides pour les domaines
        chars = string.ascii_lowercase + string.digits
        
        # Générer des combinaisons de différentes longueurs
        lengths = [3, 4, 5, 6, 7, 8]
        
        for _ in range(count):
            length = random.choice(lengths)
            # Générer un nom aléatoire
            name = ''.join(random.choice(chars) for _ in range(length))
            domains.add(name)
            
            # Ajouter des variantes avec tirets
            if length > 4:
                # Insérer un tiret
                pos = random.randint(1, length - 2)
                variant = name[:pos] + '-' + name[pos:]
                domains.add(variant)
        
        logger.info(f"Génération de {len(domains)} combinaisons aléatoires")
        return domains
    
    def generate_domains(self, max_domains: int = 20000) -> Set[str]:
        """
        Génère un grand nombre de domaines possibles.
        
        Args:
            max_domains: Nombre maximum de domaines à générer
        
        Returns:
            Set de domaines générés
        """
        logger.info(f"Génération de domaines Shopify possibles (objectif: {max_domains})")
        
        all_domains = set()
        
        # 1. Patterns communs
        common_domains = self._generate_common_patterns()
        all_domains.update(common_domains)
        logger.info(f"  → {len(all_domains)} domaines générés (patterns communs)")
        
        # 2. Combinaisons aléatoires pour atteindre l'objectif
        remaining = max_domains - len(all_domains)
        if remaining > 0:
            random_domains = self._generate_random_combinations(remaining)
            all_domains.update(random_domains)
            logger.info(f"  → {len(all_domains)} domaines générés au total")
        
        # Convertir en URLs
        shopify_urls = set()
        for domain in all_domains:
            # Nettoyer le domaine
            domain = domain.lower().strip()
            if domain and len(domain) >= 3:
                shopify_urls.add(f"https://{domain}.myshopify.com")
        
        logger.info(f"✓ {len(shopify_urls)} URLs Shopify générées")
        
        return shopify_urls



