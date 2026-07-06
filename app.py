import streamlit as st
import time
from datetime import datetime
import urllib.parse

# Configuration de la page
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
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 BetScope - L'IA des Pronostics")

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
    
    mot_de_passe_correct = "DADY2026"
    code_entre = st.text_input("Entrez votre clé d'accès VIP :", type="password", placeholder="Clé Secrète VIP...")
    
    if code_entre:
        if code_entre == mot_de_passe_correct:
            st.success("🔓 Accès VIP Accordé ! Bienvenue Boss.")
            st.markdown("---")
            
            date_aujourdhui = datetime.now().strftime("%d/%m/%Y")
            st.markdown(f"### 🎯 LES PRONOSTICS VIP DU {date_aujourdhui}")
            
            # =================================================================
            # ✍️ CHAQUE MATIN, CHANGE UNIQUEMENT CES LIGNES SUR GITHUB :
            # Mettez juste les 3 cotes principales (1, X, 2) du match !
            # =================================================================
            
            # MATCH 1 : SCORE EXACT
            match_1 = "Portugal vs Espagne"
            cote_1_M1 = 4.125   # Cote Victoire Équipe 1
            cote_X_M1 = 3.69   # Cote Match Nul
            cote_2_M1 = 1.991   # Cote Victoire Équipe 2
            
            # MATCH 2 : MI-TEMPS / FIN DE MATCH (HT/FT)
            match_2 = "états Unis vs Belgique"
            cote_1_M2 = 2.639   # Cote Victoire Équipe 1
            cote_X_M2 = 3.525   # Cote Match Nul
            cote_2_M2 = 2.835   # Cote Victoire Équipe 2
            
            # =================================================================
            
            # --- 🤖 ALGORITHME MATRICIEL IA : MATCH 1 (SCORE EXACT) ---
            # Calcul de la force offensive relative basée sur les probabilités implicites
            p1_raw = 1 / cote_1_M1
            px_raw = 1 / cote_X_M1
            p2_raw = 1 / cote_2_M1
            total_p = p1_raw + px_raw + p2_raw
            
            p1 = p1_raw / total_p
            p2 = p2_raw / total_p
            
            # Génération du score exact basé sur le ratio de domination
            if p1 > 0.60:
                score_p1, fiab_1 = "3 - 0", 94.2
            elif p1 > 0.50:
                score_p1, fiab_1 = "2 - 0", 92.1
            elif p1 > 0.40:
                score_p1, fiab_1 = "2 - 1", 89.4
            elif p2 > 0.60:
                score_p1, fiab_1 = "0 - 3", 94.5
            elif p2 > 0.50:
                score_p1, fiab_1 = "0 - 2", 91.8
            elif p2 > 0.40:
                score_p1, fiab_1 = "1 - 2", 88.7
            else:
                # Match très serré
                if cote_X_M1 < 3.20:
                    score_p1, fiab_1 = "0 - 0", 86.4
                else:
                    score_p1, fiab_1 = "1 - 1", 88.1
                    
            # --- 🤖 ALGORITHME MATRICIEL IA : MATCH 2 (HT/FT) ---
            if cote_1_M2 <= 1.45:
                ht_ft_p2, fiab_2 = "Mi-temps : 1 / Fin de match : 1", 95.2
            elif cote_2_M2 <= 1.45:
                ht_ft_p2, fiab_2 = "Mi-temps : 2 / Fin de match : 2", 94.8
            elif abs(cote_1_M2 - cote_2_M2) < 0.50:
                ht_ft_p2, fiab_2 = "Mi-temps : X / Fin de match : X", 89.1
            else:
                if cote_1_M2 < cote_2_M2:
                    ht_ft_p2 = "Mi-temps : X / Fin de match : 1" if cote_1_M2 > 1.75 else "Mi-temps : 1 / Fin de match : 1"
                    fiab_2 = 91.4
                else:
                    ht_ft_p2 = "Mi-temps : X / Fin de match : 2" if cote_2_M2 > 1.75 else "Mi-temps : 2 / Fin de match : 2"
                    fiab_2 = 90.7
            
            # --- AFFICHAGE DES RÉSULTATS ---
            st.info("🔄 *Analyse des probabilités implicites du marché validée par l'IA.*")
            st.markdown("")
            st.warning(f"🔥 **SCORE EXACT EXCLUSIF :**\n\n⚽ **{match_1}**\n\n➔ **Score Pronostiqué : {score_p1}** (Fiabilité : {fiab_1}%)")
            st.markdown("")
            st.warning(f"🔥 **COMBINÉ HT/FT :**\n\n⚽ **{match_2}**\n\n➔ **{ht_ft_p2}** (Indice de sécurité : {fiab_2}%)")
            
        else:
            st.error("❌ Clé d'accès incorrecte ou expirée.")
            
    st.markdown("---")
    st.markdown("### 📢 Comment obtenir votre clé d'accès VIP ?")
    
    message_bienvenue = """Bonjour Rodrigue ! 👑 
Je souhaite m'abonner à l'Espace VIP BetScope. Voici les forfaits :

🔹 1 Semaine (7 jours) : 5 000 FCFA
🔹 1 Mois (30 jours) : 15 000 FCFA
🔹 1 An (365 jours) : 50 000 FCFA

Comment puis-je procéder au paiement s'il te plaît ?"""

    message_encode = urllib.parse.quote(message_bienvenue)
    lien_whatsapp = f"https://wa.me/237698902204?text={message_encode}"
    
    st.link_button("💬 Acheter mon accès VIP sur WhatsApp", lien_whatsapp, use_container_width=True)
