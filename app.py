def generer_analyse_vip_complete(cible_match):
  """Génère un rapport complet et prépare le texte pour la voix IA."""
  model = genai.GenerativeModel(model_name="gemini-1.5-pro")

  prompt = f"""
    Tu es l'algorithme d'analyse prédictive principal de l'application VIP "Rodrigue Pro Puissant Prédiction".
    Ton but est de fournir une analyse d'expert mathématique, historique et contextuelle pour le match ou le lien suivant : {cible_match}
    
    Compile les éléments suivants :
    1. JOURNAL HISTORIQUE (H2H) : Comment les précédents matchs entre ces équipes se sont déroulés ? Qui a gagné ? Combien de buts ont été marqués en moyenne ?
    2. CONTEXTE ACTUEL : Les blessures récentes, les joueurs clés absents ou suspendus, la météo et son impact.
    3. FLUX FINANCIERS : Les mouvements de cotes importants sur le marché 1X2.

    Génère un rapport VIP structuré en français avec ces sections exactes :

    📖 [1] LE JOURNAL DES CONFRONTATIONS (H2H)
    - Historique des derniers face-à-face entre les deux équipes.
    - Analyse des buts marqués lors de leurs confrontations.
    - Dynamique récente et état de forme général.

    📋 [2] INFOS TERRAIN & MÉTÉO
    - Liste des joueurs blessés ou absents importants pour ce match.
    - Conditions météo locales et impact attendu sur le score.

    📈 [3] PROBABILITÉS NETTES (1X2 & Doubles Chances)
    - % Victoire Domicile : [Indiquer le % précis]
    - % Match Nul : [Indiquer le % précis]
    - % Victoire Extérieur : [Indiquer le % précis]
    - Choix conseillé ferme : (1, X, 2, 1X ou X2)

    ⚽ [4] SCORES EXACTS & MI-TEMPS (Haute Précision)
    - Score Exact Final le plus probable (ex: 2-1).
    - Score Exact à la Mi-temps (ex: 1-0).
    - Scénario Mi-temps / Fin du match (ex: 1/1, X/1, X/2).
    - Les deux équipes marquent : [Oui/Non + Pourcentage].

    🎯 [5] OPTIONS AVANCÉES & COMBOS PREMIUM
    - Over / Under : (Plus ou moins de 1.5 buts et 2.5 buts dans le match).
    - Spécial : Une équipe gagne-t-elle spécifiquement la 2ème mi-temps ?
    - Combo Premium Rentable : (Ex: Victoire Domicile + Plus de 2.5 buts).
    """

  try:
    response = model.generate_content(prompt)
    return response.text
  except Exception as e:
    return f"❌ Erreur lors de l'analyse : {str(e)}"
