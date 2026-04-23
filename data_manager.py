import pandas as pd
import json
import os

SETTINGS_FILE = "settings.json"

# --- Paramètres par défaut enrichis (Programme Alimentaire) ---
DEFAULT_SETTINGS = {
    # Portions de référence par groupe (en grammes, sauf exception)
    "portions": {
        "proteines_viande": 125,
        "proteines_poisson": 150,
        "proteines_oeufs": 3,       # nombre d'œufs
        "feculents_cuits": 150,
        "legumes_cuits": 200,
        "legumes_crus": 150,
        "matieres_grasses_g": 10,   # 1½ càs d'huile (référence Tracy)
        "fruits": 100,              # grammes (~1 fruit)
        "legumineuses_cuites": 160,
        "oleagineux": 15,           # grammes (1 poignée)
        "pain": 50,                 # grammes
        "fromage_blanc": 100,       # grammes
    },
    # Options petit-déjeuner
    "options_pdj": [
        "100g fromage blanc/Skyr + 30-40g flocons d'avoine + 1 càs graines + 1 càs oléagineux + 1 fruit",
        "100g fromage blanc/Skyr + 50g granola + 1 fruit",
        "50g pain complet + 20g beurre de cacahuètes ou fromage frais + 1 fruit",
        "50g pain complet + 1 œuf (au plat, brouillé…) ou saumon/truite fumé + ½ avocat + 1 fruit",
        "1 viennoiserie ou brioche + 1 yaourt nature ou 100g fromage blanc + 2 càs mélange de graines (plaisir)"
    ],
    # Options collation
    "options_collation": [
        "1 fruit ou 100g compote + 1 poignée oléagineux (15g)",
        "1 fruit + 30g fromage",
        "1 fruit ou 100g compote + 125g yaourt nature/100g fromage blanc",
        "1 barre de céréales (aux noix)",
        "1 tranche pain (30g) + 1 càs fromage frais ou beurre de cacahuètes + 1 fruit",
        "100g fromage blanc + 2 càs muesli/granola aux noix",
        "2 biscuits secs ou 1 madeleine + 1 poignée graines ou 100g fromage blanc (1-2 fois max)"
    ],
    # Hydratation
    "hydratation": {
        "objectif_litres": 1.5,
        "max_cafe_the": 3,
        "repartition": "1 au réveil, 1 au PDJ, 2 dans la matinée, 1 à midi, 2 dans l'après-midi, 1 au dîner"
    },
    # Fréquences protéines
    "frequences_proteines": {
        "viandes_blanches": "5 fois/semaine",
        "viandes_rouges": "max 2 fois/semaine",
        "poissons": "2-3 fois/semaine dont poissons gras 2 fois",
        "oeufs": "min 3-4 fois/semaine",
        "vegetarien": "min 3-4 fois/semaine"
    },
    # Conseils généraux
    "conseils_generaux": """- Prendre au moins 20 minutes pour manger son repas.
- Éviter de manger 2-3h avant de vous coucher.
- Boire min. 1.5-2L par jour.
- 2 fruits par jour (entier, sec, compote).
- Varier vos huiles végétales.
- Limiter les produits gras/frits à 2-3 fois par semaine.
- Limiter les produits sucrés à 2-3 fois par semaine.
- 1 carré de chocolat noir par jour autorisé.
- Diversifier vos aliments au cours de la semaine."""
}

# --- Équivalences de référence par groupe ---
EQUIVALENCES = {
    "Féculents": {
        "ref_aliment": "Riz cuit",
        "ref_kcal_100g": 130,
        "alternatives": [
            {"nom": "Pâtes cuites", "kcal_100g": 131},
            {"nom": "Semoule/Couscous cuit", "kcal_100g": 112},
            {"nom": "Quinoa cuit", "kcal_100g": 120},
            {"nom": "Pommes de terre cuites", "kcal_100g": 80},
            {"nom": "Patate douce cuite", "kcal_100g": 86},
            {"nom": "Pain complet", "kcal_100g": 250},
            {"nom": "Boulgour cuit", "kcal_100g": 83},
            {"nom": "Polenta", "kcal_100g": 70},
            {"nom": "Gnocchi", "kcal_100g": 133},
            {"nom": "Banane plantain cuite", "kcal_100g": 122},
            {"nom": "Igname cuit", "kcal_100g": 116},
        ]
    },
    "Protéines": {
        "ref_aliment": "Poulet (blanc)",
        "ref_kcal_100g": 110,
        "alternatives": [
            {"nom": "Dinde", "kcal_100g": 104},
            {"nom": "Bœuf (5% MG)", "kcal_100g": 137},
            {"nom": "Veau", "kcal_100g": 143},
            {"nom": "Saumon", "kcal_100g": 208},
            {"nom": "Cabillaud/Colin", "kcal_100g": 80},
            {"nom": "Thon conserve", "kcal_100g": 116},
            {"nom": "Maquereau", "kcal_100g": 205},
            {"nom": "Crevettes", "kcal_100g": 99},
            {"nom": "Œufs (2 unités ~120g)", "kcal_100g": 140},
            {"nom": "Tofu", "kcal_100g": 76},
            {"nom": "Tempeh", "kcal_100g": 192},
        ]
    },
    "Légumes": {
        "ref_aliment": "Haricots verts cuits",
        "ref_kcal_100g": 30,
        "alternatives": [
            {"nom": "Brocoli cuit", "kcal_100g": 34},
            {"nom": "Carottes cuites", "kcal_100g": 27},
            {"nom": "Courgettes cuites", "kcal_100g": 17},
            {"nom": "Épinards cuits", "kcal_100g": 23},
            {"nom": "Poivrons cuits", "kcal_100g": 21},
            {"nom": "Aubergine cuite", "kcal_100g": 25},
            {"nom": "Chou-fleur cuit", "kcal_100g": 23},
            {"nom": "Tomates cuites", "kcal_100g": 18},
            {"nom": "Poireaux cuits", "kcal_100g": 24},
            {"nom": "Champignons cuits", "kcal_100g": 22},
        ]
    },
    "Légumineuses": {
        "ref_aliment": "Lentilles cuites",
        "ref_kcal_100g": 115,
        "alternatives": [
            {"nom": "Pois chiches cuits", "kcal_100g": 164},
            {"nom": "Haricots rouges cuits", "kcal_100g": 127},
            {"nom": "Haricots blancs cuits", "kcal_100g": 139},
            {"nom": "Pois cassés cuits", "kcal_100g": 118},
            {"nom": "Fèves cuites", "kcal_100g": 88},
            {"nom": "Edamame", "kcal_100g": 122},
            {"nom": "Flageolets cuits", "kcal_100g": 98},
        ]
    },
    "Matières Grasses": {
        "ref_aliment": "Huile (olive, colza, tournesol, noix, coco, avocat, noisette)",
        "ref_portion_g": 10,
        "ref_kcal_100g": 900,
        "use_explicit_weights": True,
        "alternatives": [
            {"nom": "Beurre ou margarine", "poids_g": 12, "kcal_100g": 750},
            {"nom": "Crème 15% (1½ càs)", "poids_g": 22, "kcal_100g": 155},
            {"nom": "Mayonnaise", "poids_g": 14, "kcal_100g": 680},
            {"nom": "Avocat (⅓)", "poids_g": 50, "kcal_100g": 160},
        ]
    },
    "Fruits": {
        "ref_aliment": "Pomme (~150g)",
        "ref_kcal_100g": 52,
        "alternatives": [
            {"nom": "Banane (~120g)", "kcal_100g": 89},
            {"nom": "Orange (~200g)", "kcal_100g": 47},
            {"nom": "Poire (~160g)", "kcal_100g": 57},
            {"nom": "Kiwi (2 petits ~150g)", "kcal_100g": 61},
            {"nom": "Fraises (7-8 ~150g)", "kcal_100g": 32},
            {"nom": "Raisins (10-15 ~100g)", "kcal_100g": 67},
            {"nom": "Mangue (½ ~150g)", "kcal_100g": 60},
            {"nom": "Clémentines (2 ~150g)", "kcal_100g": 47},
            {"nom": "Ananas (¼ ~150g)", "kcal_100g": 50},
        ]
    },
    "Produits Laitiers": {
        "ref_aliment": "Fromage blanc 0%",
        "ref_kcal_100g": 48,
        "alternatives": [
            {"nom": "Yaourt nature", "kcal_100g": 50},
            {"nom": "Skyr", "kcal_100g": 63},
            {"nom": "Yaourt grecque", "kcal_100g": 97},
            {"nom": "Petits-suisses (2)", "kcal_100g": 110},
            {"nom": "Fromage - Comté (30g)", "kcal_100g": 410},
            {"nom": "Fromage - Mozzarella (30g)", "kcal_100g": 280},
        ]
    },
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
        df = pd.read_excel(file_path)
        
        rename_map = {
            'alim_nom_fr': 'name',
            'alim_grp_nom_fr': 'ciqual_group',
            'Energie,\nRèglement\nUE N°\n1169\n2011 (kcal\n100 g)': 'kcal',
            'Protéines,\nN x\nfacteur de\nJones (g\n100 g)': 'prot',
            'Glucides\n(g\n100 g)': 'carb',
            'Lipides\n(g\n100 g)': 'lip'
        }
        
        cols_to_rename = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=cols_to_rename)
        
        expected_cols = ['name', 'kcal', 'prot', 'carb', 'lip', 'ciqual_group']
        
        for col in expected_cols:
            if col not in df.columns:
                df[col] = "Inconnu" if col in ['name', 'ciqual_group'] else 0.0

        df = df[expected_cols]

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
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                # Merge avec les défauts pour garantir que toutes les clés existent
                merged = DEFAULT_SETTINGS.copy()
                merged.update(saved)
                return merged
        except json.JSONDecodeError:
            print("Erreur de lecture du fichier settings.json. Utilisation des défauts.")
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()


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


def generate_equivalences(groupe, portion_g):
    """
    Génère la table d'équivalences pour un groupe alimentaire donné et une portion de référence.
    Retourne une liste de dicts : [{nom, poids_equivalent_g, kcal}]
    """
    if groupe not in EQUIVALENCES:
        return []

    group_data = EQUIVALENCES[groupe]
    ref_kcal_100g = group_data["ref_kcal_100g"]
    portion_kcal = (ref_kcal_100g * portion_g) / 100

    results = [{
        "nom": f"{group_data['ref_aliment']} (réf.)",
        "poids_g": round(portion_g, 1),
        "kcal": round(portion_kcal)
    }]

    if group_data.get("use_explicit_weights"):
        # Règles cliniques fournies par la praticienne : on n'applique PAS
        # la proportionnalité kcal (sinon 58g de crème 15% au lieu de 22g).
        # On scale uniquement si la portion de réf est modifiée.
        ref_portion_g = group_data.get("ref_portion_g") or portion_g
        scale = portion_g / ref_portion_g if ref_portion_g else 1.0
        for alt in group_data["alternatives"]:
            poids = alt["poids_g"] * scale
            kcal = round((alt["kcal_100g"] * poids) / 100) if alt.get("kcal_100g") else 0
            results.append({
                "nom": alt["nom"],
                "poids_g": round(poids, 1),
                "kcal": kcal
            })
    else:
        for alt in group_data["alternatives"]:
            if alt["kcal_100g"] > 0:
                poids_equiv = (portion_kcal * 100) / alt["kcal_100g"]
                poids_equiv = round(poids_equiv / 5) * 5
                results.append({
                    "nom": alt["nom"],
                    "poids_g": poids_equiv,
                    "kcal": round((alt["kcal_100g"] * poids_equiv) / 100)
                })

    return results


# --- Fonctions de calcul BMR ---
def calc_bmr_harris_benedict(gender, weight, height_cm, age):
    """Harris-Benedict (révisé 1984)"""
    if gender == "H":
        return 88.362 + (13.397 * weight) + (4.799 * height_cm) - (5.677 * age)
    else:
        return 447.593 + (9.247 * weight) + (3.098 * height_cm) - (4.330 * age)


def calc_bmr_black(gender, weight, height_cm, age):
    """Black et al (1996) — résultat en MJ converti en kcal"""
    height_m = height_cm / 100
    if gender == "H":
        bmr_mj = 1.083 * (weight ** 0.48) * (height_m ** 0.50) * (age ** -0.13)
    else:
        bmr_mj = 0.963 * (weight ** 0.48) * (height_m ** 0.50) * (age ** -0.13)
    return bmr_mj * 239  # 1 MJ ≈ 239 kcal


def calc_bmr_muller(gender, weight, age, body_fat_pct):
    """Muller — nécessite le % de masse grasse"""
    fm = weight * (body_fat_pct / 100)  # Fat Mass
    lbm = weight - fm                    # Lean Body Mass
    sex_val = 1 if gender == "H" else 0
    return (13.587 * lbm) + (9.613 * fm) + (198 * sex_val) - (3.351 * age) + 674
