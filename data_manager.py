import pandas as pd
import json
import os

SETTINGS_FILE = "settings.json"

# Mapping des groupes Ciqual vers les groupes "Tracy" (Familles logiques pour les régimes)
# Basé sur les catégories standards Ciqual
CIQUAL_TO_TRACY_MAP = {
    "entrées et plats composés": "Plats Composés",
    "fruits, légumes, légumineuses et oléagineux": "Légumes/Fruits",
    "produits céréaliers": "Féculents",
    "viandes, œufs, poissons": "Protéines (V/P/O)",
    "lait et produits laitiers": "Produits Laitiers",
    "boissons": "Boissons",
    "matières grasses": "Matières Grasses",
    "produits sucrés": "Produits Sucrés",
    "glaces et sorbets": "Produits Sucrés",
    "aides culinaires et ingrédients divers": "Condiments/Divers",
    "aliments infantiles": "Divers"
}

def load_and_clean_ciqual(file_path="Ciqual.xlsx"):
    """
    Charge le fichier Ciqual, renomme les colonnes et nettoie les données.
    Retourne un DataFrame avec les colonnes: name, kcal, prot, carb, lip, ciqual_group
    """
    if not os.path.exists(file_path):
        print(f"Fichier non trouvé: {file_path}")
        return pd.DataFrame()

    try:
        # Lecture du fichier Excel
        df = pd.read_excel(file_path)
        
        # Dictionnaire de renommage aligné sur la demande
        # Attention aux sauts de ligne dans les headers Excel Ciqual originaux
        rename_map = {
            'alim_nom_fr': 'name',
            'alim_grp_nom_fr': 'ciqual_group',
            'Energie,\nRèglement\nUE N°\n1169\n2011 (kcal\n100 g)': 'kcal',
            'Protéines,\nN x\nfacteur de\nJones (g\n100 g)': 'prot',
            'Glucides\n(g\n100 g)': 'carb',
            'Lipides\n(g\n100 g)': 'lip'
        }
        
        # Filtrage et renommage des colonnes existantes
        # On utilise une compréhension de dictionnaire pour ne mapper que ce qui existe
        cols_to_rename = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=cols_to_rename)
        
        # Liste des colonnes attendues en sortie
        expected_cols = ['name', 'kcal', 'prot', 'carb', 'lip', 'ciqual_group']
        
        # Assurer que toutes les colonnes existent, sinon les initialiser
        for col in expected_cols:
            if col not in df.columns:
                # Si ciqual_group manque, on met "Inconnu", sinon 0 pour les valeurs numériques
                df[col] = "Inconnu" if col in ['name', 'ciqual_group'] else 0.0

        # On ne garde que les colonnes utiles
        df = df[expected_cols]

        # Fonction de nettoyage (similaire à app.py mais réutilisable)
        def clean_val(x):
            if pd.isna(x): return 0.0
            if isinstance(x, (int, float)): return float(x)
            if isinstance(x, str):
                x = x.strip()
                if x in ['-', 'traces']: return 0.0
                if x.startswith('<'):
                    x = x.replace('<', '').strip()
                try:
                    return float(x.replace(',', '.'))
                except ValueError:
                    return 0.0
            return 0.0

        # Application du nettoyage sur les colonnes numériques
        for col in ['kcal', 'prot', 'carb', 'lip']:
            df[col] = df[col].apply(clean_val)
            
        return df

    except Exception as e:
        print(f"Erreur critique lors du chargement des données Ciqual: {e}")
        return pd.DataFrame()

def get_settings():
    """
    Récupère les paramètres depuis le fichier JSON ou retourne les valeurs par défaut.
    """
    default_settings = {
        "Féculents": 150,
        "Viande": 125,
        "Poisson": 150,
        "Eau": 1.5
    }
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Erreur de lecture du fichier settings.json (corrompu). Utilisation des défauts.")
            return default_settings
    return default_settings

def save_settings(data):
    """
    Sauvegarde les paramètres fournis dans le fichier JSON.
    """
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des settings : {e}")
        return False
