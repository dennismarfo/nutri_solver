import streamlit as st
import pandas as pd
import json
import requests
import data_manager # Import des fonctions de gestion de données

# Constants
URL_ANALYSE_IA = 'https://n8n.srv775529.hstgr.cloud/webhook/analyze-meal'
URL_GENERATION_PDF = 'https://n8n.srv775529.hstgr.cloud/webhook/generation-plan'

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

# --- Sidebar : Profil & Besoins ---
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

# Formules BMR (Harris-Benedict)
st.sidebar.markdown("---")
st.sidebar.subheader("🧮 Calcul BMR (Harris-Benedict)")

if gender == "H":
    bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
else:
    bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

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

# Chargement des réglages praticien
settings = data_manager.get_settings()

# Système d'Onglets
tab_analyse, tab_config = st.tabs(["📊 Analyse de Repas", "⚙️ Configuration Praticien"])

with tab_analyse:
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
    st.subheader("🔎 Ajouter un aliment")
    
    # --- Integration AI ---
    with st.expander("🤖 Assistant IA (Décrire un repas)"):
        c_ai_1, c_ai_2 = st.columns([3, 1])
        with c_ai_1:
            ai_query = st.text_input("Description", placeholder="Ex: 'Un steak avec du riz'", key="ai_input")
        with c_ai_2:
            ai_meal_ctx = st.selectbox("Repas cible", ["Matin", "Midi", "Soir", "Collation"], key="ai_meal_ctx")
            
        if st.button("✨ Analyser et Ajouter", key="ai_btn"):
            if ai_query:
                with st.spinner("Analyse intelligente en cours..."):
                    try:
                        # 1. Chargement des réglages & Construction des règles
                        settings = data_manager.get_settings()
                        
                        # Création de la chaîne de règles (ex: 'Féculents: 150g, Viande: 125g')
                        rules_list = []
                        for k, v in settings.items():
                            # On ne garde que les portions (on exclut Eau et conseils)
                            if k not in ["Eau", "conseils_generaux"] and isinstance(v, (int, float)):
                                rules_list.append(f"{k}: {v}g")
                        nutrition_rules = ", ".join(rules_list)
                        
                        # 2. Envoi à n8n avec le nouveau format demandé
                        payload = {
                            "user_query": ai_query,
                            "meal_type": ai_meal_ctx,
                            "nutrition_rules": nutrition_rules
                        }
                        
                        # Appel Webhook
                        response = requests.post(URL_ANALYSE_IA, json=payload)
                        response.raise_for_status()
                        
                        raw_response = response.json()
                        
                        # 1. Extraction de la chaîne JSON depuis la réponse n8n
                        # Format attendu : [{ "output": "{'analyse': [...] }" }]
                        ai_output_str = "{}"
                        if isinstance(raw_response, list) and len(raw_response) > 0:
                            ai_output_str = raw_response[0].get("output", "{}")
                        elif isinstance(raw_response, dict):
                             ai_output_str = raw_response.get("output", "{}")
                            
                        # 2. Désérialisation avec json.loads
                        data = json.loads(ai_output_str)
                        
                        items_added = []
                        # 3. Mapping des résultats
                        if "analyse" in data:
                            for item in data["analyse"]:
                                new_food = {
                                    "meal": ai_meal_ctx,
                                    "name": item.get("aliment_reference", "Inconnu"),
                                    "qty": item.get("poids_g", 0),
                                    "calories": item.get("kcal_total", 0),
                                    "protein": item.get("prot", 0),
                                    "lipids": item.get("lip", 0),
                                    "carbs": item.get("gluc", 0),
                                    "group": item.get("categorie", "Autre"),
                                    # Calcul des valeurs pour 100g pour consistance avec le reste de l'app si nécessaire
                                    "data_per_100g": {
                                        "Energie_kcal_100g": (item.get("kcal_total", 0) / item.get("poids_g", 1) * 100) if item.get("poids_g", 0) > 0 else 0,
                                        "Proteines_Jones_g_100g": (item.get("prot", 0) / item.get("poids_g", 1) * 100) if item.get("poids_g", 0) > 0 else 0
                                    }
                                }
                                st.session_state.selected_foods.append(new_food)
                                items_added.append(f"{new_food['qty']}g {new_food['name']}")
                            
                            if items_added:
                                st.success(f"✅ Ajouté : {', '.join(items_added)}")
                                st.rerun()
                        else:
                            st.warning(f"L'IA n'a pas pu structurer les aliments. Réponse : {data}")
                            
                    except requests.exceptions.RequestException as e:
                        st.error(f"Erreur de connexion n8n : {e}")
                    except json.JSONDecodeError as e:
                        st.error(f"Erreur de lecture du JSON : {e}")
                    except Exception as e:
                        st.error(f"Une erreur inattendue est survenue : {e}")

    st.markdown("---")
    st.write("**Ou ajouter manuellement :**")

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
                # Récupération des conseils praticien
                current_settings = data_manager.get_settings()
                conseils = current_settings.get("conseils_generaux", "")
                
                payload = {
                    "client_ref": client_name,
                    "total_kcal": round(total_cals, 1),
                    "bmr": round(bmr, 1),
                    "tdee": round(tdee, 1),
                    "conseils_generaux": conseils, # Renommé pour correspondre à la demande
                    "repas": repas_list
                }
                
                response = requests.post(
                    URL_GENERATION_PDF, 
                    json=payload
                )
                
                if response.status_code == 200:
                    st.success("✅ Programme par Équivalences généré avec succès !")
                    st.balloons()
                else:
                    st.error(f"Erreur n8n : {response.text}")
            except Exception as e:
                st.error(f"Erreur de connexion : {e}")

with tab_config:
    st.subheader("⚙️ Configuration Praticien")
    st.info("Ici, vous pouvez définir vos portions de référence standards et vos conseils hydratation.")
    
    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Portions de Référence (en g)")
            # On charge les clés actuelles de settings mais on pourrait aussi hardcoder les champs demandés
            new_feculents = st.number_input("Portion Féculents (g)", value=settings.get("Féculents", 150), step=10)
            new_viande = st.number_input("Portion Viande (g)", value=settings.get("Viande", 125), step=10)
            new_poisson = st.number_input("Portion Poisson (g)", value=settings.get("Poisson", 150), step=10)
            
        with col2:
            st.markdown("### Autres")
            new_eau = st.number_input("Objectif Eau (L)", value=float(settings.get("Eau", 1.5)), step=0.1)
        
        st.markdown("### Conseils Généraux")
        default_conseils = "Boire régulièrement. Manger lentement dans le calme."
        new_conseils = st.text_area("Conseils à inclure dans les fiches", value=settings.get("conseils_generaux", default_conseils), height=100)

        submitted = st.form_submit_button("💾 Enregistrer les réglages")
        
        if submitted:
            # Création du dictionnaire à sauvegarder
            new_data = {
                "Féculents": new_feculents,
                "Viande": new_viande,
                "Poisson": new_poisson,
                "Eau": new_eau,
                "conseils_generaux": new_conseils
            }
            
            if data_manager.save_settings(new_data):
                st.success("Réglages enregistrés avec succès !")
                # Optionnel : Rerun pour mettre à jour immédiatement partout si besoin
                # st.rerun() 
            else:
                st.error("Erreur lors de l'enregistrement.")
