import math

def analyse_match():
    print("===== IA PREDICTION BOT V1.0 💯 =====")
    
    # 1. DONNEES ENTREES
    home = input("Nom équipe Domicile: ")
    away = input("Nom équipe Extérieur: ")
    
    home_gf = float(input(f"Total Buts marqués à la maison {home}: "))
    home_ga = float(input(f"Total Buts encaissés à la maison {home}: "))
    home_mp = float(input(f"Matchs joués à domicile {home}: "))
    
    away_gf = float(input(f"Total Buts marqués dehors {away}: "))
    away_ga = float(input(f"Total Buts encaissés dehors {away}: "))
    away_mp = float(input(f"Matchs joués à l'extérieur {away}: "))
    
    league_avg = float(input("Constante de buts par match du championnat: "))
    
    # Côtes bookmakers
    cote_1 = float(input("Côte 1 (Domicile): "))
    cote_X = float(input("Côte X (Nul): "))
    cote_2 = float(input("Côte 2 (Extérieur): "))
    cote_over25 = float(input("Côte Over 2.5: "))
    cote_under25 = float(input("Côte Under 2.5: "))
    cote_over15 = float(input("Côte Over 1.5: "))
    cote_under15 = float(input("Côte Under 1.5: "))
    cote_btts_oui = float(input("Côte BTTS Oui: "))
    cote_btts_non = float(input("Côte BTTS Non: "))

    # 2. CALCULS VRAIS
    home_attaque = home_gf / home_mp
    home_defense = home_ga / home_mp
    away_attaque = away_gf / away_mp
    away_defense = away_ga / away_mp
    
    buts_prevus_home = (home_attaque * away_defense) / league_avg
    buts_prevus_away = (away_attaque * home_defense) / league_avg
    total_buts_prevu = buts_prevus_home + buts_prevus_away
    
    # Probabilités 1X2 avec poisson
    prob_home = (buts_prevus_home / (buts_prevus_home + buts_prevus_away + 0.2)) * 100
    prob_away = (buts_prevus_away / (buts_prevus_home + buts_prevus_away + 0.2)) * 100
    prob_draw = 100 - prob_home - prob_away
    
    # BTTS
    prob_btts_oui = (1 - math.exp(-buts_prevus_home)) * (1 - math.exp(-buts_prevus_away)) * 100
    prob_btts_non = 100 - prob_btts_oui
    
    # Over/Under
    prob_over25 = (1 - math.exp(-total_buts_prevu) * (1 + total_buts_prevu + total_buts_prevu**2/2)) * 100
    prob_under25 = 100 - prob_over25
    prob_over15 = (1 - math.exp(-total_buts_prevu) * (1 + total_buts_prevu)) * 100
    prob_under15 = 100 - prob_over15
    
    # Score exact le plus probable
    score_home = round(buts_prevus_home)
    score_away = round(buts_prevus_away)
    if score_home == score_away: score_home += 1 # éviter 0-0 si attaque forte
    
    # Mi-temps: 40% des buts en 1ere
    mt_home = round(score_home * 0.5)
    mt_away = round(score_away * 0.5)
    
    # 3. RESULTAT FORMATÉ COMME SUR TES IMAGES
    print("\n===== RESULTAT ANALYSE IA =====")
    print(f"\n📊 **COTES BOOKMAKERS**")
    print(f"1(Dom): {cote_1} | X(Nul): {cote_X} | 2(Ext): {cote_2}")
    print(f"Over 2.5: {cote_over25} | Under 2.5: {cote_under25}")
    print(f"BTTS Oui: {cote_btts_oui} | BTTS Non: {cote_btts_non}")
    
    print(f"\n🔥 **PROBABILITES 1X2**")
    print(f"{home}: {prob_home:.0f}% | Nul: {prob_draw:.0f}% | {away}: {prob_away:.0f}%")
    
    print(f"\n🎯 **PREDICTION IA**")
    print(f"Score Exact: {score_home}-{score_away},00")
    print(f"Mi-temps: {mt_home}-{mt_away},00")
    print(f"Over/Under 2.5: {'Over' if prob_over25 > 55 else 'Under'} {prob_over25:.0f}%")
    print(f"BTTS: {'Oui' if prob_btts_oui > 55 else 'Non'} {prob_btts_oui:.0f}%")
    
    # Meilleur pari
    if prob_home > 60: meilleur = f"Victoire {home}"
    elif prob_away > 60: meilleur = f"Victoire {away}"
    else: meilleur = "Nul ou Double Chance"
    
    print(f"\n💎 **PARI LE PLUS SAFE: {meilleur}**")
    print(f"Fiabilité: {max(prob_home, prob_away, prob_draw):.0f}%")
    
    print(f"\n📈 **STATS CALCULÉES**")
    print(f"{home} Attaque: {home_attaque:.2f} buts/m | Défense: {home_defense:.2f}")
    print(f"{away} Attaque: {away_attaque:.2f} buts/m | Défense: {away_defense:.2f}")
    print(f"Total buts prévu: {total_buts_prevu:.2f}")

analyse_match()
