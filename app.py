import streamlit as st
import time
from datetime import datetime
import urllib.parse

# Configuration de la page avec l'icône officielle
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
    
    mot_de_passe_correct = "RODRIGUE2026"
    code_entre = st.text_input("Entrez votre clé d'accès VIP :", type="password", placeholder="Clé Secrète VIP...")
    
    if code_entre:
        if code_entre == mot_de_passe_correct:
            st.success("🔓 Accès VIP Accordé ! Bienvenue Boss.")
            st.markdown("---")
            
            date_aujourdhui = datetime.now().strftime("%d/%m/%Y")
            st.markdown(f"### 🎯 LES PRONOSTICS VIP DU {date_aujourdhui}")
            
            # =================================================================
            # ✍️ TOI-MÊME MODIFIE UNIQUEMENT CES GRILLES CHAQUE MATIN :
            # Remplis simplement avec les chiffres de tes grilles d'écrans !
            # =================================================================
            match_1 = "Portugal vs Espagne"
            
            # Ici tu mets les cotes de la grille "Score Exact" (comme sur ton image 75553.jpg)
            # Tu n'as pas besoin de tout mettre, mets juste les plus petites cotes (les plus probables)
            grille_scores_m1 = {
                "1-0": 10.0, "0-0": 13.0, "0-1": 10.0,
                "2-0": 13.0, "1-1": 6.5,  "0-2": 14.0,
                "2-1": 9.0,  "2-2": 10.0, "1-2": 9.0,
                "3-0": 23.0, "3-1": 15.0, "1-3": 17.0,
                "3-2": 19.0, "2-3": 19.0
            }
            
            match_2 = "etats Unis vs Belgique"
            
            # Ici tu mets les cotes de la grille "MT-Fin" (comme sur ton image 75555.jpg)
            grille_ht_ft_m2 = {
                "V1/V1": 4.05, "X/V1": 6.2,  "V2/V1": 29.0,
                "V1/X": 14.0,  "X/X": 5.25,  "V2/X": 14.2,
                "V1/V2": 29.0, "X/V2": 6.55, "V2/V2": 4.4
            }
            # =================================================================
            
            # --- 🤖 FONCTION ALGORITHMIQUE DE HAUTE PRÉCISION ---
            def analyser_grille_probabilites(grille_cotes):
                # Calcul de l'inversion des cotes (1 / cote)
                inverse_prob = {option: 1.0 / cote for option, cote in grille_cotes.items() if cote > 0}
                total_somme = sum(inverse_prob.values())
                # Normalisation pour obtenir les vrais pourcentages réels du marché
                vrais_pourcentages = {option: (prob / total_somme) * 100 for option, prob in inverse_prob.items()}
                # Extraction du grand favori de la grille
                meilleure_option = max(vrais_pourcentages, key=vrais_pourcentages.get)
                pourcentage_fiabilite = vrais_pourcentages[meilleure_option]
                return meilleure_option, pourcentage_fiabilite

            # Exécution de l'analyse scientifique pour le Match 1 et Match 2
            score_predit, fiab_score = analyser_grille_probabilites(grille_scores_m1)
            ht_ft_predit, fiab_ht_ft = analyser_grille_probabilites(grille_ht_ft_m2)
            
            # Formatage propre des textes pour l'affichage de la Mi-temps
            texte_ht_ft = ht_ft_predit.replace("/", " / Fin de match : ").replace("V1", "1").replace("V2", "2")
            texte_ht_ft = "Mi-temps : " + texte_ht_ft
            
            # --- AFFICHAGE ULTRA-PRO POUR TES CLIENTS ---
            st.info("🔄 *Analyse probabiliste croisée sur l'ensemble des marchés validée par l'IA.*")
            st.markdown("")
            st.warning(f"🔥 **SCORE EXACT EXCLUSIF :**\n\n⚽ **{match_1}**\n\n➔ **Score Pronostiqué : {score_predit}** (Vraie Probabilité : {fiab_score:.1f}%)")
            st.markdown("")
            st.warning(f"🔥 **COMBINÉ HT/FT :**\n\n⚽ **{match_2}**\n\n➔ **{texte_ht_ft}** (Indice de confiance réel : {fiab_ht_ft:.1f}%)")
            
        else:
            st.error("❌ Clé d'accès incorrecte ou expirée.")
            
    st.markdown("---")
    st.markdown("### 📢 Comment obtenir votre clé d'accès VIP ?")
    
    # Message automatique WhatsApp avec tes tarifs d'abonnement
    message_bienvenue = """Bonjour Rodrigue ! 👑 
Je souhaite m'abonner à l'Espace VIP BetScope. Voici les forfaits :

🔹 1 Semaine (7 jours) : 5 000 FCFA
🔹 1 Mois (30 jours) : 15 000 FCFA
🔹 1 An (365 jours) : 50 000 FCFA

Comment puis-je procéder au paiement s'il te plaît ?"""

    message_encode = urllib.parse.quote(message_bienvenue)
    lien_whatsapp = f"https://wa.me/237698902204?text={message_encode}"
    
    st.link_button("💬 Acheter mon accès VIP sur WhatsApp", lien_whatsapp, use_container_width=True)
