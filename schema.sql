-- Schéma de base de données pour le projet de scraping Shopify
-- 
-- Ce script crée la table nécessaire pour stocker les informations
-- de contact extraites des sites Shopify.

-- Créer la table shopify_contacts
CREATE TABLE IF NOT EXISTS shopify_contacts (
    id SERIAL PRIMARY KEY,
    url VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255),
    phone_number VARCHAR(50),
    contact_page_url VARCHAR(255),
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Créer un index sur l'URL pour améliorer les performances de recherche
CREATE INDEX IF NOT EXISTS idx_shopify_contacts_url ON shopify_contacts(url);

-- Créer un index sur la date de scraping pour faciliter les requêtes temporelles
CREATE INDEX IF NOT EXISTS idx_shopify_contacts_scraped_at ON shopify_contacts(scraped_at);

-- Commentaires sur les colonnes
COMMENT ON TABLE shopify_contacts IS 'Table stockant les informations de contact extraites des sites Shopify';
COMMENT ON COLUMN shopify_contacts.id IS 'Identifiant unique auto-incrémenté';
COMMENT ON COLUMN shopify_contacts.url IS 'URL du domaine Shopify (unique)';
COMMENT ON COLUMN shopify_contacts.email IS 'Adresse e-mail extraite de la page de contact';
COMMENT ON COLUMN shopify_contacts.phone_number IS 'Numéro de téléphone extrait de la page de contact';
COMMENT ON COLUMN shopify_contacts.contact_page_url IS 'URL de la page de contact utilisée pour le scraping';
COMMENT ON COLUMN shopify_contacts.scraped_at IS 'Date et heure du scraping (avec fuseau horaire)';

