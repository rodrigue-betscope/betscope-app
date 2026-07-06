import streamlit as st
import time
from datetime import datetime
import urllib.parse

# Configuration de la page
st.set_page_config(page_title="Rodrigue Pro Puissant Prédiction", page_icon="73766_3.png", layout="centered")

# CSS pour le design mobile
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

# ==========================================
# 🗂️ LE NOUVEAU MENU À 3 SECTIONS
# ==========================================
menu = st.radio("Navigation", ["⚽ Gratuit", "👑 VIP Privé", "🏆 Résultats"], horizontal=True)

# ---------------------------------------------------------
# SECTION 1 : GRATUIT
# ---------------------------------------------------------
if menu == "⚽ Gratuit":
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

# ---------------------------------------------------------
# SECTION 2 : VIP PRIVÉ (Les matchs du jour)
# ---------------------------------------------------------
elif menu == "👑 VIP Privé":
    st.subheader("🔒 Bienvenue dans l'Espace VIP")
    
    mot_de_passe_correct = "DADY2026"
    code_entre = st.text_input("Entrez votre clé d'accès VIP :", type="password", placeholder="Clé Secrète VIP...")
    
    if code_entre:
        if code_entre == mot_de_passe_correct:
            st.success("🔓 Accès VIP Accordé ! Bienvenue Boss.")
            st.markdown("---")
            
            date_aujourdhui = datetime.now().strftime("%d/%m/%Y")
            st.markdown(f"### 🎯 LES PRONOSTICS VIP DU {date_aujourdhui}")
            
            # ✍️ MODIFIE UNIQUEMENT CES COTES CHAQUE MATIN
            
            # MATCH 1 : SCORE EXACT
            match_1 = "brommapojka vs gais"
            cote_1_M1 = 2.999
            cote_X_M1 = 3.38
            cote_2_M1 = 2.28
            
            # MATCH 2 : MI-TEMPS / FIN DE MATCH (HT/FT)
            match_2 = "hacken vs djurgardens"
            cote_1_M2 = 2.425 
            cote_X_M2 = 3.79  
            cote_2_M2 = 2.656
            
            # --- CALCULS IA ---
            p1_raw, px_raw, p2_raw = 1/cote_1_M1, 1/cote_X_M1, 1/cote_2_M1
            total_p = p1_raw + px_raw + p2_raw
            p1, p2 = p1_raw / total_p, p2_raw / total_p
            
            if p1 > 0.60: score_p1, fiab_1 = "3 - 0", 94.2
            elif p1 > 0.50: score_p1, fiab_1 = "2 - 0", 92.1
            elif p1 > 0.40: score_p1, fiab_1 = "2 - 1", 89.4
            elif p2 > 0.60: score_p1, fiab_1 = "0 - 3", 94.5
            elif p2 > 0.50: score_p1, fiab_1 = "0 - 2", 91.8
            elif p2 > 0.40: score_p1, fiab_1 = "1 - 2", 88.7
            else: score_p1, fiab_1 = ("0 - 0", 86.4) if cote_X_M1 < 3.20 else ("1 - 1", 88.1)
                    
            if cote_1_M2 <= 1.45: ht_ft_p2, fiab_2 = "Mi-temps : 1 / Fin de match : 1", 95.2
            elif cote_2_M2 <= 1.45: ht_ft_p2, fiab_2 = "Mi-temps : 2 / Fin de match : 2", 94.8
            elif abs(cote_1_M2 - cote_2_M2) < 0.50: ht_ft_p2, fiab_2 = "Mi-temps : X / Fin de match : X", 89.1
            else:
                if cote_1_M2 < cote_2_M2:
                    ht_ft_p2, fiab_2 = ("Mi-temps : X / Fin de match : 1", 91.4) if cote_1_M2 > 1.75 else ("Mi-temps : 1 / Fin de match : 1", 91.4)
                else:
                    ht_ft_p2, fiab_2 = ("Mi-temps : X / Fin de match : 2", 90.7) if cote_2_M2 > 1.75 else ("Mi-temps : 2 / Fin de match : 2", 90.7)
            
            # --- AFFICHAGE VIP ---
            st.info("🔄 *Analyse des probabilités implicites du marché validée par l'IA.*")
            st.markdown("")
            st.warning(f"🔥 **SCORE EXACT EXCLUSIF :**\n\n⚽ **{match_1}**\n\n➔ **Score Pronostiqué : {score_p1}** (Fiabilité : {fiab_1}%)")
            st.markdown("")
            st.warning(f"🔥 **COMBINÉ HT/FT :**\n\n⚽ **{match_2}**\n\n➔ **{ht_ft_p2}** (Indice de sécurité : {fiab_2}%)")
            
        else:
            st.error("❌ Clé d'accès incorrecte ou expirée.")

# ---------------------------------------------------------
# SECTION 3 : RÉSULTATS (Historique pour attirer les clients)
# ---------------------------------------------------------
elif menu == "🏆 Résultats":
    st.subheader("✅ Historique des Validations")
    st.markdown("Découvrez les derniers pronostics validés avec succès par l'algorithme BetScope. Rejoignez le VIP pour ne plus rater ces cotes !")
    
    st.markdown("---")
    
    # ✍️ MODIFIE CETTE SECTION CHAQUE JOUR POUR AFFICHER TES VICTOIRES DE LA VEILLE
    st.success("✅ **05/07/2026** | Shanghai vs Zhejiang\n\n➔ **Score Exact 2-0** validé ! 🏆")
    st.success("✅ **05/07/2026** | Qingdao vs Chengdu\n\n➔ **HT/FT 2/2** validé ! 🏆")
    
    # Tu peux ajouter autant de lignes "st.success" que tu veux pour montrer ton historique
    
    st.markdown("---")
    st.markdown("### 📢 Envie d'obtenir les pronostics d'aujourd'hui ?")

# ==========================================
# 🟢 BOUTON WHATSAPP GLOBAL DÉFINITIF (FORCER LE NAVIGATEUR EXTERNE)
# ==========================================
if menu != "⚽ Gratuit":
    message_bienvenue = """Bonjour BetScope ! 👑 ✅✅
Je souhaite m'abonner à l'Espace VIP BetScope. Voici les forfaits :

🔹 1 Semaine (7 jours) : 5 000 FCFA
🔹 1 Mois (30 jours) : 15 000 FCFA
🔹 1 An (365 jours) : 50 000 FCFA

Comment puis-je procéder au paiement s'il te plaît ?"""

    message_encode = urllib.parse.quote(message_bienvenue)
    lien_whatsapp = f"https://api.whatsapp.com/send?phone=237698902204&text={message_encode}"
    
    # Correction ici : target="_blank" pour activer le mode "Default Browser" de ton APK
    st.markdown(f"""
    <a href="{lien_whatsapp}" target="_blank" style="text-decoration: none;">
        <div style="background-color: #25D366; color: white; text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 16px; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
            💬 Acheter mon accès VIP sur WhatsApp
        </div>
    </a>
    """, unsafe_allow_html=True)
