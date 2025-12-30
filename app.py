import streamlit as st
import pandas as pd
import json
import requests

# Configuration de la page
st.set_page_config(
    page_title="NutriSolver",
    page_icon="🥗",
    layout="wide"
)

# Styles CSS personnalisés pour un look premium
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .metric-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #41444e;
    }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# Chargement des données
@st.cache_data
def load_data():
    try:
        # Load Excel file
        # The header is on the first row (index 0)
        df = pd.read_excel("Ciqual.xlsx")
        
        # Rename columns to match the app's expected format
        # We map the complex Excel headers to simple keys
        column_mapping = {
            'alim_nom_fr': 'alim_nom_fr',
            'Energie,\nRèglement\nUE N°\n1169\n2011 (kcal\n100 g)': 'Energie_kcal_100g',
            'Protéines,\nN x\nfacteur de\nJones (g\n100 g)': 'Proteines_Jones_g_100g',
            'Glucides\n(g\n100 g)': 'Glucides_g_100g',
            'Lipides\n(g\n100 g)': 'Lipides_g_100g'
        }
        
        # Check if columns exist (handling potential variations)
        # We only keep the columns we need
        available_cols = [c for c in column_mapping.keys() if c in df.columns]
        if len(available_cols) < 5:
            # Fallback or error if columns are missing/different
            st.warning(f"Certaines colonnes attendues sont manquantes. Colonnes trouvées : {list(df.columns)}")
        
        df = df.rename(columns=column_mapping)
        
        # Filter to keep only necessary columns
        cols_to_keep = list(column_mapping.values())
        # Ensure we only keep columns that actually exist after renaming
        cols_to_keep = [c for c in cols_to_keep if c in df.columns]
        df = df[cols_to_keep]
        
        # Data cleaning function
        def clean_val(x):
            if pd.isna(x): return 0.0
            if isinstance(x, (int, float)): return float(x)
            if isinstance(x, str):
                x = x.strip()
                if x == '-' or x == 'traces': return 0.0
                if x.startswith('<'):
                    x = x.replace('<', '').strip()
                return float(x.replace(',', '.'))
            return 0.0

        # Apply cleaning to numeric columns
        numeric_cols = ['Energie_kcal_100g', 'Proteines_Jones_g_100g', 'Glucides_g_100g', 'Lipides_g_100g']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(clean_val)
                
        return df
    except FileNotFoundError:
        st.error("Fichier Ciqual.xlsx introuvable. Veuillez le placer dans le répertoire du projet.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return pd.DataFrame()

df = load_data()

# Initialisation du Session State
if 'selected_foods' not in st.session_state:
    st.session_state.selected_foods = []

# --- Sidebar : Objectifs ---
# --- Sidebar : Calculateur de Besoins ---
st.sidebar.header("👤 Profil & Besoins")
client_name = st.sidebar.text_input("Nom du Client", value="Client 1")

# Paramètres physiologiques
col_g, col_a = st.sidebar.columns(2)
gender = col_g.radio("Sexe", ["H", "F"], horizontal=True)
age = col_a.number_input("Age", 15, 100, 30)

col_w, col_h = st.sidebar.columns(2)
weight = col_w.number_input("Poids (kg)", 30.0, 200.0, 70.0, step=0.5)
height = col_h.number_input("Taille (cm)", 100, 250, 175)

activity_map = {
    "Sédentaire (1.2)": 1.2,
    "Légèrement actif (1.375)": 1.375,
    "Modérément actif (1.55)": 1.55,
    "Très actif (1.725)": 1.725,
    "Extrêmement actif (1.9)": 1.9
}
activity_label = st.sidebar.selectbox("Activité", list(activity_map.keys()), index=2)
activity_factor = activity_map[activity_label]

# Formules BMR
st.sidebar.markdown("---")
st.sidebar.subheader("🧮 Calcul BMR")
formula_option = st.sidebar.radio("Formule", ["Mifflin-St Jeor", "Katch-McArdle", "Cunningham"])

bmr = 0.0
# Logic for Body Fat
if formula_option in ["Katch-McArdle", "Cunningham"]:
    body_fat = st.sidebar.number_input("Masse Grasse (%)", 0.0, 60.0, 15.0, step=0.5)
    lbm = weight * (1 - body_fat / 100)
    
    if formula_option == "Katch-McArdle":
        bmr = 370 + (21.6 * lbm)
    else: # Cunningham
        bmr = 500 + (22 * lbm)
else:
    # Mifflin-St Jeor
    base_mifflin = (10 * weight) + (6.25 * height) - (5 * age)
    if gender == "H":
        bmr = base_mifflin + 5
    else:
        bmr = base_mifflin - 161

tdee = bmr * activity_factor

st.sidebar.info(f"**BMR :** {int(bmr)} kcal\n\n**TDEE :** {int(tdee)} kcal")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Objectifs Cibles")

# On pré-remplit avec le TDEE calculé
target_cals = st.sidebar.number_input("Calories (kcal)", min_value=0, value=int(tdee), step=50)
target_prot = st.sidebar.number_input("Protéines (g)", min_value=0, value=180, step=5)
target_lip = st.sidebar.number_input("Lipides (g)", min_value=0, value=80, step=5)
target_carb = st.sidebar.number_input("Glucides (g)", min_value=0, value=300, step=5)

# --- Main Content ---
st.title("🥗 NutriSolver : Calculateur Inversé")

# --- Données de Référence pour les Équivalences ---
# Structure : Groupe -> {keywords: [...], refs: [(Nom, Kcal/100g), ...]}
EQUIVALENCE_GROUPS = {
    "Féculents": {
        "keywords": ["riz", "pâte", "pate", "pomme de terre", "semoule", "blé", "pain", "quinoa", "lentille", "pois", "haricot rouge", "fève", "igname", "patate douce", "boulgour", "maïs", "flocon"],
        "refs": [
            ("Riz cuit", 130),
            ("Pâtes cuites", 110),
            ("Pommes de terre", 85),
            ("Patate douce", 86),
            ("Pain complet", 240),
            ("Lentilles cuites", 115),
            ("Quinoa cuit", 120),
            ("Banane plantain", 120)
        ]
    },
    "Viandes/Poissons/Oeufs": {
        "keywords": ["poulet", "boeuf", "veau", "porc", "agneau", "dinde", "canard", "steak", "jambon", "poisson", "saumon", "thon", "colin", "cabillaud", "crevette", "oeuf", "merlu", "sardine", "maquereau"],
        "refs": [
            ("Poulet (blanc)", 110),
            ("Boeuf (5% MG)", 125),
            ("Saumon", 200),
            ("Oeufs (2 unités)", 140),
            ("Thon conserve", 110),
            ("Cabillaud", 80),
            ("Tofu", 76)
        ]
    },
    "Légumes": {
        "keywords": ["tomate", "carotte", "courgette", "haricot vert", "brocoli", "chou", "épinard", "poivron", "salade", "aubergine", "concombre", "radis", "poireau", "champignon"],
        "refs": [
            ("Haricots verts", 30),
            ("Carottes cuites", 35),
            ("Brocoli", 34),
            ("Courgettes", 17),
            ("Salade verte", 15)
        ]
    },
    "Fruits": {
        "keywords": ["pomme", "banane", "orange", "poire", "fraise", "framboise", "myrtille", "kiwi", "raisin", "pêche", "abricot", "ananas", "mangue", "clémentine"],
        "refs": [
            ("Pomme", 52),
            ("Banane", 89),
            ("Orange", 47),
            ("Kiwi", 61),
            ("Raisins", 67)
        ]
    },
    "Matières Grasses": {
        "keywords": ["huile", "beurre", "margarine", "avocat", "amande", "noix", "cacahuète", "cajou", "pistache", "mayonnaise", "vinaigrette"],
        "refs": [
            ("Huile d'olive (1 c.à.s)", 90), # ~10g
            ("Beurre (10g)", 75),
            ("Avocat", 160),
            ("Amandes", 600),
            ("Noix", 650)
        ]
    },
    "Produits Laitiers": {
        "keywords": ["lait", "yaourt", "fromage", "crème", "skyr", "faisselle", "blanc", "petit suisse"],
        "refs": [
            ("Lait demi-écrémé (ml)", 46),
            ("Yaourt nature", 50),
            ("Fromage blanc 0%", 48),
            ("Mozzarella", 280),
            ("Comté", 410)
        ]
    }
}

def detect_group(food_name):
    """Détermine le groupe d'aliment basé sur le nom."""
    name_lower = food_name.lower()
    for group, data in EQUIVALENCE_GROUPS.items():
        for kw in data['keywords']:
            if kw in name_lower:
                return group
    return "Autre"

def generate_equivalence_string(group, target_kcal, current_food_name):
    """Génère la chaîne de texte pour les équivalences."""
    if group not in EQUIVALENCE_GROUPS or group == "Autre":
        return ""
    
    refs = EQUIVALENCE_GROUPS[group]['refs']
    equivs = []
    
    for ref_name, ref_kcal_100g in refs:
        # On ne compare pas l'aliment avec lui-même (approximativement)
        if ref_name.lower() in current_food_name.lower() or current_food_name.lower() in ref_name.lower():
            continue
            
        # Règle de trois calorique
        # Poids équivalent = (Cibles Kcal * 100) / Kcal réf
        if ref_kcal_100g > 0:
            weight = (target_kcal * 100) / ref_kcal_100g
            # Arrondi joli (ex: 233 -> 230)
            weight = round(weight / 5) * 5 
            equivs.append(f"{int(weight)}g {ref_name}")
    
    if not equivs:
        return ""
        
    return "Ou environ : " + " / ".join(equivs[:4]) # On limite à 4 suggestions pour la lisibilité

# 1. Search & Add
st.subheader("🔎 Ajouter un aliment (Programme Équivalences)")

if not df.empty:
    col_search, col_meal, col_qty, col_add = st.columns([2, 1, 1, 1])
    
    with col_search:
        food_options = df['alim_nom_fr'].tolist()
        selected_food_name = st.selectbox("Rechercher un aliment", options=[""] + food_options)
        
        # Feedback immédiat sur le groupe détecté
        if selected_food_name:
            detected_grp = detect_group(selected_food_name)
            st.caption(f"Groupe détecté : **{detected_grp}**")
    
    with col_meal:
        meal_type = st.selectbox("Repas", ["Matin", "Midi", "Soir", "Collation"])

    with col_qty:
        qty = st.number_input("Quantité (g)", min_value=0, value=100, step=10)
        
    with col_add:
        st.write("") # Spacer
        st.write("") # Spacer
        if st.button("Ajouter", type="primary"):
            if selected_food_name:
                food_data = df[df['alim_nom_fr'] == selected_food_name].iloc[0]
                item_group = detect_group(selected_food_name)
                
                item = {
                    "meal": meal_type,
                    "name": selected_food_name,
                    "group": item_group, # Stockage du groupe
                    "qty": qty,
                    "protein": (food_data['Proteines_Jones_g_100g'] * qty) / 100,
                    "lipids": (food_data['Lipides_g_100g'] * qty) / 100,
                    "carbs": (food_data['Glucides_g_100g'] * qty) / 100,
                    "calories": (food_data['Energie_kcal_100g'] * qty) / 100,
                    "data_per_100g": food_data.to_dict()
                }
                st.session_state.selected_foods.append(item)
                st.rerun()

# 2. Liste des aliments sélectionnés
if st.session_state.selected_foods:
    st.subheader("📋 Plan par Équivalences")
    
    for i, item in enumerate(st.session_state.selected_foods):
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 3, 1, 1, 1, 1, 1])
        c1.write(f"**{item.get('meal', 'N/A')}**")
        
        # Affichage enrichi avec le groupe
        grp_display = f" ({item.get('group', '?')})" if item.get('group') != "Autre" else ""
        c2.markdown(f"**{item['name']}**{grp_display}")
        
        c2.caption(f"Cible : {item['qty']}g ({int(item['calories'])} kcal)")
        
        c3.write(f"{item['protein']:.1f}g P")
        c4.write(f"{item['lipids']:.1f}g L")
        c5.write(f"{item['carbs']:.1f}g G")
        
        if c7.button("🗑️", key=f"del_{i}"):
            st.session_state.selected_foods.pop(i)
            st.rerun()

# 3. Calculs des Totaux
total_cals = sum(item['calories'] for item in st.session_state.selected_foods)
total_prot = sum(item['protein'] for item in st.session_state.selected_foods)
total_lip = sum(item['lipids'] for item in st.session_state.selected_foods)
total_carb = sum(item['carbs'] for item in st.session_state.selected_foods)

# 4. Jauges / Métriques
st.subheader("📊 Avancement")
m1, m2, m3, m4 = st.columns(4)

def get_delta_color(current, target):
    return "normal" if current <= target else "inverse"

m1.metric("Calories", f"{total_cals:.0f} / {target_cals}", delta=f"{total_cals - target_cals:.0f}", delta_color=get_delta_color(total_cals, target_cals))
m2.metric("Protéines", f"{total_prot:.1f} / {target_prot}g", delta=f"{total_prot - target_prot:.1f}g", delta_color=get_delta_color(total_prot, target_prot))
m3.metric("Lipides", f"{total_lip:.1f} / {target_lip}g", delta=f"{total_lip - target_lip:.1f}g", delta_color=get_delta_color(total_lip, target_lip))
m4.metric("Glucides", f"{total_carb:.1f} / {target_carb}g", delta=f"{total_carb - target_carb:.1f}g", delta_color=get_delta_color(total_carb, target_carb))

st.progress(min(total_cals / target_cals if target_cals > 0 else 0, 1.0), text="Calories")
st.progress(min(total_prot / target_prot if target_prot > 0 else 0, 1.0), text="Protéines")

# 5. Solver
st.subheader("🧮 Solver : Combler les Protéines")
if not df.empty:
    c_sol_food, c_sol_meal = st.columns([3, 1])
    with c_sol_food:
        solver_food = st.selectbox("Choisir un aliment combler", options=[""] + df['alim_nom_fr'].tolist(), key="solver_select")
    with c_sol_meal:
        solver_meal = st.selectbox("Repas cible", ["Collation", "Matin", "Midi", "Soir"], key="solver_meal")
    
    if st.button("Calculer et Ajouter"):
        if solver_food:
            remaining_prot = target_prot - total_prot
            if remaining_prot <= 0:
                st.warning("Objectif de protéines déjà atteint !")
            else:
                food_data = df[df['alim_nom_fr'] == solver_food].iloc[0]
                prot_per_100 = food_data['Proteines_Jones_g_100g']
                
                if prot_per_100 > 0:
                    needed_qty = (remaining_prot * 100) / prot_per_100
                    
                    item = {
                        "meal": solver_meal,
                        "name": solver_food,
                        "group": detect_group(solver_food),
                        "qty": round(needed_qty, 1),
                        "protein": remaining_prot,
                        "lipids": (food_data['Lipides_g_100g'] * needed_qty) / 100,
                        "carbs": (food_data['Glucides_g_100g'] * needed_qty) / 100,
                        "calories": (food_data['Energie_kcal_100g'] * needed_qty) / 100,
                        "data_per_100g": food_data.to_dict()
                    }
                    st.session_state.selected_foods.append(item)
                    st.success(f"Ajouté : {needed_qty:.1f}g de {solver_food}")
                    st.rerun()
                else:
                    st.error("Pas de protéines dans cet aliment.")

# 6. Export
st.subheader("📤 Validation du Plan avec Équivalences")
if st.button("🚀 Valider et Générer le PDF"):
    # Group foods by meal
    meals_dict = {}
    for item in st.session_state.selected_foods:
        m_name = item.get('meal', 'Autre')
        if m_name not in meals_dict:
            meals_dict[m_name] = []
        
        # Generation de la chaîne d'équivalence
        eq_text = generate_equivalence_string(item.get('group', 'Autre'), item['calories'], item['name'])
        
        food_entry = {
            "nom": item['name'],
            "poids": item['qty'],
            "groupe": item.get('group', 'Autre'),
            "equivalences": eq_text, # Nouvelle clé
            "prot": round(item['protein'], 1),
            "lip": round(item['lipids'], 1),
            "gluc": round(item['carbs'], 1),
            "kcal": round(item['calories'], 1)
        }
        meals_dict[m_name].append(food_entry)
    
    # Construct final list
    repas_list = []
    meal_order = ["Matin", "Midi", "Collation", "Soir"]
    for m in meal_order:
        if m in meals_dict:
            repas_list.append({
                "nom": m,
                "aliments": meals_dict[m]
            })
            del meals_dict[m]
    for m, foods in meals_dict.items():
        repas_list.append({
            "nom": m,
            "aliments": foods
        })

    with st.spinner('Orchestration des équivalences...'):
        try:
            payload = {
                "client_ref": client_name,
                "total_kcal": round(total_cals, 1),
                "bmr": round(bmr, 1), # Ajout contextuel
                "tdee": round(tdee, 1), # Ajout contextuel
                "repas": repas_list
            }
            
            response = requests.post(
                "https://n8n.srv775529.hstgr.cloud/webhook/generation-plan", 
                json=payload
            )
            
            if response.status_code == 200:
                st.success("✅ Programme par Équivalences généré avec succès !")
                st.balloons()
            else:
                st.error(f"Erreur n8n : {response.text}")
        except Exception as e:
            st.error(f"Erreur de connexion : {e}")
