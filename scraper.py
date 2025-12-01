"""
Script de scraping des pages de contact Shopify.

Ce script lit le fichier domains_to_scrape.txt, visite chaque page de contact,
extrait les adresses e-mail et numéros de téléphone, puis stocke les données
dans une base de données PostgreSQL.
"""

import os
import re
import time
import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse
from pathlib import Path

# Charger les variables d'environnement
BASE_DIR = Path(__file__).parent
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path), override=True)
else:
    load_dotenv(override=True)

# Configuration
INPUT_FILE = 'domains_to_scrape.txt'
MAX_RETRIES = 3
RETRY_DELAY = 2  # secondes
REQUEST_TIMEOUT = 10  # secondes
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Configuration de la base de données
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'shopify_scraper'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


# Expressions régulières pour l'extraction
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    re.IGNORECASE
)

# Pattern pour numéros de téléphone (international et français)
PHONE_PATTERN = re.compile(
    r'(?:\+33|0)[1-9](?:[.\s-]?\d{2}){4}|'  # Format français
    r'\+?[1-9]\d{1,4}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}'  # Format international
)


def get_db_connection():
    """
    Établit une connexion à la base de données PostgreSQL.
    
    Returns:
        Objet de connexion psycopg2
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"✗ Erreur de connexion à la base de données: {e}")
        raise


def normalize_domain(domain: str) -> str:
    """
    Normalise un domaine en ajoutant le protocole si nécessaire.
    
    Args:
        domain: Le domaine à normaliser
        
    Returns:
        Le domaine normalisé avec https://
    """
    domain = domain.strip()
    if not domain.startswith(('http://', 'https://')):
        domain = f'https://{domain}'
    return domain


def get_contact_page_url(domain: str) -> Optional[str]:
    """
    Détermine l'URL de la page de contact pour un domaine donné.
    Essaie d'abord /pages/contact, puis /contact en cas d'échec.
    
    Args:
        domain: Le domaine à tester
        
    Returns:
        L'URL de la page de contact si trouvée, None sinon
    """
    domain = normalize_domain(domain)
    
    # Liste des URLs à essayer dans l'ordre de priorité
    contact_urls = [
        f'{domain}/pages/contact',
        f'{domain}/contact',
        f'{domain}/pages/contact-us',
        f'{domain}/contact-us'
    ]
    
    headers = {'User-Agent': USER_AGENT}
    
    for url in contact_urls:
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True
                )
                
                # Accepte 200, 301, 302 (redirections)
                if response.status_code in [200, 301, 302]:
                    # Suivre la redirection finale si nécessaire
                    if response.status_code in [301, 302]:
                        final_url = response.url
                    else:
                        final_url = url
                    return final_url
                    
            except requests.exceptions.Timeout:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
            except requests.exceptions.RequestException:
                # Erreur de réseau, passer à l'URL suivante
                break
            except Exception as e:
                print(f"    ⚠ Erreur lors de la vérification de {url}: {e}")
                break
    
    return None


def extract_email(text: str) -> Optional[str]:
    """
    Extrait la première adresse e-mail valide du texte.
    
    Args:
        text: Le texte à analyser
        
    Returns:
        La première adresse e-mail trouvée ou None
    """
    # Exclure les emails génériques/non pertinents
    excluded_domains = [
        'example.com', 'test.com', 'domain.com', 'email.com',
        'sentry.io', 'shopify.com', 'facebook.com', 'twitter.com',
        'instagram.com', 'pinterest.com', 'youtube.com'
    ]
    
    matches = EMAIL_PATTERN.findall(text)
    
    for email in matches:
        email_lower = email.lower()
        # Vérifier que l'email n'est pas dans la liste d'exclusion
        if not any(excluded in email_lower for excluded in excluded_domains):
            return email
    
    return None


def extract_phone(text: str) -> Optional[str]:
    """
    Extrait le premier numéro de téléphone valide du texte.
    
    Args:
        text: Le texte à analyser
        
    Returns:
        Le premier numéro de téléphone trouvé ou None
    """
    matches = PHONE_PATTERN.findall(text)
    
    for phone in matches:
        # Nettoyer le numéro
        phone_clean = re.sub(r'[\s.\-()]', '', phone)
        # Vérifier qu'il a une longueur raisonnable (au moins 10 chiffres)
        if len(re.sub(r'\D', '', phone_clean)) >= 10:
            return phone.strip()
    
    return None


def scrape_contact_page(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Scrape une page de contact et extrait l'email et le téléphone.
    
    Args:
        url: L'URL de la page de contact
        
    Returns:
        Un tuple (email, phone) ou (None, None) en cas d'erreur
    """
    headers = {'User-Agent': USER_AGENT}
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Parser le HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraire le texte de la page
            # Supprimer les scripts et styles pour éviter les faux positifs
            for script in soup(['script', 'style', 'noscript']):
                script.decompose()
            
            page_text = soup.get_text()
            
            # Extraire email et téléphone
            email = extract_email(page_text)
            phone = extract_phone(page_text)
            
            return email, phone
            
        except requests.exceptions.HTTPError as e:
            if response.status_code >= 500:
                # Erreur serveur, réessayer
                if attempt < MAX_RETRIES - 1:
                    print(f"    ⚠ Erreur serveur {response.status_code}, nouvelle tentative...")
                    time.sleep(RETRY_DELAY)
                    continue
            else:
                # Erreur client (404, etc.), ne pas réessayer
                break
                
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                print(f"    ⚠ Timeout, nouvelle tentative...")
                time.sleep(RETRY_DELAY)
                continue
            break
            
        except requests.exceptions.RequestException as e:
            print(f"    ✗ Erreur de requête: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            break
            
        except Exception as e:
            print(f"    ✗ Erreur inattendue: {e}")
            break
    
    return None, None


def save_to_database(domain: str, email: Optional[str], phone: Optional[str], 
                     contact_url: Optional[str]) -> bool:
    """
    Sauvegarde les données extraites dans la base de données.
    
    Args:
        domain: Le domaine scrappé
        email: L'adresse e-mail extraite
        phone: Le numéro de téléphone extrait
        contact_url: L'URL de la page de contact
        
    Returns:
        True si l'insertion a réussi, False sinon
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Utiliser ON CONFLICT pour éviter les doublons
        query = """
            INSERT INTO shopify_contacts (url, email, phone_number, contact_page_url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            RETURNING id;
        """
        
        cursor.execute(query, (domain, email, phone, contact_url))
        
        if cursor.fetchone():
            conn.commit()
            cursor.close()
            conn.close()
            return True
        else:
            # Pas d'insertion (doublon)
            conn.rollback()
            cursor.close()
            conn.close()
            return False
            
    except psycopg2.Error as e:
        print(f"    ✗ Erreur lors de l'insertion en base: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False


def process_domain(domain: str) -> None:
    """
    Traite un domaine: trouve la page de contact, scrape et sauvegarde.
    
    Args:
        domain: Le domaine à traiter
    """
    print(f"  Traitement de: {domain}")
    
    # Trouver la page de contact
    contact_url = get_contact_page_url(domain)
    
    if not contact_url:
        print(f"    ✗ Aucune page de contact trouvée")
        # Sauvegarder quand même le domaine (sans email/phone)
        save_to_database(domain, None, None, None)
        return
    
    print(f"    ✓ Page de contact trouvée: {contact_url}")
    
    # Scraper la page
    email, phone = scrape_contact_page(contact_url)
    
    # Afficher les résultats
    results = []
    if email:
        results.append(f"Email: {email}")
    if phone:
        results.append(f"Téléphone: {phone}")
    
    if results:
        print(f"    ✓ Données extraites: {', '.join(results)}")
    else:
        print(f"    ⚠ Aucune donnée de contact trouvée")
    
    # Sauvegarder en base
    if save_to_database(domain, email, phone, contact_url):
        print(f"    ✓ Données sauvegardées en base")
    else:
        print(f"    ⚠ Données non sauvegardées (doublon ou erreur)")


def main():
    """Point d'entrée principal du script."""
    # Vérifier que le fichier d'entrée existe
    if not os.path.exists(INPUT_FILE):
        print(f"✗ Fichier {INPUT_FILE} introuvable!")
        print(f"  Veuillez d'abord exécuter discover.py pour générer ce fichier.")
        return
    
    # Lire les domaines
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        domains = [line.strip() for line in f if line.strip()]
    
    if not domains:
        print(f"✗ Aucun domaine trouvé dans {INPUT_FILE}")
        return
    
    print(f"Démarrage du scraping de {len(domains)} domaine(s)...")
    print(f"Base de données: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}\n")
    
    # Vérifier la connexion à la base de données
    try:
        conn = get_db_connection()
        conn.close()
        print("✓ Connexion à la base de données réussie\n")
    except Exception as e:
        print(f"✗ Impossible de se connecter à la base de données: {e}")
        return
    
    # Traiter chaque domaine
    for i, domain in enumerate(domains, 1):
        print(f"[{i}/{len(domains)}]")
        process_domain(domain)
        print()
        
        # Pause entre les requêtes pour éviter la surcharge
        if i < len(domains):
            time.sleep(1)
    
    print("✓ Scraping terminé!")


if __name__ == '__main__':
    main()

