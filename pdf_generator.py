"""
Générateur de PDF — Programme Alimentaire
Reproduit le format utilisé par Tracy :
 Page 1: Objectifs + Petit-Déjeuner
 Page 2: Déjeuner (Protéines + Féculents + Légumes + MG + Dessert)
 Page 3: Collation
 Page 4: Dîner
 Page 5: Répartition assiette
 Page 6: Hydratation + Légumineuses
 Page 7: Oléagineux + Graines
 Page 8: Fruits
 Page 9-10: Conseils Généraux
"""

from fpdf import FPDF
import data_manager
import os
from datetime import datetime

# Chemin du font Unicode
FONT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(FONT_DIR, "DejaVuSans.ttf")

FONT_NAME = "DejaVu"


class ProgrammePDF(FPDF):
    """PDF personnalisé pour le Programme Alimentaire."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        # Enregistrer la police Unicode
        self.add_font(FONT_NAME, "", FONT_PATH, uni=True)
        self.add_font(FONT_NAME, "B", FONT_PATH, uni=True)
        self.add_font(FONT_NAME, "I", FONT_PATH, uni=True)

    # --- En-tête et pied ---
    def header(self):
        if self.page_no() > 1:
            self.set_font(FONT_NAME, "I", 8)
            self.set_text_color(130, 130, 130)
            self.cell(0, 6, "Programme Alimentaire", align="L")
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font(FONT_NAME, "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, str(self.page_no()), align="C")

    # --- Helpers ---
    def section_title(self, title):
        """Titre de section avec bandeau coloré."""
        self.set_fill_color(0, 166, 81)  # Vert Tricky Nutrition (#00A651)
        self.set_text_color(255, 255, 255)
        self.set_font(FONT_NAME, "B", 14)
        self.cell(0, 10, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_text_color(40, 40, 40)

    def sub_title(self, title):
        """Sous-titre."""
        self.set_font(FONT_NAME, "B", 11)
        self.set_text_color(0, 166, 81)  # Vert Tricky Nutrition
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(40, 40, 40)

    def body_text(self, text):
        """Texte normal multi-lignes."""
        self.set_font(FONT_NAME, "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def bullet_list(self, items):
        """Liste a puces."""
        self.set_font(FONT_NAME, "", 10)
        self.set_text_color(40, 40, 40)
        for item in items:
            txt = item.strip()
            if txt.startswith("- "):
                txt = txt[2:]
            self.multi_cell(0, 5.5, f"  - {txt}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def numbered_list(self, items, prefix="Option"):
        """Liste numerotee."""
        self.set_font(FONT_NAME, "", 10)
        for i, item in enumerate(items, 1):
            self.set_font(FONT_NAME, "B", 10)
            self.set_text_color(40, 40, 40)
            self.cell(0, 6, f"  {prefix} {i}", new_x="LMARGIN", new_y="NEXT")
            self.set_font(FONT_NAME, "", 9)
            self.set_text_color(80, 80, 80)
            self.multi_cell(0, 5, f"      {item}", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(40, 40, 40)
            self.ln(1)
        self.ln(2)

    def equivalence_table(self, title, equivalences):
        """Tableau d'équivalences."""
        if not equivalences:
            return

        if title:
            self.sub_title(title)

        # En-tête du tableau
        col_w = [90, 45, 35]
        self.set_font(FONT_NAME, "B", 9)
        self.set_fill_color(236, 240, 241)
        self.set_text_color(40, 40, 40)
        self.cell(col_w[0], 7, "  Aliment", border=1, fill=True)
        self.cell(col_w[1], 7, "  Poids (g)", border=1, fill=True)
        self.cell(col_w[2], 7, "  Kcal", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        # Lignes
        self.set_font(FONT_NAME, "", 9)
        for j, row in enumerate(equivalences):
            fill = j % 2 == 0
            if fill:
                self.set_fill_color(249, 249, 249)
            self.cell(col_w[0], 6, f"  {row['nom']}", border=1, fill=fill)
            self.cell(col_w[1], 6, f"  {row['poids_g']}g", border=1, fill=fill)
            self.cell(col_w[2], 6, f"  {row['kcal']}", border=1, fill=fill, new_x="LMARGIN", new_y="NEXT")

        self.ln(4)

    def info_box(self, text):
        """Encadre d'information."""
        self.set_font(FONT_NAME, "I", 9)
        self.set_text_color(232, 200, 64)  # Or Tricky Nutrition (#E8C840)
        self.multi_cell(0, 5.5, f"  >> {text}", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(40, 40, 40)
        self.ln(3)


def generate_programme_pdf(data):
    """
    Génère le PDF du Programme Alimentaire.

    Args:
        data: dict avec les clés :
            client_ref, bmr, tdee, formule_bmr, objectifs,
            petit_dejeuner, dejeuner, collation, diner,
            hydratation, frequences_proteines, conseils_generaux,
            listes_reference

    Returns:
        bytes — le contenu du fichier PDF
    """
    pdf = ProgrammePDF()
    pdf.set_margins(15, 15, 15)

    # =============================================
    # PAGE 1 : Couverture + Objectifs + PDJ
    # =============================================
    pdf.add_page()

    # Titre principal
    pdf.set_font(FONT_NAME, "B", 24)
    pdf.set_text_color(0, 166, 81)  # Vert Tricky Nutrition
    pdf.cell(0, 15, "PROGRAMME ALIMENTAIRE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Nom du patient
    pdf.set_font(FONT_NAME, "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, data.get("client_ref", "Patient"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Info BMR
    pdf.set_font(FONT_NAME, "I", 9)
    formule = data.get("formule_bmr", "Harris-Benedict")
    bmr_val = data.get("bmr", 0)
    tdee_val = data.get("tdee", 0)
    pdf.cell(0, 6, f"Formule : {formule}  |  BMR : {int(bmr_val)} kcal  |  TDEE : {int(tdee_val)} kcal",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT_NAME, "I", 8)
    pdf.cell(0, 5, f"Genere le {datetime.now().strftime('%d/%m/%Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Ligne de séparation
    pdf.set_draw_color(200, 200, 200)
    pdf.line(15, pdf.get_y(), pdf.w - 15, pdf.get_y())
    pdf.ln(6)

    # Objectifs
    pdf.section_title("OBJECTIFS")
    objectifs = data.get("objectifs", [])
    pdf.bullet_list([f"- {o}" for o in objectifs])

    # Petit-Déjeuner
    pdf.section_title("PETIT-DEJEUNER")
    pdj_options = data.get("petit_dejeuner", {}).get("options", [])
    if pdj_options:
        pdf.numbered_list(pdj_options)
    pdf.info_box("Ces options peuvent etre a emporter. Les options \"plaisir\" doivent etre occasionnelles.")

    # Notes pain
    pdf.sub_title("Reperes pain :")
    pdf.body_text("50g de pain frais = 2 petites tranches = 1 grande tranche = 1/5 baguette = 2 biscottes")

    # =============================================
    # PAGE 2 : Déjeuner
    # =============================================
    pdf.add_page()
    pdf.section_title("DEJEUNER")
    pdf.body_text("Composez votre assiette avec UN des composants de chaque groupe alimentaire :")

    # Protéines
    dejeuner = data.get("dejeuner", {})
    prot_data = dejeuner.get("proteines", {})
    equiv_prot = prot_data.get("equivalences", [])
    pdf.equivalence_table(
        f"Proteines - portion de reference : {prot_data.get('portion_viande_g', 125)}g viande / {prot_data.get('portion_poisson_g', 150)}g poisson / {prot_data.get('portion_oeufs', 3)} oeufs",
        equiv_prot
    )

    # Féculents
    fec_data = dejeuner.get("feculents", {})
    equiv_fec = fec_data.get("equivalences", [])
    pdf.equivalence_table(
        f"Feculents - portion : {fec_data.get('portion_g', 150)}g CUITS",
        equiv_fec
    )

    # Légumes
    leg_data = dejeuner.get("legumes", {})
    pdf.sub_title(f"Legumes - {leg_data.get('portion_cuits_g', 200)}g cuits et/ou {leg_data.get('portion_crudites_g', 150)}g crudites")
    equiv_leg = leg_data.get("equivalences", [])
    if equiv_leg:
        pdf.equivalence_table("", equiv_leg)
    else:
        pdf.body_text("150-200g legumes cuits (1/2 assiette) ou 100-150g crudites ou 250-300ml soupe de legumes")

    # Matières grasses
    mg_data = dejeuner.get("matieres_grasses", {})
    pdf.sub_title("Matieres Grasses")
    pdf.body_text(f"{mg_data.get('portion_cas', 1)} cuillere(s) a soupe (8-10g) d'huile pour la cuisson ou l'assaisonnement. Varier vos huiles (olive, colza, coco, noix, noisette...).")

    # Dessert
    pdf.sub_title("Dessert")
    dessert_dej = dejeuner.get("dessert", "+ 1 fruit")
    pdf.body_text(dessert_dej)

    # =============================================
    # PAGE 3 : Collation
    # =============================================
    pdf.add_page()
    pdf.section_title("COLLATION - APRES-MIDI")

    collation_options = data.get("collation", {}).get("options", [])
    if collation_options:
        for i, opt in enumerate(collation_options, 1):
            pdf.set_font(FONT_NAME, "", 10)
            pdf.multi_cell(0, 6, f"  - {opt}", new_x="LMARGIN", new_y="NEXT")
            if i < len(collation_options):
                pdf.set_font(FONT_NAME, "I", 9)
                pdf.set_text_color(130, 130, 130)
                pdf.cell(0, 4, "    OU", new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(40, 40, 40)
        pdf.ln(3)

    pdf.info_box("Accompagner d'une boisson chaude (the, tisane sans sucre) ou d'eau.")
    pdf.ln(2)
    pdf.body_text("Rappel : si consommation de produits sucres (biscuits, gateaux, chocolat), toujours accompagner d'1 poignee d'oleagineux ou 1 fromage blanc.")

    # =============================================
    # PAGE 4 : Dîner
    # =============================================
    pdf.add_page()
    pdf.section_title("DINER")
    pdf.body_text("Composez votre assiette avec UN des composants de chaque groupe alimentaire :")

    diner = data.get("diner", {})
    d_prot = diner.get("proteines", {})
    d_equiv_prot = d_prot.get("equivalences", [])
    pdf.equivalence_table(
        f"Proteines - portion : {d_prot.get('portion_viande_g', 125)}g",
        d_equiv_prot
    )

    d_fec = diner.get("feculents", {})
    d_equiv_fec = d_fec.get("equivalences", [])
    pdf.equivalence_table(
        f"Feculents - portion : {d_fec.get('portion_g', 150)}g CUITS",
        d_equiv_fec
    )

    d_leg = diner.get("legumes", {})
    pdf.sub_title(f"Legumes - {d_leg.get('portion_cuits_g', 200)}g cuits / {d_leg.get('portion_crudites_g', 150)}g crudites / 250-300ml soupe")

    d_mg = diner.get("matieres_grasses", {})
    pdf.sub_title("Matieres Grasses")
    pdf.body_text(f"{d_mg.get('portion_cas', 1)} cuillere(s) a soupe pour la cuisson ou l'assaisonnement.")

    pdf.sub_title("Dessert")
    dessert_din = diner.get("dessert", "100g fromage blanc/Skyr/yaourt grecque")
    pdf.body_text(dessert_din)

    # =============================================
    # PAGE 5 : Répartition assiette
    # =============================================
    pdf.add_page()
    pdf.section_title("REPARTITION DE L'ASSIETTE")
    pdf.ln(4)
    pdf.body_text("Partagez votre assiette en 3 :")
    pdf.ln(2)

    pdf.sub_title("Option 1")
    pdf.bullet_list([
        "- 1/2 assiette : Legumes",
        "- 1/4 assiette : Feculents",
        "- 1/4 assiette : Proteines animales ou vegetales"
    ])

    pdf.sub_title("Option 2")
    pdf.bullet_list([
        "- 1/3 assiette : Legumes",
        "- 1/3 assiette : Feculents",
        "- 1/3 assiette : Proteines animales ou vegetales"
    ])

    # =============================================
    # PAGE 6 : Hydratation + Légumineuses
    # =============================================
    pdf.add_page()
    pdf.section_title("HYDRATATION")
    hydratation = data.get("hydratation", {})
    hydra_rules = [
        f"- Repartir la consommation tout au long de la journee. Min. 8 verres (250ml) d'eau par jour.",
        f"- Repartition suggeree : {hydratation.get('repartition', '')}",
        f"- Limiter la consommation de cafe et the noir a {hydratation.get('max_cafe_the', 3)} tasses par jour. Privilegier les tisanes.",
        f"- Objectif : Boire au moins {hydratation.get('objectif_litres', 1.5)}-2L par jour"
    ]
    pdf.bullet_list(hydra_rules)

    # Légumineuses
    pdf.section_title("LEGUMINEUSES")
    listes = data.get("listes_reference", {})
    equiv_legum = listes.get("legumineuses", [])
    if equiv_legum:
        pdf.equivalence_table("Equivalences legumineuses", equiv_legum)
    pdf.body_text("Haricots secs (rouge, blanc, coco, noir...), Lentilles (corail, vert, beluga...), Pois chiches, Feves, Pois casses, Flageolets, Edamame.")
    pdf.info_box("Bien les tremper si secs (min 8h). En conserve, bien les rincer avant consommation.")

    # =============================================
    # PAGE 7 : Oléagineux + Graines
    # =============================================
    pdf.add_page()
    pdf.section_title("FRUITS A COQUE / OLEAGINEUX (grilles, sans sel)")
    pdf.body_text("Amande, Noix, Noix de pecan, Noisette, Noix de macadamia, Pistache, Noix de cajou, Noix de Bresil, Chataigne")

    pdf.section_title("GRAINES")
    pdf.body_text("Tournesol, Courge, Lin (broye avant de consommer), Chia, Chanvre")

    # =============================================
    # PAGE 8 : Fruits
    # =============================================
    pdf.add_page()
    pdf.section_title("FRUITS")
    pdf.sub_title("Equivalences : 1 fruit = environ 100g")
    pdf.body_text(
        "100g compote sans sucres ajoutes, 1 pomme, 1 poire, 1 banane, 2 clementines, "
        "2 mandarines, 1 orange, 1 pamplemousse, 10-15 raisins, 3 abricots (petits), "
        "2 dattes, 1 peche, 1 nectarine, 2 kiwis (petit), 2 poignees de myrtilles (20), "
        "7-8 fraises, 10-15 framboises, 1/4 ananas, 1/2 mangue, 1 belle tranche de pasteque, "
        "2-3 figues, 2-3 prunes, 1/4 melon (grand) ou 1/2 melon (petit), 15 cerises, 3-4 quetsches"
    )
    pdf.ln(2)
    pdf.info_box("Pour les fruits seches : meme quantite en frais que seche. Ex. 2-3 abricots frais = 2-3 abricots seches.")

    # =============================================
    # PAGE 9-10 : Conseils Généraux
    # =============================================
    pdf.add_page()
    pdf.section_title("CONSEILS GENERAUX")

    conseils = data.get("conseils_generaux", "")
    if isinstance(conseils, str):
        lines = [l.strip() for l in conseils.split("\n") if l.strip()]
        pdf.bullet_list(lines)
    elif isinstance(conseils, list):
        pdf.bullet_list(conseils)

    # Fréquences protéines
    pdf.section_title("FREQUENCES DES PROTEINES AU REPAS")
    freq = data.get("frequences_proteines", {})

    col_w = [60, 60]
    pdf.set_font(FONT_NAME, "B", 9)
    pdf.set_fill_color(236, 240, 241)
    pdf.cell(col_w[0], 7, "  Type", border=1, fill=True)
    pdf.cell(col_w[1], 7, "  Frequence", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(FONT_NAME, "", 9)
    freq_items = [
        ("Viandes blanches", freq.get("viandes_blanches", "5 fois/semaine")),
        ("Viandes rouges", freq.get("viandes_rouges", "max 2 fois/semaine")),
        ("Poissons", freq.get("poissons", "2-3 fois/semaine")),
        ("Oeufs", freq.get("oeufs", "min 3-4 fois/semaine")),
        ("Vegetarien", freq.get("vegetarien", "min 3-4 fois/semaine")),
    ]
    for j, (label, val) in enumerate(freq_items):
        fill = j % 2 == 0
        if fill:
            pdf.set_fill_color(249, 249, 249)
        pdf.cell(col_w[0], 6, f"  {label}", border=1, fill=fill)
        pdf.cell(col_w[1], 6, f"  {val}", border=1, fill=fill, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Extras et matières grasses
    pdf.sub_title("MATIERES GRASSES")
    pdf.bullet_list([
        "- Varier vos huiles vegetales",
        "- Ne pas cuire le beurre et la margarine",
        "- Cuisson : huile d'olive, huile de coco, huile de sesame, huile d'avocat, ghee",
        "- Assaisonnement : huile de colza, huile de lin, huile de noix, huile de pepins de raisin"
    ])

    pdf.sub_title("EXTRAS")
    pdf.bullet_list([
        "- Limiter a 1 produit gras/frit 2-3 fois par semaine",
        "- Limiter a 2-3 produits sucres par semaine",
        "- 1 carre de chocolat noir par jour autorise (collation ou apres repas)",
        "- Limiter boissons sucrees/gazeuses a 2 fois/semaine",
        "- Limiter restaurants et plats livres a 2 fois par semaine",
        "- Si dessert patisserie : reduire de ~50g les feculents cuits"
    ])

    pdf.sub_title("CONDIMENTS")
    pdf.body_text("Pas de regles specifiques. Variez vos epices. Vinaigrette maison : 1 cas huile pour 2 cas vinaigre + assaisonnements.")

    # Retourner le PDF en bytes
    return pdf.output()
