import numpy as np
import requests
from bs4 import BeautifulSoup
from scipy.stats import poisson


def extraire_donnees_url(url):
    """Scrape les données de l'URL fournie (Exemple générique adaptable).

    Remplacez les sélecteurs CSS selon le site cible (Flashscore, Footystats,
    etc.)
    """
    print(f"[1] Analyse de la page : {url}...")
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # --- EXEMPLE DE SIMULATION DE DONNÉES EXTRAITES ---
        # En pratique, l'IA ou le script doit cibler les balises contenant les stats
        # Ici on simule les moyennes historiques des 5-10 derniers matchs
        stats = {
            "buts_marques_dom": 1.85,  # Moyenne buts marqués à domicile
            "buts_encaisses_dom": 0.90,  # Moyenne buts encaissés à domicile
            "buts_marques_ext": 1.40,  # Moyenne buts marqués à l'extérieur
            "buts_encaisses_ext": 1.20,  # Moyenne buts encaissés à l'extérieur
            "moyenne_ligue_dom": 1.50,  # Constante de la ligue (domicile)
            "moyenne_ligue_ext": 1.20,  # Constante de la ligue (extérieur)
        }
        return stats
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse du lien : {e}")
        return None


def calculer_lambdas(stats):
    """Calcule la force d'attaque/défense mathématique pour obtenir les espérances

    de buts (Lambda).
    """
    # Force Domicile
    force_att_dom = stats["buts_marques_dom"] / stats["moyenne_ligue_dom"]
    force_def_dom = stats["buts_encaisses_dom"] / stats["moyenne_ligue_ext"]

    # Force Extérieur
    force_att_ext = stats["buts_marques_ext"] / stats["moyenne_ligue_ext"]
    force_def_ext = stats["buts_encaisses_ext"] / stats["moyenne_ligue_dom"]

    # Espérance de buts finale (Full Time)
    lambda_dom_ft = force_att_dom * force_def_ext * stats["moyenne_ligue_dom"]
    lambda_ext_ft = force_att_ext * force_def_dom * stats["moyenne_ligue_ext"]

    # Espérance de buts à la Mi-temps (Généralement 40% des buts du match)
    lambda_dom_ht = lambda_dom_ft * 0.42
    lambda_ext_ht = lambda_ext_ft * 0.42

    return lambda_dom_ht, lambda_ext_ht, lambda_dom_ft, lambda_ext_ft


def simuler_loi_poisson(lambda_dom, lambda_ext, max_buts=5):
    """Génère la matrice des probabilités pour chaque score exact."""
    matrice = np.zeros((max_buts + 1, max_buts + 1))
    for i in range(max_buts + 1):
        for j in range(max_buts + 1):
            prob_dom = poisson.pmf(i, lambda_dom)
            prob_ext = poisson.pmf(j, lambda_ext)
            matrice[i, j] = prob_dom * prob_ext
    return matrice


def analyser_match(url):
    """Fonction principale d'analyse de probabilités."""
    stats = extraire_donnees_url(url)
    if not stats:
        return

    lam_dom_ht, lam_ext_ht, lam_dom_ft, lam_ext_ft = calculer_lambdas(stats)

    # 1. Analyse Mi-temps (HT)
    matrice_ht = simuler_loi_poisson(lam_dom_ht, lam_ext_ht)
    prob_nul_ht = np.sum(np.diag(matrice_ht))  # Somme des scores 0-0, 1-1, 2-2

    # Score exact Mi-temps le plus probable
    i_ht, j_ht = np.unravel_index(np.argmax(matrice_ht), matrice_ht.shape)

    # 2. Analyse Fin du Match (FT)
    matrice_ft = simuler_loi_poisson(lam_dom_ft, lam_ext_ft)

    prob_dom_ft = np.sum(np.triu(matrice_ft, 1))  # Extérieur gagne
    prob_ext_ft = np.sum(np.tril(matrice_ft, -1))  # Domicile gagne
    prob_nul_ft = np.sum(np.diag(matrice_ft))

    i_ft, j_ft = np.unravel_index(np.argmax(matrice_ft), matrice_ft.shape)

    # 3. Calcul du scénario : Nul Mi-temps / Victoire n'importe qui Fin de match
    # Mathématiquement corrélé : P(Nul HT) * P(Pas Nul FT)
    prob_scenario_specifique = prob_nul_ht * (1 - prob_nul_ft)

    # --- AFFICHAGE DU RAPPORT MATHÉMATIQUE ---
    print("\n" + "=" * 50)
    print("📊 RAPPORT DE PRÉDICTION MATHÉMATIQUE (LOI DE POISSON)")
    print("=" * 50)
    print(
        f"⚽ Espérance buts Match : Domicile {lam_dom_ft:.2f} - {lam_ext_ft:.2f} Extérieur"
    )
    print(
        f"⏱️ Espérance buts Mi-temps : Domicile {lam_dom_ht:.2f} - {lam_ext_ht:.2f} Extérieur"
    )
    print("-" * 50)

    print(f"🎯 SCORE EXACT MI-TEMPS MAXIMUM : {i_ht} - {j_ht}")
    print(f"⏳ Probabilité Nul à la Mi-temps : {prob_nul_ht * 100:.2f}%")
    print(f"   -> Probabilité exacte du 0-0 HT : {matrice_ht[0, 0] * 100:.2f}%")
    print("-" * 50)

    print(f"🏆 SCORE EXACT FIN DE MATCH MAXIMUM : {i_ft} - {j_ft}")
    print(f"📈 Tendance 1X2 Fin de Match :")
    print(f"   -> Victoire Domicile : {prob_ext_ft * 100:.2f}%")
    print(f"   -> Match Nul : {prob_nul_ft * 100:.2f}%")
    print(f"   -> Victoire Extérieur : {prob_dom_ft * 100:.2f}%")
    print("-" * 50)

    print(f"🔥 SCÉNARIO REQUIS (Nul HT / Gain Équipe 1 ou 2 FT) :")
    print(f"   -> Fiabilité calculée : {prob_scenario_specifique * 100:.2f}%")
    print("=" * 50)


# --- ZONE D'EXÉCUTION ---
if __name__ == "__main__":
    # Collez le lien de votre choix ici pour exécuter l'analyse
    lien_match = "https://exemple-football-stats.com"
    analyser_match(lien_match)
