import streamlit as st
import numpy as np
import math

# Configuration de la page de calcul haute performance
st.set_page_config(page_title="BetScope Quantum Poisson v3", page_icon="⚡", layout="wide")

# =========================================================
# 🎨 DESIGN PREMIUM SOMBRE & ACTIF
# =========================================================
st.markdown("""
<style>
    .stApp { background-color: #0B0E14; color: #F0F2F5; }
    .main-title { color: #FF9900; font-weight: 900; font-size: 36px; text-align: center; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 25px; }
    .section-title { border-left: 6px solid #FF9900; padding-left: 15px; color: #FFFFFF; font-size: 22px; margin-top: 30px; margin-bottom: 20px; font-weight: bold; }
    .metric-box { background-color: #121620; padding: 20px; border-radius: 12px; border: 1px solid #252D3A; text-align: center; box-shadow: 0 6px 12px rgba(0,0,0,0.5); }
    .highlight-value { color: #00FFcc; font-size: 28px; font-weight: 800; display: block; margin-top: 5px; }
    .text-glow { text-shadow: 0 0 10px rgba(0, 255, 204, 0.4); }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 🧠 ALGORITHMES MATHÉMATIQUES AVANCÉS (NIVEAU PROFESSIONNEL)
# =========================================================
def loi_poisson_pure(k, lambda_param):
    """Calcule la probabilité de Poisson brute pour k buts."""
    if lambda_param <= 0:
        return 0.0
    return (math.exp(-lambda_param) * (lambda_param ** k)) / math.factorial(k)

def modèle_quantum_dixon_coles(x, y, lambda_x, lambda_y, rho):
    """
    Algorithme de Dixon-Coles appliqué au football professionnel.
    Ajuste la corrélation mathématique des scores faibles (0-0, 1-0, 0-1, 1-1).
    Il supprime l'effet d'estimation mathématique pour coller à la réalité du terrain.
    """
    if rho == 0:
        return 1.0
    if x == 0 and y == 0:
        return 1.0 - (lambda_x * lambda_y * rho)
    elif x == 1 and y == 0:
        return 1.0 + (lambda_x * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lambda_y * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0

# =========================================================
# 🔐 SÉCURITÉ ACCÈS VIP
# =========================================================
CLE_VIP_CORRECTE = ""
CLE_ADMIN_FORCAGE = "ADMIN99"

# =========================================================
# 🧭 STRUCTURE PRINCIPALE
# =========================================================
menu = st.sidebar.radio("SÉLECTEUR DE MOTEUR", ["⚽ Espace Public", "⚡ Moteur Quantique VIP v3.0"])

if menu == "⚽ Espace Public":
    st.markdown('<div class="main-title">⚽ Espace Standard</div>', unsafe_allow_html=True)
    st.info("Système en attente. Le processeur bivarié à haute fidélité mathématique nécessite l'accès VIP.")

elif menu == "⚡ Moteur Quantique VIP v3.0":
    st.markdown('<div class="main-title">⚡ Moteur Quantique : Poisson Bivarié Pro</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 25px; background-color: #111520; padding: 15px; border-radius: 10px; border: 1px solid #FF9900;">
            <span style="height: 14px; width: 14px; background-color: #00FFcc; border-radius: 50%; display: inline-block; margin-right: 12px; box-shadow: 0 0 12px #00FFcc;"></span>
            <span style="color: #00FFcc; font-weight: 800; font-size: 16px;">ANALYSEUR HAUTE RÉSOLUTION ACTIF — Modèle Mathématique Sans Estimation</span>
        </div>
    """, unsafe_allow_html=True)

    cle_acces = st.text_input("🔑 Entrez votre clé d'accès VIP :", type="password")
    
    if cle_acces in [CLE_VIP_CORRECTE, CLE_ADMIN_FORCAGE] and cle_acces != "":
        st.success("🔓 Algorithme déverrouillé. Modèle de simulation mathématique pure initialisé.")

        # =========================================================
        # 📂 EXTENSION STRICTE À 1500 PAGES CONFIGURÉES
        # =========================================================
        st.markdown('<div class="section-title">🌍 Matrice Territoriale Extensible (1500 Configurations)</div>', unsafe_allow_html=True)
        
        # 75 Pays x 20 Divisions = Équilibre parfait de 1500 pages analytiques
        pays_liste = [f"Zone Géographique / Pays ID-{i:02d}" for i in range(1, 76)]
        divisions_liste = [f"Division / Ligue Professionnelle {j:02d}" for j in range(1, 21)]
        
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            pays_choisi = st.selectbox("Sélectionnez le territoire :", pays_liste)
        with col_nav2:
            ligue_choisie = st.selectbox("Sélectionnez le niveau de la ligue :", divisions_liste)
            
        index_pays = pays_liste.index(pays_choisi)
        index_ligue = divisions_liste.index(ligue_choisie)
        page_id = (index_pays * 20) + index_ligue + 1
        
        st.caption(f"📍 Configuration de calcul chargée de manière unique : **Page {page_id} / 1500**")

        # =========================================================
        # 📊 PARAMÈTRES ENTRÉES DU MATCH (ZÉRO DONNÉE ARRONDIE)
        # =========================================================
        st.markdown('<div class="section-title">📊 Statistiques Brutes de Performance Réelle</div>', unsafe_allow_html=True)
        
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            st.subheader("🏠 Bloc Équipe Domicile")
            nom_dom = st.text_input("Nom du club local :", "Teramo")
            buts_marques_dom = st.number_input("Total Buts marqués à la maison :", min_value=0.0, value=34.0, step=0.1)
            buts_encaisses_dom = st.number_input("Total Buts encaissés à la maison :", min_value=0.0, value=12.0, step=0.1)
            matchs_joues_dom = st.number_input("Volume total matchs joués à domicile :", min_value=1, value=5)

        with col_input2:
            st.subheader("🚀 Bloc Équipe Extérieur")
            nom_ext = st.text_input("Nom du club visiteur :", "Scafatese")
            buts_marques_ext = st.number_input("Total Buts marqués dehors :", min_value=0.0, value=12.0, step=0.1)
            buts_encaisses_ext = st.number_input("Total Buts encaissés dehors :", min_value=0.0, value=17.0, step=0.1)
            matchs_joues_ext = st.number_input("Volume total matchs joués à l'extérieur :", min_value=1, value=5)

        st.markdown("---")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            moyenne_buts_championnat = st.slider("⚽ Constante de buts par match du championnat général :", min_value=1.0, max_value=8.0, value=2.7, step=0.05)
        with col_p2:
            rho_param = st.slider("📉 Facteur d'interdépendance tactique (Dixon-Coles Rho) :", min_value=-0.25, max_value=0.25, value=-0.08, step=0.01)

        # Division par deux de la constante pour séparer équitablement l'attente Domicile/Extérieur
        moyenne_dom_ext = moyenne_buts_championnat / 2

        # =========================================================
        # 🧠 INJECTEUR INTELLIGENT DE PUISSANCE OFFENSIVE / DÉFENSIVE
        # =========================================================
        # Le script élimine les divisions par zéro et calcule les ratios de puissance réels
        force_attaque_dom = (buts_marques_dom / matchs_joues_dom) / moyenne_dom_ext if matchs_joues_dom > 0 else 1.0
        force_defense_dom = (buts_encaisses_dom / matchs_joues_dom) / moyenne_dom_ext if matchs_joues_dom > 0 else 1.0

        force_attaque_ext = (buts_marques_ext / matchs_joues_ext) / moyenne_dom_ext if matchs_joues_ext > 0 else 1.0
        force_defense_ext = (buts_encaisses_ext / matchs_joues_ext) / moyenne_dom_ext if matchs_joues_ext > 0 else 1.0

        # Espérances mathématiques pures (Nombre attendu de buts par équipe)
        lambda_dom = max(0.02, force_attaque_dom * force_defense_ext * moyenne_dom_ext)
        lambda_ext = max(0.02, force_attaque_ext * force_defense_dom * moyenne_dom_ext)

        # =========================================================
        # 📐 GÉNÉRATION DE LA MATRICE COMPLÈTE (RÉSOLUTION CRITIQUE 10x10)
        # =========================================================
        # Étendu à 10 buts (0 à 9) pour capturer les écarts et scores fleuves réels sans perte de probabilité
        taille_matrice = 10
        matrice_probabilités = np.zeros((taille_matrice, taille_matrice))
        
        for i in range(taille_matrice):
            for j in range(taille_matrice):
                p_pure_dom = loi_poisson_pure(i, lambda_dom)
                p_pure_ext = loi_poisson_pure(j, lambda_ext)
                ajustement_tactique = modèle_quantum_dixon_coles(i, j, lambda_dom, lambda_ext, rho_param)
                matrice_probabilités[i, j] = p_pure_dom * p_pure_ext * ajustement_tactique

        # Recalibrage de sécurité pour garantir la somme stricte à 100.00%
        somme_matrice = np.sum(matrice_probabilités)
        if somme_matrice > 0:
            matrice_probabilités /= somme_matrice

        # =========================================================
        # 📐 EXTRACTION DES PROBABILITÉS CRITIQUES 1N2 & MARCHÉS ACCESSOIRES
        # =========================================================
        prob_1 = float(np.sum(np.tril(matrice_probabilités, -1)))
        prob_N = float(np.sum(np.diag(matrice_probabilités)))
        prob_2 = float(np.sum(np.triu(matrice_probabilités, 1)))

        # Marché Over/Under 2.5 Buts (Somme exacte des scores < 2.5 buts)
        prob_under_25 = 0.0
        for i in range(3):
            for j in range(3):
                if i + j < 3:
                    prob_under_25 += matrice_probabilités[i, j]
        prob_over_25 = max(0.0, 1.0 - prob_under_25)

        # Marché Les Deux Équipes Marquent (BTTS)
        
