"""
Vérification du respect de robots.txt.
"""

import urllib.robotparser
from urllib.parse import urlparse
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Vérifie si une URL est autorisée selon robots.txt."""
    
    def __init__(self):
        self.parsers = {}  # Cache des parsers robots.txt par domaine
    
    def can_fetch(self, url: str, user_agent: str = '*') -> bool:
        """
        Vérifie si une URL peut être scrapée selon robots.txt.
        
        Args:
            url: URL à vérifier
            user_agent: User-Agent à utiliser
        
        Returns:
            True si autorisé, False sinon
        """
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = f"{base_url}/robots.txt"
            
            # Récupérer ou créer le parser pour ce domaine
            if base_url not in self.parsers:
                rp = urllib.robotparser.RobotFileParser()
                rp.set_url(robots_url)
                try:
                    rp.read()
                    self.parsers[base_url] = rp
                    logger.debug(f"robots.txt chargé pour {base_url}")
                except Exception as e:
                    logger.warning(f"Impossible de charger robots.txt pour {base_url}: {e}")
                    # Si on ne peut pas charger robots.txt, on autorise par défaut
                    return True
            
            parser = self.parsers[base_url]
            can_fetch = parser.can_fetch(user_agent, url)
            
            if not can_fetch:
                logger.warning(f"URL bloquée par robots.txt: {url}")
            
            return can_fetch
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification robots.txt pour {url}: {e}")
            # En cas d'erreur, on autorise par défaut (mais on log l'erreur)
            return True

