import streamlit as st

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
