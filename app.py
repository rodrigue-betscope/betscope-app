import os
import re
import math
import streamlit as st
from google import genai
from google.genai import types
import requests
from bs4 import BeautifulSoup

# =====================================================================
# CONFIGURATION DE L'APPLICATION STREAMLIT
# =====================================================================
st.set_page_config(page_title="Assistant IA Pronostics Sportifs", page_icon="⚽", layout="centered")

st.title("⚽ ASSISTANT IA DE PRONOSTICS SPORTIFS")
st.markdown("---")

# Récupération de la clé API depuis les secrets Streamlit ou saisie manuelle sécurisée
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("Entrez votre clé API Gemini", type="password")

if not api_key:
    st.warning("⚠️ Veuillez configurer votre clé API Gemini pour lancer l'analyse.")
    st.stop()

# Initialisation du client officiel Google GenAI
client = genai.Client(api_key=api_key)

# =====================================================================
# 1. FONCTION DE SCRAPING DES DONNÉES DU MATCH
# =====================================================================
def recuperer_donnees_match(url_match):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url_match, headers=headers, timeout=15)
        if response.status_code != 200:
            return f"Erreur de connexion au site (Code: {response.status_code})"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
            
        texte_brut = soup.get_text(separator=' ')
        texte_nettoye = re.sub(r'\s+', ' ', texte_brut).strip()
        return texte_nettoye[:40000]
    except Exception as e:
        return f"Erreur lors de la récupération des données : {str(e)}"

# =====================================================================
# 2. ALGORITHME MATHÉMATIQUE (LOI DE POISSON)
# =====================================================================
def calculer_probabilites_poisson(lambda_domicile, lambda_exterieur):
    def poisson(k, lamb):
        return (math.exp(-lamb) * (lamb ** k)) / math.factorial(k)

    meilleur_score = (0, 0)
    max_prob = 0.0
    prob_les_deux_marquent = 0.0
    prob_plus_2_5 = 0.0
    
    for i in range(6):
        for j in range(6):
            prob = poisson(i, lambda_domicile) * poisson(j, lambda_exterieur)
            if prob > max_prob:
                max_prob = prob
                meilleur_score = (i, j)
            if i > 0 and j > 0:
                prob_les_deux_marquent += prob
            if (i + j) > 2.5:
                prob_plus_2_5 += prob
                
    return meilleur_score, max_prob * 100, prob_les_deux_marquent * 100, prob_plus_2_5 * 100

# =====================================================================
# 3. ANALYSE IA (GEMINI 2.5 FLASH)
# =====================================================================
def analyser_match_avec_gemini(donnees_web):
    consigne_systeme = (
        "Tu es un expert mondial en analyses de données de football et algorithmes de paris sportifs. "
        "Ton but est d'extraire les métriques clés de ce texte de match : 5 derniers matchs de chaque équipe, "
        "historique des confrontations directes (H2H), buts marqués/encaissés à domicile/extérieur, "
        "dynamique d'attaque et faiblesses défensives. "
        "Donne des estimations chiffrées précises et réalistes."
    )
    
    prompt_utilisateur = f"""
    Analyse le texte brut suivant récupéré sur une page de statistiques de match. 
    Effectue un tri minutieux des données et génère un rapport de pronostic structuré.

    DONNÉES DU MATCH EXTRAITES : 
    {donnees_web}

    Génère une réponse structurée exactement comme ceci :
    
    ### 📊 ANALYSE DES COMPORTEMENTS ET DYNAMIQUES
    * **Équipe Domicile (Forme & Buts)** : [Synthèse rapide]
    * **Équipe Extérieur (Forme & Buts)** : [Synthèse rapide]
    
    ### 🎯 PROPOSITIONS DE MOYENNES ESTIMÉES POUR LES CALCULS (Crucial)
    * **Moyenne de buts attendus Équipe Domicile** : [Donne uniquement un chiffre décimal, ex: 1.65]
    * **Moyenne de buts attendus Équipe Extérieur** : [Donne uniquement un chiffre décimal, ex: 1.12]
    
    ### 🔮 PRONOSTIC PROBABLE
    * **Résultat Mi-temps (1, N ou 2)** : 
    * **Résultat Fin du match (1, N ou 2)** : 
    * **Les deux équipes marquent (Oui/Non)** : 
    * **Total de buts (Plus ou Moins de 2.5)** : 
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_utilisateur,
            config=types.GenerateContentConfig(
                system_instruction=consigne_systeme,
                temperature=0.2,
            )
        )
        return response.text
    except Exception as e:
        return f"Erreur lors de l'appel à l'IA Gemini : {str(e)}"

# =====================================================================
# INTERFACE UTILISATEUR STREAMLIT
# =====================================================================
url_cible = st.text_input("Collez le lien URL complet contenant les statistiques du match :")

if st.button("Lancer l'analyse du match", type="primary"):
    if not url_cible:
        st.error("Veuillez entrer une URL valide.")
    else:
        with st.spinner("Récupération et analyse des données en cours..."):
            donnees_brutes = recuperer_donnees_match(url_cible)
            
            if "Erreur" in donnees_brutes[:10]:
                st.error(donnees_brutes)
            else:
                st.info("Analyse croisée de l'historique par l'IA Gemini...")
                analyse_ia = analyser_match_avec_gemini(donnees_brutes)
                st.markdown(analyse_ia)
                
                st.info("Calcul de la matrice des scores exacts par la loi de Poisson...")
                try:
                    valeurs = re.findall(r"[-+]?\d*\.\d+|\d+", analyse_ia)
                    moyennes = [float(v) for v in valeurs if 0.2 <= float(v) <= 4.5]
                    
                    if len(moyennes) >= 2:
                        lambda_dom, lambda_ext = moyennes[0], moyennes[1]
                        score, prob_score, prob_btts, prob_over = calculer_probabilites_poisson(lambda_dom, lambda_ext)
                        
                        st.success("Analyse statistique terminée avec succès !")
                        st.markdown("### 📈 SYNTHÈSE STATISTIQUE MATHÉMATIQUE")
                        st.write(f"- **Score exact le plus probable** : {score[0]} - {score[1]} (Confiance : {prob_score:.2f}%)")
                        st.write(f"- **Probabilité que les deux équipes marquent** : {prob_btts:.2f}%")
                        st.write(f"- **Probabilité de Plus de 2.5 buts** : {prob_over:.2f}%")
                    else:
                        st.warning("Impossible d'isoler automatiquement les moyennes de buts pour le calcul de Poisson.")
                except Exception as e:
                    st.error(f"Erreur lors du calcul de Poisson : {e}")
