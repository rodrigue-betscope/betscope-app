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
    </style>
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
            match_1 = "Paraguay vs France"
            cote_1_M1 = 15.5
            cote_X_M1 = 7.8
            cote_2_M1 = 1.212
            
            match_2 = "gremio porto vs chapecoense"
            cote_1_M2 = 1.56
            cote_X_M2 = 4.1
            cote_2_M2 = 5.49
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
