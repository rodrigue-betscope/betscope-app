import requests
import numpy as np
import scipy.stats as stats

class MonRobotPredicteur:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api-sports.io"
        self.headers = {
            'x-rapidapi-host': "v3.football.api-sports.io",
            'x-rapidapi-key': api_key
        }

    def analyser_et_predire_match(self, fixture_id, cote_dom, cote_nul, cote_ext, manual_xg_dom=None, manual_xg_ext=None):
        """
        Fait TOUT le travail : Récupération API, Calcul de Poisson, HT/FT, xG, et Détection de Value.
        """
        print(f"🔄 Analyse du match (ID: {fixture_id}) en cours...")
        
        # 1. Extraction automatique des statistiques d'équipes via l'API
        endpoint = f"{self.base_url}fixtures/statistics"
        response = requests.get(endpoint, headers=self.headers, params={'fixture': fixture_id})
        
        # Initialisation des xG par défaut si l'API ou le match n'a pas encore de xG calculé
        xg_dom = manual_xg_dom if manual_xg_dom else 1.65
        xg_ext = manual_xg_ext if manual_xg_ext else 1.20

        if response.status_code == 200:
            data = response.json().get('response', [])
            if len(data) >= 2:
                # Tentative d'extraction des Expected Goals (xG) directement depuis l'API si disponibles
                for team_data in data:
                    stats_list = team_data.get('statistics', [])
                    for s in stats_list:
                        if s.get('type') == 'Expected Goals' and s.get('value'):
                            if team_data['team']['id'] == data[0]['team']['id']:
                                xg_dom = float(s['value'])
                            else:
                                xg_ext = float(s['value'])

        print(f"📊 xG retenus pour l'analyse -> Domicile : {xg_dom} | Extérieur : {xg_ext}")

        # 2. Algorithme de Poisson pour la Fin du Match (Full-Time)
        matrice_ft = self._calculer_matrice_poisson(xg_dom, xg_ext)
        
        # 3. Algorithme de Poisson pour la Mi-Temps (Half-Time)
        # Statistiquement, environ 45% des buts d'un match sont marqués en 1ère mi-temps
        matrice_ht = self._calculer_matrice_poisson(xg_dom * 0.45, xg_ext * 0.45)

        # 4. Calcul des Probabilités 1N2 (Fin de match)
        prob_nul_ft = np.diag(matrice_ft).sum()
        prob_dom_ft = np.tril(matrice_ft, -1).sum()
        prob_ext_ft = np.triu(matrice_ft, 1).sum()

        # 5. Calcul des Probabilités 1N2 (Mi-temps)
        prob_nul_ht = np.diag(matrice_ht).sum()
        prob_dom_ht = np.tril(matrice_ht, -1).sum()
        prob_ext_ht = np.triu(matrice_ht, 1).sum()

        # 6. Scénarios de Buts (Plus/Moins de 2.5)
        prob_moins_25 = 0
        for i in range(3):
            for j in range(3):
                if i + j < 2.5:
                    prob_moins_25 += matrice_ft[i, j]
        prob_plus_25 = 1 - prob_moins_25

        # Les deux équipes marquent (BTTS)
        prob_btts = 1 - (matrice_ft[0, :].sum() + matrice_ft[:, 0].sum() - matrice_ft[0, 0])

        # 7. Restitution des résultats clairs
        print("\n==================================================")
        print("🎯 RAPPORT DE PRÉDICTION MATHÉMATIQUE (PRÉCISION MAX)")
        print("==================================================")
        
        print(f"\n🔮 PROBABILITÉS MI-TEMPS (HT) :")
        print(f" • Victoire Domicile : {prob_dom_ht:.2%}")
        print(f" • Match Nul : {prob_nul_ht:.2%}")
        print(f" • Victoire Extérieur : {prob_ext_ht:.2%}")

        print(f"\n🔮 PROBABILITÉS FIN DE MATCH (FT) :")
        print(f" • Victoire Domicile : {prob_dom_ft:.2%}")
        print(f" • Match Nul : {prob_nul_ft:.2%}")
        print(f" • Victoire Extérieur : {prob_ext_ft:.2%}")

        print(f"\n⚽ MARCHÉS ALTERNATIFS :")
        print(f" • Plus de 2.5 Buts : {prob_plus_25:.2%}")
        print(f" • Les deux équipes marquent : {prob_btts:.2%}")

        # 8. ANALYSE DES VALUE BETS (Où se situe l'argent ?)
        print(f"\n📉 RECHERCHE DE VALUE BETS (Comparaison avec vos Cotes) :")
        self._verifier_value("Victoire Domicile (FT)", prob_dom_ft, cote_dom)
        self._verifier_value("Match Nul (FT)", prob_nul_ft, cote_nul)
        self._verifier_value("Victoire Extérieur (FT)", prob_ext_ft, cote_ext)

        # 9. TOP SCORES EXACTS (Fin de match)
        print(f"\n🎲 TOP SCORES EXACTS LES PLUS PROBABLES :")
        scores_tries = sorted(
            [(i, j, matrice_ft[i, j]) for i in range(4) for j in range(4)],
            key=lambda x: x[2], reverse=True
        )[:3]
        for score in scores_tries:
            print(f" • Score : {score[0]} - {score[1]} (Probabilité : {score[2]:.2%})")
        print("==================================================\n")

    def _calculer_matrice_poisson(self, lambda_dom, lambda_ext, max_buts=6):
        matrice = np.zeros((max_buts, max_buts))
        for i in range(max_buts):
            for j in range(max_buts):
                matrice[i, j] = stats.poisson.pmf(i, lambda_dom) * stats.poisson.pmf(j, lambda_ext)
        return matrice

    def _verifier_value(self, nom_pari, probabilite, cote):
        indice_value = probabilite * cote
        if indice_value > 1.05: # Value nette supérieure à 5% de marge
            print(f" 🟩 VALUE TROUVÉE -> [{nom_pari}] | Votre Cote : {cote} | Avantage : +{(indice_value-1)*100:.1f}%")
        else:
            print(f" 🟥 Pas de value sur [{nom_pari}] (Cote : {cote})")

# =====================================================================
# ÉTAPE FINALE : EXÉCUTION DU TEST
# =====================================================================
if __name__ == "__main__":
    # Remplacer par votre clé API-Sports / API-Football
    MA_CLE_API = "VOTRE_CLE_API_ICI" 
    
    bot = MonRobotPredicteur(MA_CLE_API)
    
    # EXEMPLE DE MATCH : Vous donnez l'ID du match, et les 3 cotes de votre bookmaker
    # Si vous n'avez pas encore les xG officiels, vous pouvez forcer vos propres estimations à la fin.
    ID_MATCH_EXEMPLE = 1044322  
    COTE_1 = 2.10
    COTE_N = 3.40
    COTE_2 = 3.80
    
    # Lancement complet
    bot.analyser_et_predire_match(
        fixture_id=ID_MATCH_EXEMPLE,
        cote_dom=COTE_1,
        cote_nul=COTE_N,
        cote_ext=COTE_2,
        manual_xg_dom=2.15, # Optionnel : Entrez vos xG précis si l'API n'a pas encore le live
        manual_xg_ext=1.10  # Optionnel
    )
