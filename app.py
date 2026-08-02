import os
import re
import math
from google import genai
from google.genai import types
import requests
from bs4 import BeautifulSoup

# =====================================================================
# 1. CONFIGURATION DE LA NOUVELLE CLÉ GEMINI (Format AQ....)
# =====================================================================
# Remplacez par votre nouvelle clé API Gemini
GEMINI_API_KEY = "VOTRE_CLE_API_ICI" 

# Initialisation du nouveau client officiel Google GenAI (Norme 2025/2026)
client = genai.Client(api_key=GEMINI_API_KEY)

# =====================================================================
# 2. FONCTION DE SCRAPING DES DONNÉES DU MATCH
# =====================================================================
def recuperer_donnees_match(url_match):
    """
    Extrait le contenu texte de la page du match pour l'analyse.
    Pour contourner les blocages, on utilise un en-tête utilisateur standard.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url_match, headers=headers, timeout=15)
        if response.status_code != 200:
            return f"Erreur de connexion au site (Code: {response.status_code})"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraction du texte global de la page (historique, stats, cotes)
        # Supprime les scripts et balises inutiles pour optimiser les jetons
        for script in soup(["script", "style"]):
            script.decompose()
            
        texte_brut = soup.get_text(separator=' ')
        # Nettoyage des espaces superflus
        texte_nettoye = re.sub(r'\s+', ' ', texte_brut).strip()
        
        # On limite le texte aux 8000 premiers mots pour rester performant
        return texte_nettoye[:40000]
    except Exception as e:
        return f"Erreur lors de la récupération des données : {str(e)}"

# =====================================================================
# 3. ALGORITHME MATHÉMATIQUE (LOI DE POISSON) POUR LES SCORES EXACTS
# =====================================================================
def calculer_probabilites_poisson(lambda_domicile, lambda_exterieur):
    """
    Calcule mathématiquement le score exact le plus probable.
    """
    def poisson(k, lamb):
        return (math.exp(-lamb) * (lamb ** k)) / math.factorial(k)

    meilleur_score = (0, 0)
    max_prob = 0.0
    prob_les_deux_marquent = 0.0
    prob_plus_2_5 = 0.0
    
    # Analyse matricielle des scores de 0-0 à 5-5
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
# 4. DIRECTEUR DE PRONOSTIC (INTELLIGENCE ARTIFICIELLE GEMINI)
# =====================================================================
def analyser_match_avec_gemini(donnees_web):
    """
    Demande à Gemini 2.5 Flash d'agir en parieur professionnel et statisticien.
    En utilisant search, il extrait et croise les données temps réel.
    """
    
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

    FALSIFICATION INTERDITE. Génère une réponse structurée exactement comme ceci :
    
    ### 📊 ANALYSE DES COMPORTEMENTS ET DYNAMIQUES
    * **Équipe Domicile (Forme & Buts)** : [Mets ici une synthèse rapide de leurs 5 derniers matchs et capacité à marquer]
    * **Équipe Extérieur (Forme & Buts)** : [Mets ici une synthèse rapide de leurs 5 derniers matchs et capacité à encaisser]
    
    ### 🎯 PROPOSITIONS DE MOYENNES ESTIMÉES POUR LES CALCULS (Crucial)
    * **Moyenne de buts attendus Équipe Domicile** : [Donne uniquement un chiffre décimal, ex: 1.65]
    * **Moyenne de buts attendus Équipe Extérieur** : [Donne uniquement un chiffre décimal, ex: 1.12]
    
    ### 🔮 PRONOSTIC PROBABLE (Seulement si l'indice de confiance dépasse 80%)
    * **Résultat Mi-temps (1, N ou 2)** : 
    * **Résultat Fin du match (1, N ou 2)** : 
    * **Les deux équipes marquent (Oui/Non)** : 
    * **Total de buts (Plus ou Moins de 2.5)** : 
    """

    try:
        # Appel du modèle moderne gemini-2.5-flash avec outils de recherche Google activés
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_utilisateur,
            config=types.GenerateContentConfig(
                system_instruction=consigne_systeme,
                temperature=0.2,  # Température basse pour limiter l'imagination et privilégier la rigueur logique
            )
        )
        return response.text
    except Exception as e:
        return f"Erreur lors de l'appel à l'IA Gemini : {str(e)}"

# =====================================================================
# 5. EXÉCUTION DU PROGRAMME PRINCIPAL
# =====================================================================
if __name__ == "__main__":
    print("=== ASSISTANT IA DE PRONOSTICS SPORTIFS - GEMINI v2.5 ===")
    
    # Étape A: Entrer l'URL du match (ex: de Flashscore, Sofascore, WhoScored, etc.)
    url_cible = input("\nCollez le lien URL complet contenant les statistiques du match : ")
    
    print("\n[1/3] Récupération des données en temps réel sur la page web...")
    donnees_brutes = recuperer_donnees_match(url_cible)
    
    if "Erreur" in donnees_brutes[:10]:
        print(donnees_brutes)
    else:
        print("[2/3] Analyse croisée de l'historique par l'IA Gemini...")
        analyse_ia = analyser_match_avec_gemini(donnees_brutes)
        print("\n" + analyse_ia)
        
        print("\n[3/3] Calcul de la matrice des scores exacts par l'algorithme mathématique...")
        # Extraction automatique des moyennes suggérées par Gemini pour la loi de Poisson
        try:
            valeurs = re.findall(r"[-+]?\d*\.\d+|\d+", analyse_ia)
            # Recherche de valeurs décimales plausibles (entre 0.2 et 4.5 buts par match)
            moyennes = [float(v) for v in valeurs if 0.2 <= float(v) <= 4.5]
            
            if len(moyennes) >= 2:
                lambda_dom, lambda_ext = moyennes[0], moyennes[1]
                
                score, prob_score, prob_btts, prob_over = calculer_probabilites_poisson(lambda_dom, lambda_ext)
                
                print("\n================ 📈 SYNTHÈSE STATISTIQUE MATHÉMATIQUE ================")
                print(f" * Score exact le plus probable : {score[0]} - {score[1]} (Confiance mathématique: {prob_score:.2f}%)")
                print(f" * Probabilité que les deux équipes marquent : {prob_btts:.2f}%")
                print(f" * Probabilité de Plus de 2.5 buts dans le match : {prob_over:.2f}%")
                print("=======================================================================")
            else:
                print("\n⚠️ Impossible d'isoler les moyennes de buts dans l'analyse pour calculer le score exact exact.")
        except Exception as e:
            print(f"\n⚠️ Erreur lors du calcul automatique de Poisson : {e}")

    print("\nAnalyse terminée. Note importante : Aucun algorithme n'offre 100% de certitude. Restez responsable.")
    
