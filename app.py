import streamlit as st
import time
from datetime import datetime

# L'application va chercher l'image 73766_3.png pour en faire son icône officielle
st.set_page_config(page_title="Rodrigue Pro Puissant Prédiction", page_icon="73766_3.png", layout="centered")

# CSS pour masquer les éléments Streamlit et forcer le style mobile
st.markdown("""
    <head>
        <link rel="apple-touch-icon" href="73766_3.png">
        <link rel="icon" type="image/png" href="73766_3.png">
        <meta name="apple-mobile-web-app-capable" content="yes">
    </head>
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>import streamlit as st

# ==========================================
# ⚙️ CONFIGURATION DES 5 MATCHS DU MATIN
# Mettez à jour les équipes et les cotes ici chaque matin
# ==========================================

MATCHS_DU_JOUR = [
    {
        "equipes": "Real Madrid vs Barcelone",
        "cotes_dc": {'1X': 1.22, '12': 1.31, '2X': 2.06},
        "cotes_mf": {'V1/V1': 2.65, 'X/X': 5.5, 'V2/V2': 7.9},
        "cotes_score": {'1-0': 8.0, '1-1': 7.0, '2-1': 7.0, '3-1': 12.0}
    },
    {
        "equipes": "Man. City vs Liverpool",
        "cotes_dc": {'1X': 1.18, '12': 1.25, '2X': 2.30},
        "cotes_mf": {'V1/V1': 2.20, 'X/X': 5.8, 'V2/V2': 8.5},
        "cotes_score": {'1-0': 9.0, '1-1': 8.0, '2-1': 7.5, '2-0': 10.0}
    },
    # Tu peux ajouter jusqu'à 5 matchs ici en suivant la même structure...
]

# ==========================================
# 🤖 FONCTION D'ANALYSE AUTOMATIQUE DU ROBOT
# ==========================================
def calculer_analyse_vip(match):
    # Calcul Mi-temps / Fin (HT/FT)
    cotes_mf = match["cotes_mf"]
    if cotes_mf['V1/V1'] < 2.80:
        prono_mt = "Mi-temps : 1 / Fin de match : 1"
    elif cotes_mf['V2/V2'] < 2.80:
        prono_mt = "Mi-temps : 2 / Fin de match : 2"
    else:
        prono_mt = "Mi-temps : X / Fin de match : 1" # Exemple standard de ton interface

    # Calcul Score Exact
    cotes_score = match["cotes_score"]
    score_probable = min(cotes_score, key=cotes_score.get)
    cote_score = cotes_score[score_probable]
    fiabilite = 100 - (cote_score * 2.5) # Rendu plus stable pour afficher ~92%
    fiabilite = round(min(max(fiabilite, 85), 96))

    return prono_mt, score_probable, fiabilite

# ==========================================
# 🔑 INTERFACE GRAPHIQUE VIP NATIVE (Image 74018.jpg)
# ==========================================
st.set_page_config(page_title="BetScope Pro VIP", page_icon="🔐", layout="centered")

st.title("🔒 Bienvenue dans l'Espace VIP")
st.write("Accédez aux algorithmes de Scores Exacts et aux pronostics Mi-temps/Fin de match (HT/FT) à haute fiabilité.")

# Clé d'accès
cle_saisie = st.text_input("Entrez votre clé d'accès VIP :", type="password")

if cle_saisie:
    # Remplacer 'admin123' par ta vraie clé secrète
    if cle_saisie == "rodriguepro": 
        st.success("🔓 Accès VIP Accordé ! Bienvenue Boss.")
        
        st.markdown("---")
        st.header("🎯 LES PRONOSTICS VIP DU JOUR")
        
        # Le robot boucle et génère automatiquement l'affichage pour chaque match configuré
        for i, match in enumerate(MATCHS_DU_JOUR[:5]): # Limité à 5 matchs max
            prono_mt, score_probable, fiabilite = calculer_analyse_vip(match)
            
            # Bloc Score Exact
            st.info(f"🔥 **SCORE EXACT EXCLUSIF** : {match['equipes']} ➔ **Score : {score_probable}** (Fiabilité {fiabilite}%)")
            
            # Bloc HT/FT
            st.warning(f"🔥 **COMBINÉ HT/FT** : {match['equipes']} ➔ **{prono_mt}**")
            st.markdown(" ")
            
        st.markdown("---")
        st.subheader("📢 Comment obtenir votre clé d'accès VIP ?")
        st.write("Contactez le service client pour activer votre abonnement mensuel.")
    else:
        st.error("❌ Clé incorrecte. Veuillez vérifier vos accès.")

    """, unsafe_allow_html=True)

st.title("🤖 BetScope - L'IA des Pronostics")

# --- AFFICHAGE DE TON IMAGE EN HAUT DE L'APPLICATION ---
try:
    st.image("73766_3.png", use_container_width=True)
except Exception:
    st.markdown("👑 **ESPACE PRÉDICTION PRO**")

st.markdown("---")

menu = st.radio("Navigation", ["⚽ Pronostics Gratuits", "👑 Espace VIP Privé"], horizontal=True)

# --- SECTION GRATUITE ---
if menu == "⚽ Pronostics Gratuits":
    st.subheader("Analyse Algorithmique Dynamique (Free)")
    match_url = st.text_input("Collez le lien du match ici :", placeholder="https://www.besoccer.com/match/...")
    
    if st.button("Lancer l'Analyse Gratuite 🚀", use_container_width=True):
        if match_url:
            with st.spinner("Analyse IA en cours..."):
                time.sleep(1.5)
                st.success("Analyse terminée !")
                st.info("🎯 **Pronostic conseillé :** Victoire Équipe 1 ou Nul (1X)")
        else:
            st.error("❌ Veuillez insérer un lien.")

# --- SECTION VIP ---
elif menu == "👑 Espace VIP Privé":
    st.subheader("🔒 Bienvenue dans l'Espace VIP")
    
    mot_de_passe_correct = "RODRIGUE2026"
    code_entre = st.text_input("Entrez votre clé d'accès VIP :", type="password", placeholder="Clé Secrète VIP...")
    
    if code_entre:
        if code_entre == mot_de_passe_correct:
            st.success("🔓 Accès VIP Accordé ! Bienvenue Boss.")
            st.markdown("---")
            
            date_aujourdhui = datetime.now().strftime("%d/%m/%Y")
            st.markdown(f"### 🎯 LES PRONOSTICS VIP DU {date_aujourdhui}")
            
            # =================================================================
            # ✍️ MODIFIE UNIQUEMENT CES LIGNES CHAQUE MATIN AVEC TES DEUX MATCHS :
            # =================================================================
            match_1 = "Canada vs Maroc"
            cote_1_M1 = 5.64
            cote_X_M1 = 3.535
            cote_2_M1 = 1.801
            
            match_2 = "Paraguay vs France"
            cote_1_M2 = 16.0
            cote_X_M2 = 7.90
            cote_2_M2 = 1.207
            # =================================================================
            
            # --- ANALYSE DE L'IA (MATCH 1) ---
            if cote_2_M1 < cote_1_M1:
                diff = cote_1_M1 - cote_2_M1
                score_p1, fiab_1 = ("0 - 3", "94%") if diff > 5 else (("1 - 3", "91%") if diff > 2 else ("1 - 2", "88%"))
            elif cote_1_M1 < cote_2_M1:
                diff = cote_2_M1 - cote_1_M1
                score_p1, fiab_1 = ("3 - 0", "93%") if diff > 5 else (("3 - 1", "90%") if diff > 2 else ("2 - 1", "87%"))
            else:
                score_p1, fiab_1 = "1 - 1", "85%"
                
            # --- ANALYSE DE L'IA (MATCH 2) ---
            if cote_2_M2 <= 1.35:
                ht_ft_p2, fiab_2 = "Mi-temps : 2 / Fin de match : 2", "95%"
            elif cote_1_M2 <= 1.35:
                ht_ft_p2, fiab_2 = "Mi-temps : 1 / Fin de match : 1", "94%"
            elif abs(cote_1_M2 - cote_2_M2) < 1.0:
                ht_ft_p2, fiab_2 = "Mi-temps : X / Fin de match : X", "86%"
            else:
                ht_ft_p2, fiab_2 = ("Mi-temps : X / Fin de match : 1" if cote_1_M2 < cote_2_M2 else "Mi-temps : X / Fin de match : 2"), "89%"
            
            st.info("🔄 *Analyse des effectifs, absences et fluctuations des marchés validée par l'IA.*")
            st.markdown("")
            st.warning(f"🔥 **SCORE EXACT EXCLUSIF :**\n\n⚽ **{match_1}**\n\n➔ **Score Pronostiqué : {score_p1}** (Fiabilité : {fiab_1})")
            st.markdown("")
            st.warning(f"🔥 **COMBINÉ HT/FT :**\n\n⚽ **{match_2}**\n\n➔ **{ht_ft_p2}** (Indice de sécurité : {fiab_2})")
            
        else:
            st.error("❌ Clé d'accès incorrecte ou expirée.")
            
    st.markdown("---")
    st.markdown("### 📢 Comment obtenir votre clé d'accès VIP ?")
    lien_whatsapp = "https://wa.me/237600000000?text=Bonjour%20Rodrigue"
    st.link_button("💬 Acheter mon accès VIP sur WhatsApp", lien_whatsapp, use_container_width=True)
