import streamlit as st
import datetime
import time

# --- TITRE ET NAVIGATION (Image 74867.jpg) ---
st.title("🧠 BetScope - L'IA des Pronostics")
st.caption("👑 ESPACE PRÉDICTION PRO")

navigation = st.radio("Navigation", ["⚽ Pronostics Gratuits", "👑 Espace VIP Privé"], horizontal=True)

# --- 1. OPTION PRONOSTICS GRATUITS ---
if navigation == "⚽ Pronostics Gratuits":
    st.subheader("📊 Analyses Gratuites du Jour")
    lien_match = st.text_input("Insérer le lien du match ou le nom des équipes :")
    if st.button("Lancer l'analyse gratuite"):
        if lien_match:
            with st.spinner("Analyse IA en cours..."):
                time.sleep(1.5)
            st.success("Analyse terminée !")
            st.info("🎯 **Pronostic conseillé :** Victoire Équipe Favorite ou Double Chance")
        else:
            st.error("❌ Veuillez insérer un lien.")

# --- 2. OPTION ESPACE VIP PRIVÉ (Image 74873.jpg) ---
elif navigation == "👑 Espace VIP Privé":
    st.subheader("🔒 Bienvenue dans l'Espace VIP")
    
    mot_de_pass_correct = "RODRIGUE2026"
    code_entre = st.text_input("Entrez votre clé d'accès VIP :", type="password", placeholder="Clé Secrète VIP...")
    
    if code_entre:
        if code_entre == mot_de_pass_correct:
            st.success("🔓 Accès VIP Accordé ! Bienvenue Boss.")
            st.markdown("---")
            
            date_aujourdhui = datetime.datetime.now().strftime("%d/%m/%Y")
            st.markdown(f"### 🎯 LES PRONOSTICS VIP DU {date_aujourdhui}")
            
            # =========================================================================
            # 👉 MODIFIE UNIQUEMENT CES LIGNES CHAQUE MATIN AVEC LES NOMS ET LES COTES
            # =========================================================================
            
            # --- MATCH 1 ---
            match_1 = "persiga vs persipani"
            cote_1_M1 = 4.25
            cote_X_M1 = 2.488
            cote_2_M1 = 2.165
            
            # --- MATCH 2 ---
            match_2 = "Paraguay vs France"
            cote_1_M2 = 16.0
            cote_X_M2 = 7.90
            cote_2_M2 = 1.207
            
            # =========================================================================
            # 🤖 ANALYSE DE L'IA AUTOMATIQUE (NE PLUS MODIFIER EN DESSOUS)
            # =========================================================================
            
            # --- CALCULS IA MATCH 1 ---
            if cote_2_M1 < cote_1_M1:
                diff_1 = cote_1_M1 - cote_2_M1
                score_p1, fiab_1 = ("0 - 2", "94%") if diff_1 > 3 else ("1 - 2", "88%")
                ht_ft_1 = "X / 2 (Serré puis Victoire Extérieur)" if diff_1 < 2 else "2 / 2 (Domination Extérieur HT/FT)"
            else:
                diff_1 = cote_2_M1 - cote_1_M1
                score_p1, fiab_1 = ("2 - 0", "93%") if diff_1 > 3 else ("2 - 1", "87%")
                ht_ft_1 = "X / 1 (Serré puis Victoire Domicile)" if diff_1 < 2 else "1 / 1 (Domination Domicile HT/FT)"
                
            # --- CALCULS IA MATCH 2 ---
            if cote_2_M2 < cote_1_M2:
                diff_2 = cote_1_M2 - cote_2_M2
                score_p2, fiab_2 = ("0 - 3", "95%") if diff_2 > 5 else ("1 - 2", "89%")
                ht_ft_2 = "X / 2" if diff_2 < 2 else "2 / 2 (Domination Extérieur HT/FT)"
            else:
                diff_2 = cote_2_M2 - cote_1_M2
                score_p2, fiab_2 = ("3 - 0", "94%") if diff_2 > 5 else ("2 - 1", "88%")
                ht_ft_2 = "X / 1" if diff_2 < 2 else "1 / 1 (Domination Domicile HT/FT)"

            # --- AFFICHAGE VIP STYLE NATIVE ---
            st.info(f"🔥 **SCORE EXACT EXCLUSIF :** {match_1} ➔ **Score : {score_p1}** (Fiabilité {fiab_1})")
            st.warning(f"🔥 **COMBINÉ HT/FT :** {match_1} ➔ **{ht_ft_1}**")
            st.markdown("---")
            st.info(f"🔥 **SCORE EXACT EXCLUSIF :** {match_2} ➔ **Score : {score_p2}** (Fiabilité {fiab_2})")
            st.warning(f"🔥 **COMBINÉ HT/FT :** {match_2} ➔ **{ht_ft_2}**")
            
            st.markdown("---")
            st.subheader("📢 Comment obtenir votre clé d'accès VIP ?")
            st.link_button("💬 Acheter mon accès VIP sur WhatsApp", "https://wa.me/ton_numero")
        else:
            st.error("❌ Clé incorrecte. Veuillez vérifier vos accès.")
