"""
Module de gestion des données (sauvegarde, chargement)
"""
import json
import csv
import os
from typing import List, Dict
from datetime import datetime
import pandas as pd

from config import OUTPUT_DIR, RESULTS_FILE, CSV_FILE


class DataManager:
    """Classe pour gérer la sauvegarde et le chargement des données"""
    
    def __init__(self):
        self.ensure_output_dir()
    
    def ensure_output_dir(self):
        """Crée le dossier de sortie s'il n'existe pas"""
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
    
    def save_to_json(self, data: List[Dict], filename: str = None):
        """
        Sauvegarde les données en JSON
        
        Args:
            data: Liste de dictionnaires à sauvegarder
            filename: Nom du fichier (utilise RESULTS_FILE par défaut)
        """
        if filename is None:
            filename = RESULTS_FILE
        
        filepath = os.path.join(OUTPUT_DIR, filename) if not filename.startswith(OUTPUT_DIR) else filename
        
        # Ajouter la date de sauvegarde
        output_data = {
            'date_export': datetime.now().isoformat(),
            'total_sites': len(data),
            'sites': data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Données sauvegardées dans {filepath} ({len(data)} sites)")
    
    def save_to_csv(self, data: List[Dict], filename: str = None):
        """
        Sauvegarde les données en CSV
        
        Args:
            data: Liste de dictionnaires à sauvegarder
            filename: Nom du fichier (utilise CSV_FILE par défaut)
        """
        if filename is None:
            filename = CSV_FILE
        
        filepath = os.path.join(OUTPUT_DIR, filename) if not filename.startswith(OUTPUT_DIR) else filename
        
        if not data:
            print("Aucune donnée à sauvegarder")
            return
        
        # Créer un DataFrame
        df = pd.DataFrame(data)
        
        # Sauvegarder en CSV
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        print(f"Données sauvegardées dans {filepath} ({len(data)} sites)")
    
    def load_from_json(self, filename: str = None) -> List[Dict]:
        """
        Charge les données depuis un fichier JSON
        
        Args:
            filename: Nom du fichier (utilise RESULTS_FILE par défaut)
            
        Returns:
            Liste de dictionnaires
        """
        if filename is None:
            filename = RESULTS_FILE
        
        filepath = os.path.join(OUTPUT_DIR, filename) if not filename.startswith(OUTPUT_DIR) else filename
        
        if not os.path.exists(filepath):
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Retourner les sites si la structure contient 'sites', sinon retourner les données directement
        if isinstance(data, dict) and 'sites' in data:
            return data['sites']
        
        return data if isinstance(data, list) else []
    
    def merge_data(self, new_data: List[Dict], existing_file: str = None) -> List[Dict]:
        """
        Fusionne de nouvelles données avec des données existantes
        
        Args:
            new_data: Nouvelles données à ajouter
            existing_file: Fichier existant à fusionner
            
        Returns:
            Liste fusionnée et dédupliquée
        """
        existing_data = self.load_from_json(existing_file) if existing_file else []
        
        # Créer un set d'URLs existantes pour la déduplication
        existing_urls = {item.get('url', '') for item in existing_data}
        
        # Ajouter seulement les nouvelles URLs
        merged_data = existing_data.copy()
        
        for item in new_data:
            url = item.get('url', '')
            if url and url not in existing_urls:
                merged_data.append(item)
                existing_urls.add(url)
        
        return merged_data
    
    def export_statistics(self, data: List[Dict], filename: str = None):
        """
        Exporte des statistiques sur les données
        
        Args:
            data: Liste de dictionnaires
            filename: Nom du fichier de sortie
        """
        if filename is None:
            filename = os.path.join(OUTPUT_DIR, 'statistics.txt')
        
        stats = {
            'total_sites': len(data),
            'verified_shopify': sum(1 for item in data if item.get('verified', False)),
            'with_title': sum(1 for item in data if item.get('title')),
            'with_description': sum(1 for item in data if item.get('description')),
            'myshopify_domains': sum(1 for item in data if 'myshopify.com' in item.get('url', ''))
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== STATISTIQUES DES SITES SHOPIFY ===\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for key, value in stats.items():
                f.write(f"{key}: {value}\n")
        
        print(f"Statistiques exportées dans {filename}")

