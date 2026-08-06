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
CLE_VIP_CORRECTE = "POISSON95"
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
            <span style="color: #00FFcc; font-weight: 800; font-size: 16px;">ANALYSEUR HAUTE RÉSOLUTION ACTIF — Compétitions Officielles & Internationales</span>
        </div>
    """, unsafe_allow_html=True)

    cle_acces = st.text_input("🔑 Entrez votre clé d'accès VIP :", type="password")
    
    if cle_acces in [CLE_VIP_CORRECTE, CLE_ADMIN_FORCAGE] and cle_acces != "":
        st.success("🔓 Algorithme déverrouillé. Base de données complète chargée.")

        # =========================================================
        # 🌍 DICTIONNAIRE COMPLET DES PAYS ET COMPÉTITIONS RÉELLES
        # =========================================================
        st.markdown('<div class="section-title">🌍 Sélection des Pays et Compétitions Officielles</div>', unsafe_allow_html=True)
        
        base_competitions = {
            "🌍 International / Europe": [
                "UEFA Champions League", 
                "UEFA Europa League", 
                "UEFA Conference League", 
                "UEFA Super Cup", 
                "Copa Libertadores", 
                "Copa Sudamericana",
                "CAF Champions League",
                "CAF Coupe de la Confédération",
                "Coupe du Monde de la FIFA",
                "Matchs Amicaux Internationaux"
            ],
            "Angleterre": ["Premier League", "Championship", "League One", "League Two", "FA Cup", "EFL Cup"],
            "Espagne": ["La Liga", "Segunda División", "Copa del Rey", "Supercopa de España"],
            "Italie": ["Serie A", "Serie B", "Serie C", "Coppa Italia", "Supercoppa Italiana"],
            "France": ["Ligue 1", "Ligue 2", "National 1", "Coupe de France", "Trophée des Champions"],
            "Allemagne": ["Bundesliga", "2. Bundesliga", "3. Liga", "DFB-Pokal"],
            "Portugal": ["Primeira Liga", "Segunda Liga", "Taça de Portugal"],
            "Pays-Bas": ["Eredivisie", "Eerste Divisie", "KNVB Beker"],
            "Belgique": ["Jupiler Pro League", "Challenger Pro League", "Coupe de Belgique"],
            "Brésil": ["Série A", "Série B", "Campeonato Paulista", "Copa do Brasil"],
            "Argentine": ["Liga Profesional", "Primera Nacional", "Copa Argentina"],
            "Cameroun": ["MTN Elite One", "MTN Elite Two", "Coupe du Cameroun"],
            "Sénégal": ["Ligue 1 sénégalaise", "Ligue 2 sénégalaise"],
            "Maroc": ["Botola Pro 1", "Botola Pro 2"],
            "Égypte": ["Egyptian Premier League", "Egypt Cup"],
            "Algérie": ["Ligue 1 Professionnelle", "Ligue 2 Algérie"],
            "Tunisie": ["Ligue Professionnelle 1", "Ligue Professionnelle 2"],
            "Turquie": ["Süper Lig", "1. Lig", "Türkiye Kupası"],
            "Grèce": ["Super League Ellada", "Greek Football Cup"],
            "Russie": ["Premier League Russe", "FNL", "Coupe de Russie"],
            "Ukraine": ["Premyer-liha", "Coupe d'Ukraine"],
            "Arabie Saoudite": ["Saudi Pro League", "King Cup"],
            "Émirats Arabes Unis": ["UAE Pro League"],
            "Qatar": ["Qatar Stars League"],
            "Japon": ["J1 League", "J2 League", "Emperor's Cup"],
            "Corée du Sud": ["K League 1", "K League 2"],
            "Chine": ["Chinese Super League"],
            "États-Unis": ["MLS", "USL Championship"],
            "Mexique": ["Liga MX", "Liga de Expansión MX"],
            "Colombie": ["Categoría Primera A", "Copa Colombia"],
            "Chili": ["Primera División de Chile"],
            "Uruguay": ["Primera División de Uruguay"],
            "Équateur": ["Liga Pro Serie A"],
            "Pérou": ["Liga 1 de Fútbol Profesional"],
            "Suisse": ["Super League", "Challenge League", "Coupe de Suisse"],
            "Autriche": ["Austrian Bundesliga", "2. Liga"],
            "Danemark": ["Superligaen", "1. Division"],
            "Suède": ["Allsvenskan", "Superettan"],
            "Norvège": ["Eliteserien", "1. Divisjon"],
            "Pologne": ["Ekstraklasa", "I Liga"],
            "République Tchèque": ["Czech First League"],
            "Roumanie": ["SuperLiga României"],
            "Hongrie": ["Nemzeti Bajnokság I"],
            "Croatie": ["HNL", "Prva NL"],
            "Serbie": ["Superliga Srbije"],
            "Écosse": ["Scottish Premiership", "Scottish Championship", "Scottish Cup"],
            "Irlande": ["League of Ireland Premier Division"],
            "Pays de Galles": ["Cymru Premier"],
            "Finlande": ["Veikkausliiga"],
            "Islande": ["Úrvalsdeild karla"],
            "Bulgarie": ["efbet Liga"],
            "Slovaquie": ["Niké Liga"],
            "Slovénie": ["PrvaLiga"],
            "Chyprerie": ["Cyta Championship"],
            "Israël": ["Israeli Premier League"],
            "Australie": ["A-League Men"],
            "Nouvelle-Zélande": ["National League"],
            "Afrique du Sud": ["DSTV Premiership", "National First Division"],
            "Ghana": ["Ghana Premier League"],
            "Côte d'Ivoire": ["Ligue 1 Lonaci"],
            "Nigeria": ["Nigeria Premier Football League"],
            "Mali": ["Ligue 1 Malienne"],
            "Guinée": ["Ligue 1 Pro Guinée"],
            "RD Congo": ["Linafoot Ligue 1"],
            "Angola": ["Girabola"],
            "Zambie": ["Zambian Super League"],
            "Tanzanie": ["Tanzanian Premier League"],
            "Kenya": ["Kenyan Premier League"],
            "Inde": ["Indian Super League"],
            "Thaïlande": ["Thai League 1"],
            "Viêt Nam": ["V.League 1"],
            "Indonésie": ["Liga 1 Indonésie"],
            "Malaisie": ["Malaysia Super League"],
            "Singapour": ["Singapore Premier League"]
        }
        
        pays_liste = list(base_competitions.keys())
        
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            pays_choisi = st.selectbox("Sélectionnez le territoire ou la zone :", pays_liste)
        with col_nav2:
            divisions_disponibles = base_competitions[pays_choisi]
            ligue_choisie = st.selectbox("Sélectionnez la compétition / ligue :", divisions_disponibles)
            
        page_id = f"{pays_choisi} -> {ligue_choisie}"
        
        st.caption(f"📍 Configuration de calcul active : **{page_id}**")

        # =========================================================
        # 📊 PARAMÈTRES ENTRÉES DU MATCH
        # =========================================================
        st.markdown('<div class="section-title">📊 Statistiques Brutes de Performance Réelle</div>', unsafe_allow_html=True)
        
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            st.subheader("🏠 Bloc Équipe Domicile")
            nom_dom = st.text_input("Nom du club local :", "Real Madrid")
            buts_marques_dom = st.number_input("Total Buts marqués à la maison :", min_value=0.0, value=34.0, step=0.1)
            buts_encaisses_dom = st.number_input("Total Buts encaissés à la maison :", min_value=0.0, value=12.0, step=0.1)
            matchs_joues_dom = st.number_input("Volume total matchs joués à domicile :", min_value=1, value=5)

        with col_input2:
            st.subheader("🚀 Bloc Équipe Extérieur")
            nom_ext = st.text_input("Nom du club visiteur :", "Manchester City")
            buts_marques_ext = st.number_input("Total Buts marqués dehors :", min_value=0.0, value=28.0, step=0.1)
            buts_encaisses_ext = st.number_input("Total Buts encaissés dehors :", min_value=0.0, value=15.0, step=0.1)
            matchs_joues_ext = st.number_input("Volume total matchs joués à l'extérieur :", min_value=1, value=5)

        st.markdown("---")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            moyenne_buts_championnat = st.slider("⚽ Constante de buts par match du championnat général :", min_value=1.0, max_value=8.0, value=2.7, step=0.05)
        with col_p2:
            rho_param = st.slider("📉 Facteur d'interdépendance tactique (Dixon-Coles Rho) :", min_value=-0.25, max_value=0.25, value=-0.08, step=0.01)

        moyenne_dom_ext = moyenne_buts_championnat / 2

        # =========================================================
        # 🧠 INJECTEUR INTELLIGENT DE PUISSANCE OFFENSIVE / DÉFENSIVE
        # =========================================================
        force_attaque_dom = (buts_marques_dom / matchs_joues_dom) / moyenne_dom_ext if matchs_joues_dom > 0 else 1.0
        force_defense_dom = (buts_encaisses_dom / matchs_joues_dom) / moyenne_dom_ext if matchs_joues_dom > 0 else 1.0

        force_attaque_ext = (buts_marques_ext / matchs_joues_ext) / moyenne_dom_ext if matchs_joues_ext > 0 else 1.0
        force_defense_ext = (buts_encaisses_ext / matchs_joues_ext) / moyenne_dom_ext if matchs_joues_ext > 0 else 1.0

        lambda_dom = max(0.02, force_attaque_dom * force_defense_ext * moyenne_dom_ext)
        lambda_ext = max(0.02, force_attaque_ext * force_defense_dom * moyenne_dom_ext)

        # =========================================================
        # 📐 GÉNÉRATION DE LA MATRICE COMPLÈTE (RÉSOLUTION 10x10)
        # =========================================================
        taille_matrice = 10
        matrice_probabilités = np.zeros((taille_matrice, taille_matrice))
        
        for i in range(taille_matrice):
            for j in range(taille_matrice):
                p_pure_dom = loi_poisson_pure(i, lambda_dom)
                p_pure_ext = loi_poisson_pure(j, lambda_ext)
                ajustement_tactique = modèle_quantum_dixon_coles(i, j, lambda_dom, lambda_ext, rho_param)
                matrice_probabilités[i, j] = p_pure_dom * p_pure_ext * ajustement_tactique

        somme_matrice = np.sum(matrice_probabilités)
        if somme_matrice > 0:
            matrice_probabilités /= somme_matrice

        # =========================================================
        # 📐 EXTRACTION DES PROBABILITÉS CRITIQUES 1N2 & MARCHÉS
        # =========================================================
        prob_1 = float(np.sum(np.tril(matrice_probabilités, -1)))
        prob_N = float(np.sum(np.diag(matrice_probabilités)))
        prob_2 = float(np.sum(np.triu(matrice_probabilités, 1)))

        prob_under_25 = 0.0
        for i in range(3):
            for j in range(3):
                if i + j < 3:
                    prob_under_25 += matrice_probabilités[i, j]
        prob_over_25 = max(0.0, 1.0 - prob_under_25)

        prob_btts_oui = 0.0
        for i in range(1, taille_matrice):
            for j in range(1, taille_matrice):
                prob_btts_oui += matrice_probabilités[i, j]
        prob_btts_non = max(0.0, 1.0 - prob_btts_oui)

        # =========================================================
        # 🏆 AFFICHAGE DES RÉSULTATS HAUTE PERFORMANCE
        # =========================================================
        st.markdown('<div class="section-title">🏆 Résultats de la Simulation Quantique</div>', unsafe_allow_html=True)

        col_res1, col_res2 = st.columns(2)

        with col_res1:
            st.markdown(f"""
            <div class="metric-box">
                <span>⚽ Espérance de Buts ({nom_dom})</span>
                <span class="highlight-value text-glow">{lambda_dom:.2f} buts</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-box" style="margin-top: 15px;">
                <span>📈 Probabilité Victoire Domicile (1)</span>
                <span class="highlight-value">{prob_1 * 100:.2f}%</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-box" style="margin-top: 15px;">
                <span>⚽ Marché Over 2.5 Buts</span>
                <span class="highlight-value">{prob_over_25 * 100:.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

        with col_res2:
            st.markdown(f"""
            <div class="metric-box">
                <span>🚀 Espérance de Buts ({nom_ext})</span>
                <span class="highlight-value text-glow">{lambda_ext:.2f} buts</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-box" style="margin-top: 15px;">
                <span>📉 Probabilité Victoire Extérieur (2)</span>
                <span class="highlight-value">{prob_2 * 100:.2f}%</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-box" style="margin-top: 15px;">
                <span>🤝 Probabilité Match Nul (N)</span>
                <span class="highlight-value">{prob_N * 100:.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

        col_btts1, col_btts2 = st.columns(2)
        with col_btts1:
            st.markdown(f"""
            <div class="metric-box" style="margin-top: 15px;">
                <span>🔥 Les Deux Équipes Marquent (BTTS - Oui)</span>
                <span class="highlight-value">{prob_btts_oui * 100:.2f}%</span>
            </div>
            """, unsafe_allow_html=True)
        with col_btts2:
            st.markdown(f"""
            <div class="metric-box" style="margin-top: 15px;">
                <span>🛡️ Moins de 2.5 Buts (Under 2.5)</span>
                <span class="highlight-value">{prob_under_25 * 100:.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

        max_idx = np.unravel_index(np.argmax(matrice_probabilités), matrice_probabilités.shape)
        score_exact_prob = matrice_probabilités[max_idx] * 100
        st.markdown(f"""
            <div class="metric-box" style="margin-top: 25px; border: 2px solid #FF9900;">
                <span style="font-size: 18px; font-weight: bold; color: #FF9900;">🎯 Score Exact le Plus Probable</span>
                <span class="highlight-value" style="font-size: 36px; color: #FFFFFF;">{max_idx[0]} - {max_idx[1]}</span>
                <span style="color: #00FFcc; font-size: 16px; font-weight: bold;">Confiance du Modèle : {score_exact_prob:.2f}%</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.success(f"✅ Analyse complète générée pour **{page_id}**.")
        
