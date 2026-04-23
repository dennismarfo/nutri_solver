import streamlit as st
import pandas as pd
import json
import requests
import data_manager
import pdf_generator

# Constants
URL_ANALYSE_IA = 'https://n8n.srv775529.hstgr.cloud/webhook/analyze-meal'

# Configuration de la page
st.set_page_config(
    page_title="NutriSolver",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styles CSS personnalisés (Thème Clair Tricky Nutrition)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&display=swap');

    .stApp {
        background-color: #FFFFFF;
        color: #2D2D2D;
        font-family: 'Montserrat', sans-serif;
    }
    h1, h2, h3 {
        font-family: 'Playfair Display', serif;
        color: #00A651 !important;
    }
    .metric-card {
        background-color: #F8F9FA;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E0E0E0;
    }
    .stButton>button {
        width: 100%;
        border-radius: 30px;
        font-weight: 700;
        font-family: 'Montserrat', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1px;
        background-color: #00A651 !important;
        color: #FFFFFF !important;
        border: none !important;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #2DB35D !important;
        color: #FFFFFF !important;
    }
    .equiv-table {
        background-color: #F8F9FA;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid #E0E0E0;
    }
    .section-header {
        color: #00A651;
        font-weight: 700;
        font-family: 'Playfair Display', serif;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        background-color: #F8F9FA;
    }
    div[data-testid="stSidebar"] {
        background-color: #F8F9FA;
        border-right: 1px solid #E0E0E0;
    }
    div[data-testid="stMetricValue"] {
        color: #00A651;
    }
    </style>
    """, unsafe_allow_html=True)

# Chargement des données Ciqual
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("Ciqual.xlsx")
        column_mapping = {
            'alim_nom_fr': 'alim_nom_fr',
            'Energie,\nRèglement\nUE N°\n1169\n2011 (kcal\n100 g)': 'Energie_kcal_100g',
            'Protéines,\nN x\nfacteur de\nJones (g\n100 g)': 'Proteines_Jones_g_100g',
            'Glucides\n(g\n100 g)': 'Glucides_g_100g',
            'Lipides\n(g\n100 g)': 'Lipides_g_100g'
        }
        df = df.rename(columns=column_mapping)
        cols_to_keep = [c for c in column_mapping.values() if c in df.columns]
        df = df[cols_to_keep]

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

        numeric_cols = ['Energie_kcal_100g', 'Proteines_Jones_g_100g', 'Glucides_g_100g', 'Lipides_g_100g']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(clean_val)
        return df
    except FileNotFoundError:
        st.error("Fichier Ciqual.xlsx introuvable.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return pd.DataFrame()

df = load_data()

# ============================================================
# SIDEBAR : Profil & BMR
# ============================================================
st.sidebar.header("👤 Profil du Patient")
client_name = st.sidebar.text_input("Nom du Patient", value="Patient 1")

# Paramètres physiologiques
col_g, col_a = st.sidebar.columns(2)
gender = col_g.radio("Sexe", ["H", "F"], horizontal=True)
age = col_a.number_input("Âge", 15, 100, 30)

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

# --- Sélection de la formule BMR ---
st.sidebar.markdown("---")
st.sidebar.subheader("🧮 Calcul du Métabolisme de Base")

bmr_formula = st.sidebar.selectbox(
    "Formule",
    ["Harris-Benedict", "Black et al (1996)", "Muller"],
    index=0
)

body_fat_pct = None
if bmr_formula == "Muller":
    body_fat_pct = st.sidebar.number_input(
        "Masse grasse (%)", min_value=5.0, max_value=60.0, value=25.0, step=0.5,
        help="Nécessaire pour la formule de Muller"
    )

# Calcul du BMR selon la formule choisie
if bmr_formula == "Harris-Benedict":
    bmr = data_manager.calc_bmr_harris_benedict(gender, weight, height, age)
elif bmr_formula == "Black et al (1996)":
    bmr = data_manager.calc_bmr_black(gender, weight, height, age)
elif bmr_formula == "Muller":
    bmr = data_manager.calc_bmr_muller(gender, weight, age, body_fat_pct)

tdee = bmr * activity_factor

st.sidebar.info(f"**Formule :** {bmr_formula}\n\n**BMR :** {int(bmr)} kcal\n\n**TDEE :** {int(tdee)} kcal")

# Objectifs cibles
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Objectifs Cibles")
target_cals = st.sidebar.number_input("Calories (kcal)", min_value=0, value=int(tdee), step=50)

# ============================================================
# MAIN CONTENT
# ============================================================
st.title("🥗 NutriSolver")
st.caption("Générateur de Programme Alimentaire par Équivalences")

# Chargement des réglages praticien
settings = data_manager.get_settings()
portions = settings.get("portions", data_manager.DEFAULT_SETTINGS["portions"])

# Système d'Onglets
tab_programme, tab_ia, tab_config = st.tabs([
    "📋 Programme Alimentaire",
    "🤖 Assistant IA",
    "⚙️ Configuration Praticien"
])

# ============================================================
# TAB 1 : PROGRAMME ALIMENTAIRE
# ============================================================
with tab_programme:

    # --- Section Objectifs ---
    st.subheader("🎯 Objectifs du Programme")
    
    # Objectifs par défaut modifiables
    if 'objectifs' not in st.session_state:
        st.session_state.objectifs = [
            "Rééquilibrer l'alimentation en gardant les 3 groupes alimentaires à chaque repas",
            "Manger à bonne quantité - suivre le programme",
            "Prendre le temps pour manger (environ 15-20 minutes)",
            f"Boire suffisamment d'eau min {settings.get('hydratation', {}).get('objectif_litres', 1.5)}L",
            "Prendre une collation équilibrée"
        ]
    
    objectifs_text = st.text_area(
        "Objectifs personnalisés pour le patient",
        value="\n".join(st.session_state.objectifs),
        height=120
    )
    st.session_state.objectifs = [o.strip() for o in objectifs_text.split("\n") if o.strip()]

    st.markdown("---")

    # --- Section Répartition Macro-Nutriments ---
    st.subheader("🎯 Répartition Macro-Nutriments")
    st.caption(
        "Cibles cliniques Tracy (perte de poids) : protéines 1,2-1,5 g/kg · "
        "lipides ≤ 33-34 % · glucides ≥ 40 %."
    )

    default_macros = settings.get("macros_cibles", data_manager.DEFAULT_SETTINGS["macros_cibles"])

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        patient_prot_ratio = st.number_input(
            "Protéines (g/kg)",
            min_value=0.6, max_value=2.5,
            value=float(default_macros.get("proteines_g_par_kg", 1.3)),
            step=0.1, key="patient_prot_ratio"
        )
    with col_m2:
        patient_lip_pct = st.number_input(
            "Lipides (% kcal)",
            min_value=15, max_value=50,
            value=int(default_macros.get("lipides_pct", 30)),
            step=1, key="patient_lip_pct"
        )
    with col_m3:
        patient_glu_min = st.number_input(
            "Glucides min (% kcal)",
            min_value=20, max_value=70,
            value=int(default_macros.get("glucides_pct_min", 40)),
            step=1, key="patient_glu_min"
        )

    patient_ratios = {
        "proteines_g_par_kg": patient_prot_ratio,
        "lipides_pct": patient_lip_pct,
        "glucides_pct_min": patient_glu_min,
    }
    macros = data_manager.compute_macros_targets(weight, target_cals, patient_ratios)

    df_macros = pd.DataFrame([
        {"Macro": "Protéines", "Grammes": f"{macros['proteines']['g']:.1f} g",
         "% kcal": f"{macros['proteines']['pct']:.1f} %", "Kcal": macros['proteines']['kcal']},
        {"Macro": "Lipides", "Grammes": f"{macros['lipides']['g']:.1f} g",
         "% kcal": f"{macros['lipides']['pct']:.1f} %", "Kcal": macros['lipides']['kcal']},
        {"Macro": "Glucides", "Grammes": f"{macros['glucides']['g']:.1f} g",
         "% kcal": f"{macros['glucides']['pct']:.1f} %", "Kcal": macros['glucides']['kcal']},
    ])
    st.dataframe(df_macros, use_container_width=True, hide_index=True)

    if macros["warnings"]:
        for w in macros["warnings"]:
            st.warning(f"⚠️ {w}")
    else:
        st.success("✅ Répartition cohérente avec les cibles cliniques.")

    st.markdown("---")

    # --- Section Petit-Déjeuner ---
    st.subheader("🌅 Petit-Déjeuner")
    
    options_pdj = settings.get("options_pdj", data_manager.DEFAULT_SETTINGS["options_pdj"])
    
    st.write("**Options au choix pour varier :**")
    
    # Permettre de sélectionner/désélectionner les options PDJ
    selected_pdj = []
    for i, opt in enumerate(options_pdj):
        label = f"Option {i+1}" + (" (plaisir)" if i == len(options_pdj)-1 else "")
        if st.checkbox(label, value=True, key=f"pdj_{i}"):
            selected_pdj.append(opt)
        st.caption(f"  → {opt}")
    
    st.info("💡 Ces options peuvent être à emporter. Les options \"plaisir\" doivent être occasionnelles.")
    
    st.markdown("---")
    
    # --- Section Déjeuner ---
    st.subheader("🍽️ Déjeuner")
    st.write("**Composer l'assiette avec UN composant de chaque groupe :**")
    
    # Protéines
    with st.expander("🥩 Protéines", expanded=True):
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            portion_viande = st.number_input(
                "Portion viande (g)", 
                value=int(portions.get("proteines_viande", 125)), 
                step=5, key="dej_viande"
            )
            portion_poisson = st.number_input(
                "Portion poisson (g)", 
                value=int(portions.get("proteines_poisson", 150)), 
                step=5, key="dej_poisson"
            )
            portion_oeufs = st.number_input(
                "Nombre d'œufs", 
                value=int(portions.get("proteines_oeufs", 3)), 
                step=1, key="dej_oeufs"
            )
        with col_p2:
            st.write("**Table d'équivalences protéines**")
            equiv_prot = data_manager.generate_equivalences("Protéines", portion_viande)
            if equiv_prot:
                df_equiv_p = pd.DataFrame(equiv_prot)
                df_equiv_p.columns = ["Aliment", "Poids (g)", "Kcal"]
                st.dataframe(df_equiv_p, use_container_width=True, hide_index=True)
    
    # Féculents
    with st.expander("🍚 Féculents", expanded=True):
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            portion_feculents = st.number_input(
                "Portion féculents cuits (g)", 
                value=int(portions.get("feculents_cuits", 150)), 
                step=10, key="dej_feculents"
            )
        with col_f2:
            st.write("**Table d'équivalences féculents**")
            equiv_fec = data_manager.generate_equivalences("Féculents", portion_feculents)
            if equiv_fec:
                df_equiv_f = pd.DataFrame(equiv_fec)
                df_equiv_f.columns = ["Aliment", "Poids (g)", "Kcal"]
                st.dataframe(df_equiv_f, use_container_width=True, hide_index=True)
    
    # Légumes
    with st.expander("🥦 Légumes", expanded=True):
        col_l1, col_l2 = st.columns([1, 2])
        with col_l1:
            portion_legumes = st.number_input(
                "Portion légumes cuits (g)", 
                value=int(portions.get("legumes_cuits", 200)), 
                step=10, key="dej_legumes"
            )
            portion_crudites = st.number_input(
                "Portion crudités (g)", 
                value=int(portions.get("legumes_crus", 150)), 
                step=10, key="dej_crudites"
            )
        with col_l2:
            st.write("**Table d'équivalences légumes**")
            equiv_leg = data_manager.generate_equivalences("Légumes", portion_legumes)
            if equiv_leg:
                df_equiv_l = pd.DataFrame(equiv_leg)
                df_equiv_l.columns = ["Aliment", "Poids (g)", "Kcal"]
                st.dataframe(df_equiv_l, use_container_width=True, hide_index=True)
    
    # Matières grasses
    with st.expander("🫒 Matières Grasses", expanded=True):
        col_mg1, col_mg2 = st.columns([1, 2])
        with col_mg1:
            portion_mg = st.number_input(
                "Portion huile (g)",
                value=int(portions.get("matieres_grasses_g", 10)),
                step=1, key="dej_mg",
                help="Référence : 10 g = 1½ càs d'huile"
            )
        with col_mg2:
            st.write("**Table d'équivalences matières grasses**")
            equiv_mg = data_manager.generate_equivalences("Matières Grasses", portion_mg)
            if equiv_mg:
                df_equiv_mg = pd.DataFrame(equiv_mg)
                df_equiv_mg.columns = ["Aliment", "Poids (g)", "Kcal"]
                st.dataframe(df_equiv_mg, use_container_width=True, hide_index=True)
        st.caption("Pour la cuisson ou l'assaisonnement. Varier vos huiles (olive, colza, coco, noix...).")
    
    # Dessert
    st.write("**Dessert :** + 1 fruit 🍎")
    
    st.markdown("---")
    
    # --- Section Collation ---
    st.subheader("☕ Collation - Après-midi")
    
    options_collation = settings.get("options_collation", data_manager.DEFAULT_SETTINGS["options_collation"])
    
    selected_collation = []
    for i, opt in enumerate(options_collation):
        if st.checkbox(f"Option {i+1}", value=True, key=f"col_{i}"):
            selected_collation.append(opt)
        st.caption(f"  → {opt}")
    
    st.info("☕ Accompagner votre collation d'une boisson chaude (thé, tisane sans sucre) ou d'eau.")
    
    st.markdown("---")
    
    # --- Section Dîner ---
    st.subheader("🌙 Dîner")
    st.write("**Même structure que le déjeuner (portions ajustables) :**")
    
    # Protéines Dîner
    with st.expander("🥩 Protéines (Dîner)", expanded=True):
        col_dp1, col_dp2 = st.columns([1, 2])
        with col_dp1:
            diner_portion_viande = st.number_input(
                "Portion viande (g)", 
                value=int(portions.get("proteines_viande", 125)), 
                step=5, key="din_viande"
            )
        with col_dp2:
            st.write("**Équivalences protéines**")
            equiv_prot_d = data_manager.generate_equivalences("Protéines", diner_portion_viande)
            if equiv_prot_d:
                df_ep_d = pd.DataFrame(equiv_prot_d)
                df_ep_d.columns = ["Aliment", "Poids (g)", "Kcal"]
                st.dataframe(df_ep_d, use_container_width=True, hide_index=True)
    
    # Féculents Dîner
    with st.expander("🍚 Féculents (Dîner)", expanded=True):
        col_df1, col_df2 = st.columns([1, 2])
        with col_df1:
            diner_portion_feculents = st.number_input(
                "Portion féculents cuits (g)", 
                value=int(portions.get("feculents_cuits", 150)), 
                step=10, key="din_feculents"
            )
        with col_df2:
            st.write("**Équivalences féculents**")
            equiv_fec_d = data_manager.generate_equivalences("Féculents", diner_portion_feculents)
            if equiv_fec_d:
                df_ef_d = pd.DataFrame(equiv_fec_d)
                df_ef_d.columns = ["Aliment", "Poids (g)", "Kcal"]
                st.dataframe(df_ef_d, use_container_width=True, hide_index=True)
    
    # Légumes Dîner
    with st.expander("🥦 Légumes (Dîner)"):
        st.write(f"**Portion recommandée :** {int(portions.get('legumes_cuits', 200))}g cuits ou {int(portions.get('legumes_crus', 150))}g crudités ou 250-300ml soupe")
    
    # Matières grasses Dîner
    with st.expander("🫒 Matières Grasses (Dîner)", expanded=True):
        col_dmg1, col_dmg2 = st.columns([1, 2])
        with col_dmg1:
            diner_portion_mg = st.number_input(
                "Portion huile (g)",
                value=int(portions.get("matieres_grasses_g", 10)),
                step=1, key="din_mg",
                help="Référence : 10 g = 1½ càs d'huile"
            )
        with col_dmg2:
            st.write("**Équivalences matières grasses**")
            equiv_mg_d = data_manager.generate_equivalences("Matières Grasses", diner_portion_mg)
            if equiv_mg_d:
                df_emg_d = pd.DataFrame(equiv_mg_d)
                df_emg_d.columns = ["Aliment", "Poids (g)", "Kcal"]
                st.dataframe(df_emg_d, use_container_width=True, hide_index=True)
    
    st.write("**Dessert :** + 100g fromage blanc/Skyr/yaourt grecque/2 petits-suisses")
    
    st.markdown("---")
    
    # --- Section Répartition Assiette ---
    st.subheader("🍽️ Répartition de l'assiette")
    col_rep1, col_rep2 = st.columns(2)
    with col_rep1:
        st.markdown("""
        **Option 1 :**
        - ½ assiette → Légumes
        - ¼ assiette → Féculents
        - ¼ assiette → Protéines
        """)
    with col_rep2:
        st.markdown("""
        **Option 2 :**
        - ⅓ assiette → Légumes
        - ⅓ assiette → Féculents
        - ⅓ assiette → Protéines
        """)
    
    st.markdown("---")
    
    # --- Section Hydratation ---
    st.subheader("💧 Hydratation")
    hydratation = settings.get("hydratation", data_manager.DEFAULT_SETTINGS["hydratation"])
    st.write(f"**Objectif :** Boire au moins {hydratation.get('objectif_litres', 1.5)}-2L par jour")
    st.write(f"**Répartition :** {hydratation.get('repartition', '')}")
    st.write(f"**Café/Thé noir :** Limiter à {hydratation.get('max_cafe_the', 3)} tasses par jour. Privilégier tisanes et infusions.")
    
    st.markdown("---")
    
    # --- Section Listes de Référence ---
    st.subheader("📖 Listes de Référence")
    
    with st.expander("🥜 Légumineuses"):
        equiv_leg_sec = data_manager.generate_equivalences("Légumineuses", int(portions.get("legumineuses_cuites", 160)))
        if equiv_leg_sec:
            df_ls = pd.DataFrame(equiv_leg_sec)
            df_ls.columns = ["Aliment", "Poids (g)", "Kcal"]
            st.dataframe(df_ls, use_container_width=True, hide_index=True)
        st.caption("Note : bien les tremper si secs (min 8h). En conserve, bien les rincer.")
    
    with st.expander("🌰 Oléagineux & Graines"):
        st.markdown("""
        **Fruits à coque (grillés, sans sel) :**
        Amande, Noix, Noix de pécan, Noisette, Noix de macadamia, Pistache, Noix de cajou, Noix de Brésil, Châtaigne
        
        **Graines :**
        Tournesol, Courge, Lin (broyé avant consommation), Chia, Chanvre
        """)
    
    with st.expander("🍎 Fruits - Équivalences"):
        st.markdown("""
        **1 fruit ≈ 100g** = 1 pomme, 1 poire, 1 banane, 2 clémentines, 1 orange, 
        10-15 raisins, 3 abricots, 2 kiwis, 7-8 fraises, 10-15 framboises, 
        ¼ ananas, ½ mangue, 1 tranche pastèque, 2-3 figues, 15 cerises
        """)
        st.caption("Pour les fruits séchés : même quantité en frais que séché.")
    
    with st.expander("🥛 Produits Laitiers"):
        equiv_lait = data_manager.generate_equivalences("Produits Laitiers", int(portions.get("fromage_blanc", 100)))
        if equiv_lait:
            df_lait = pd.DataFrame(equiv_lait)
            df_lait.columns = ["Aliment", "Poids (g)", "Kcal"]
            st.dataframe(df_lait, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # --- Section Fréquences + Conseils ---
    st.subheader("📝 Conseils Généraux")
    
    # Fréquences protéines
    with st.expander("🔄 Fréquences Protéines"):
        freq = settings.get("frequences_proteines", data_manager.DEFAULT_SETTINGS["frequences_proteines"])
        freq_data = [
            {"Type": "Viandes blanches", "Fréquence": freq.get("viandes_blanches", "5 fois/semaine")},
            {"Type": "Viandes rouges", "Fréquence": freq.get("viandes_rouges", "max 2 fois/semaine")},
            {"Type": "Poissons", "Fréquence": freq.get("poissons", "2-3 fois/semaine")},
            {"Type": "Œufs", "Fréquence": freq.get("oeufs", "min 3-4 fois/semaine")},
            {"Type": "Végétarien", "Fréquence": freq.get("vegetarien", "min 3-4 fois/semaine")},
        ]
        st.dataframe(pd.DataFrame(freq_data), use_container_width=True, hide_index=True)
    
    # Conseils
    conseils = settings.get("conseils_generaux", data_manager.DEFAULT_SETTINGS["conseils_generaux"])
    st.text_area("Conseils à inclure dans le programme", value=conseils, height=200, key="conseils_display", disabled=True)
    
    st.markdown("---")
    
    # --- GÉNÉRATION DU PDF ---
    st.subheader("📤 Générer le Programme Alimentaire")
    
    # Construction du payload
    payload = {
        "client_ref": client_name,
        "bmr": round(bmr, 1),
        "tdee": round(tdee, 1),
        "formule_bmr": bmr_formula,
        "objectifs": st.session_state.objectifs,
        "macros": macros,
        "poids_kg": weight,
        "petit_dejeuner": {
            "options": selected_pdj
        },
        "dejeuner": {
            "proteines": {
                "portion_viande_g": portion_viande,
                "portion_poisson_g": portion_poisson,
                "portion_oeufs": portion_oeufs,
                "equivalences": data_manager.generate_equivalences("Protéines", portion_viande)
            },
            "feculents": {
                "portion_g": portion_feculents,
                "equivalences": data_manager.generate_equivalences("Féculents", portion_feculents)
            },
            "legumes": {
                "portion_cuits_g": portion_legumes,
                "portion_crudites_g": portion_crudites,
                "equivalences": data_manager.generate_equivalences("Légumes", portion_legumes)
            },
            "matieres_grasses": {
                "portion_g": portion_mg,
                "equivalences": data_manager.generate_equivalences("Matières Grasses", portion_mg)
            },
            "dessert": "1 fruit"
        },
        "collation": {
            "options": selected_collation
        },
        "diner": {
            "proteines": {
                "portion_viande_g": diner_portion_viande,
                "equivalences": data_manager.generate_equivalences("Protéines", diner_portion_viande)
            },
            "feculents": {
                "portion_g": diner_portion_feculents,
                "equivalences": data_manager.generate_equivalences("Féculents", diner_portion_feculents)
            },
            "legumes": {
                "portion_cuits_g": int(portions.get("legumes_cuits", 200)),
                "portion_crudites_g": int(portions.get("legumes_crus", 150)),
            },
            "matieres_grasses": {
                "portion_g": diner_portion_mg,
                "equivalences": data_manager.generate_equivalences("Matières Grasses", diner_portion_mg)
            },
            "dessert": "100g fromage blanc/Skyr/yaourt grecque"
        },
        "hydratation": hydratation,
        "frequences_proteines": freq,
        "conseils_generaux": conseils,
        "listes_reference": {
            "legumineuses": data_manager.generate_equivalences("Légumineuses", int(portions.get("legumineuses_cuites", 160))),
            "fruits_equivalences": "1 fruit ≈ 100g = 1 pomme, 1 poire, 1 banane, 2 clémentines, 1 orange, 10-15 raisins, etc."
        }
    }
    
    if st.button("🚀 Générer le PDF", type="primary"):
        with st.spinner("Génération du programme alimentaire..."):
            try:
                pdf_bytes = bytes(pdf_generator.generate_programme_pdf(payload))
                st.session_state.pdf_data = pdf_bytes
                st.session_state.pdf_filename = f"Programme_Alimentaire_{client_name.replace(' ', '_')}.pdf"
                st.success("✅ Programme Alimentaire généré avec succès !")
                st.balloons()
            except Exception as e:
                st.error(f"Erreur lors de la génération : {e}")
    
    # Bouton de téléchargement (persiste après génération)
    if 'pdf_data' in st.session_state and st.session_state.pdf_data:
        st.download_button(
            label="📥 Télécharger le PDF",
            data=st.session_state.pdf_data,
            file_name=st.session_state.pdf_filename,
            mime="application/pdf",
            type="primary"
        )


# ============================================================
# TAB 2 : ASSISTANT IA
# ============================================================
with tab_ia:
    st.subheader("🤖 Assistant IA - Idées de Repas")
    st.write("Décrivez un repas ou une idée et l'IA vous proposera une analyse nutritionnelle.")
    
    c_ai_1, c_ai_2 = st.columns([3, 1])
    with c_ai_1:
        ai_query = st.text_input("Description", placeholder="Ex: 'Un steak avec du riz et des haricots verts'", key="ai_input")
    with c_ai_2:
        ai_meal_ctx = st.selectbox("Repas cible", ["Matin", "Midi", "Soir", "Collation"], key="ai_meal_ctx")

    if st.button("✨ Analyser", key="ai_btn"):
        if ai_query:
            with st.spinner("Analyse intelligente en cours..."):
                try:
                    current_settings = data_manager.get_settings()
                    rules_list = []
                    for k, v in current_settings.get("portions", {}).items():
                        if isinstance(v, (int, float)):
                            rules_list.append(f"{k}: {v}g")
                    nutrition_rules = ", ".join(rules_list)
                    
                    payload = {
                        "user_query": ai_query,
                        "meal_type": ai_meal_ctx,
                        "nutrition_rules": nutrition_rules
                    }
                    
                    response = requests.post(URL_ANALYSE_IA, json=payload)
                    response.raise_for_status()
                    
                    raw_response = response.json()
                    
                    ai_output_str = "{}"
                    if isinstance(raw_response, list) and len(raw_response) > 0:
                        ai_output_str = raw_response[0].get("output", "{}")
                    elif isinstance(raw_response, dict):
                        ai_output_str = raw_response.get("output", "{}")
                    
                    data = json.loads(ai_output_str)
                    
                    if "analyse" in data:
                        st.success("✅ Analyse terminée :")
                        for item in data["analyse"]:
                            st.write(f"- **{item.get('aliment_reference', 'Inconnu')}** : "
                                     f"{item.get('poids_g', 0)}g "
                                     f"({item.get('kcal_total', 0)} kcal, "
                                     f"P:{item.get('prot', 0)}g, "
                                     f"L:{item.get('lip', 0)}g, "
                                     f"G:{item.get('gluc', 0)}g)")
                    else:
                        st.warning(f"L'IA n'a pas pu structurer les aliments. Réponse : {data}")
                        
                except requests.exceptions.RequestException as e:
                    st.error(f"Erreur de connexion n8n : {e}")
                except json.JSONDecodeError as e:
                    st.error(f"Erreur de lecture du JSON : {e}")
                except Exception as e:
                    st.error(f"Erreur inattendue : {e}")
    
    st.markdown("---")
    st.subheader("🔎 Recherche Ciqual")
    st.write("Rechercher un aliment dans la base Ciqual pour voir ses valeurs nutritionnelles.")
    
    if not df.empty:
        food_search = st.selectbox("Rechercher un aliment", options=[""] + df['alim_nom_fr'].tolist(), key="ciqual_search")
        if food_search:
            food_data = df[df['alim_nom_fr'] == food_search].iloc[0]
            col_n1, col_n2, col_n3, col_n4 = st.columns(4)
            col_n1.metric("Énergie", f"{food_data['Energie_kcal_100g']:.0f} kcal/100g")
            col_n2.metric("Protéines", f"{food_data['Proteines_Jones_g_100g']:.1f} g/100g")
            col_n3.metric("Glucides", f"{food_data['Glucides_g_100g']:.1f} g/100g")
            col_n4.metric("Lipides", f"{food_data['Lipides_g_100g']:.1f} g/100g")


# ============================================================
# TAB 3 : CONFIGURATION PRATICIEN
# ============================================================
with tab_config:
    st.subheader("⚙️ Configuration Praticien")
    st.info("Définissez vos portions de référence, options PDJ/collation et conseils. Ces valeurs seront utilisées pour générer les programmes alimentaires.")
    
    with st.form("settings_form"):
        
        # --- Portions de référence ---
        st.markdown("### 🥩 Portions de Référence")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_viande = st.number_input("Viande (g)", value=int(portions.get("proteines_viande", 125)), step=5)
            new_poisson = st.number_input("Poisson (g)", value=int(portions.get("proteines_poisson", 150)), step=5)
            new_oeufs = st.number_input("Œufs (nombre)", value=int(portions.get("proteines_oeufs", 3)), step=1)
        with col2:
            new_feculents = st.number_input("Féculents cuits (g)", value=int(portions.get("feculents_cuits", 150)), step=10)
            new_legumes = st.number_input("Légumes cuits (g)", value=int(portions.get("legumes_cuits", 200)), step=10)
            new_crudites = st.number_input("Crudités (g)", value=int(portions.get("legumes_crus", 150)), step=10)
        with col3:
            new_mg_g = st.number_input("Matières grasses (g huile réf.)", value=int(portions.get("matieres_grasses_g", 10)), step=1)
            new_fruits = st.number_input("Fruits (g)", value=int(portions.get("fruits", 100)), step=10)
            new_legumineuses = st.number_input("Légumineuses cuites (g)", value=int(portions.get("legumineuses_cuites", 160)), step=10)
        
        col4, col5 = st.columns(2)
        with col4:
            new_oleagineux = st.number_input("Oléagineux (g)", value=int(portions.get("oleagineux", 15)), step=5)
        with col5:
            new_pain = st.number_input("Pain (g)", value=int(portions.get("pain", 50)), step=5)
        
        # --- Cibles macros par défaut ---
        st.markdown("### 🎯 Cibles Macro-Nutriments (défauts praticien)")
        st.caption(
            "Valeurs appliquées par défaut à chaque nouveau patient. "
            "Modifiables par patient dans l'onglet Programme."
        )
        macros_cfg = settings.get("macros_cibles", data_manager.DEFAULT_SETTINGS["macros_cibles"])
        col_mc1, col_mc2, col_mc3 = st.columns(3)
        with col_mc1:
            new_prot_ratio = st.number_input(
                "Protéines (g/kg)", min_value=0.6, max_value=2.5,
                value=float(macros_cfg.get("proteines_g_par_kg", 1.3)), step=0.1
            )
        with col_mc2:
            new_lip_pct = st.number_input(
                "Lipides (% kcal)", min_value=15, max_value=50,
                value=int(macros_cfg.get("lipides_pct", 30)), step=1
            )
        with col_mc3:
            new_glu_min = st.number_input(
                "Glucides min (% kcal)", min_value=20, max_value=70,
                value=int(macros_cfg.get("glucides_pct_min", 40)), step=1
            )

        # --- Hydratation ---
        st.markdown("### 💧 Hydratation")
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            new_eau = st.number_input("Objectif Eau (L)", value=float(hydratation.get("objectif_litres", 1.5)), step=0.1)
        with col_h2:
            new_cafe = st.number_input("Max café/thé par jour", value=int(hydratation.get("max_cafe_the", 3)), step=1)
        
        # --- Options PDJ ---
        st.markdown("### 🌅 Options Petit-Déjeuner")
        st.caption("Une option par ligne. Vous pouvez modifier, ajouter ou supprimer des options.")
        new_pdj_text = st.text_area(
            "Options PDJ",
            value="\n".join(options_pdj),
            height=180
        )
        
        # --- Options Collation ---
        st.markdown("### ☕ Options Collation")
        new_collation_text = st.text_area(
            "Options Collation",
            value="\n".join(options_collation),
            height=180
        )
        
        # --- Conseils ---
        st.markdown("### 📝 Conseils Généraux")
        new_conseils = st.text_area(
            "Conseils à inclure dans les programmes",
            value=conseils,
            height=200
        )
        
        submitted = st.form_submit_button("💾 Enregistrer les réglages", type="primary")
        
        if submitted:
            new_data = {
                "portions": {
                    "proteines_viande": new_viande,
                    "proteines_poisson": new_poisson,
                    "proteines_oeufs": new_oeufs,
                    "feculents_cuits": new_feculents,
                    "legumes_cuits": new_legumes,
                    "legumes_crus": new_crudites,
                    "matieres_grasses_g": new_mg_g,
                    "fruits": new_fruits,
                    "legumineuses_cuites": new_legumineuses,
                    "oleagineux": new_oleagineux,
                    "pain": new_pain,
                    "fromage_blanc": 100,
                },
                "options_pdj": [o.strip() for o in new_pdj_text.split("\n") if o.strip()],
                "options_collation": [o.strip() for o in new_collation_text.split("\n") if o.strip()],
                "hydratation": {
                    "objectif_litres": new_eau,
                    "max_cafe_the": new_cafe,
                    "repartition": hydratation.get("repartition", "")
                },
                "frequences_proteines": settings.get("frequences_proteines", data_manager.DEFAULT_SETTINGS["frequences_proteines"]),
                "macros_cibles": {
                    "proteines_g_par_kg": new_prot_ratio,
                    "lipides_pct": new_lip_pct,
                    "glucides_pct_min": new_glu_min,
                },
                "conseils_generaux": new_conseils
            }
            
            if data_manager.save_settings(new_data):
                st.success("✅ Réglages enregistrés avec succès !")
            else:
                st.error("Erreur lors de l'enregistrement.")
