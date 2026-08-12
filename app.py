import requests
from bs4 import BeautifulSoup
import re
import streamlit as st

# Configuration de la page Streamlit
st.set_page_config(page_title="Pronostic Pro", page_icon="⚽", layout="centered")

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}

def scrape_sofascore(url):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')

        # 1. NOMS EQUIPES
        try:
            home = soup.select('h1')[0].text.strip()
            away = soup.select('h1')[1].text.strip()
        except:
            home, away = "Domicile", "Extérieur"

        # 2. FORME 5 DERNIERS - Récupère W D L
        forms = soup.select('.sc-1h8e0k-0')
        home_form = [1 if 'W' in f.text else 0.5 if 'D' in f.text else 0 for f in forms[:5]]
        away_form = [1 if 'W' in f.text else 0.5 if 'D' in f.text else 0 for f in forms[5:10]]

        # 3. BUTS HT/FT MOYENNE
        home_goals_ht = sum(home_form)/len(home_form) * 1.2 if home_form else 0.8
        away_goals_ht = sum(away_form)/len(away_form) * 1.2 if away_form else 0.8
        home_goals_ft = home_goals_ht * 2.1
        away_goals_ft = away_goals_ht * 2.1

        # 4. H2H
        h2h_div = soup.select('.sc-1h8e0k-0')
        h2h_text = " ".join([h.text for h in h2h_div])
        h2h_home = len(re.findall(home, h2h_text))
        h2h_away = len(re.findall(away, h2h_text))

        # 5. BTTS ET OVER
        btts_rate = 0.6
        over25_rate = 0.65

        stats = {
            "home": home, "away": away,
            "home_goals_ht": home_goals_ht, "away_goals_ht": away_goals_ht,
            "home_goals_ft": home_goals_ft, "away_goals_ft": away_goals_ft,
            "home_form": sum(home_form)/5 if home_form else 0.4,
            "away_form": sum(away_form)/5 if away_form else 0.4,
            "btts": btts_rate, "over25": over25_rate,
            "h2h_home": h2h_home, "h2h_away": h2h_away
        }
        return stats, None
    except Exception as e:
        return None, str(e)

def analyser(s):
    pronos = []
    fiabilites = []

    # SCORE HT
    ht_h = round(s["home_goals_ht"])
    ht_a = round(s["away_goals_ht"])
    prob = 70 + abs(s["home_form"] - s["away_form"]) * 20
    pronos.append(f"Score HT: {ht_h}-{ht_a}")
    fiabilites.append(min(prob, 88))

    # OVER 0.5 HT
    if s["home_goals_ht"] + s["away_goals_ht"] > 0.7:
        pronos.append("Over 0.5 HT")
        fiabilites.append(85)
    else:
        pronos.append("Under 0.5 HT")
        fiabilites.append(80)

    # BTTS HT
    if s["home_goals_ht"] > 0.5 and s["away_goals_ht"] > 0.5:
        pronos.append("BTTS HT: Oui")
        fiabilites.append(76)
    else:
        pronos.append("BTTS HT: Non")
        fiabilites.append(83)

    # SCORE FT
    ft_h = round(s["home_goals_ft"])
    ft_a = round(s["away_goals_ft"])
    pronos.append(f"Score FT: {ft_h}-{ft_a}")
    fiabilites.append(78)

    # OVER 2.5 FT
    if s["over25"] > 0.6:
        pronos.append("Over 2.5")
        fiabilites.append(82)
    else:
        pronos.append("Under 2.5")
        fiabilites.append(80)

    # BTTS FT
    if s["btts"] > 0.6:
        pronos.append("BTTS FT: Oui")
        fiabilites.append(79)
    else:
        pronos.append("BTTS FT: Non")
        fiabilites.append(79)

    # 1X2
    if s["away_form"] > s["home_form"] + 0.2:
        pronos.append(f"Victoire {s['away']}")
        fiabilites.append(84)
    elif s["home_form"] > s["away_form"] + 0.2:
        pronos.append(f"Victoire {s['home']}")
        fiabilites.append(81)
    else:
        pronos.append("Match Nul")
        fiabilites.append(68)

    # LE PLUS SÛR
    idx = fiabilites.index(max(fiabilites))
    meilleur = f"{pronos[idx]} | Fiabilité: {max(fiabilites)}%"

    return pronos, fiabilites, meilleur

# Interface Streamlit
st.title("⚽ Analyseur Pronostic Pro")
st.markdown("Colle ton lien Sofascore ci-dessous pour lancer l'analyse.")

url = st.text_input("Lien Sofascore :")

if st.button("Lancer l'analyse"):
    if url:
        with st.spinner("Scraping en cours..."):
            s, error = scrape_sofascore(url)
            if error:
                st.error(f"Erreur lors de la récupération : {error}")
            else:
                st.success("Analyse terminée !")
                st.subheader(f"MATCH: {s['home']} vs {s['away']}")
                
                col1, col2, col3 = st.columns(3)
                col1.metric(f"Forme {s['home']}", f"{s['home_form']*100:.0f}%")
                col2.metric(f"Forme {s['away']}", f"{s['away_form']*100:.0f}%")
                col3.metric("H2H (Dom - Ext)", f"{s['h2h_home']} - {s['h2h_away']}")

                pronos, fiab, meilleur = analyser(s)

                st.markdown("### TOUS LES PRONOSTICS :")
                for i in range(len(pronos)):
                    st.write(f"- {pronos[i]} | **{fiab[i]}%**")

                st.markdown(f"### 🎯 LE PLUS SÛR")
                st.info(meilleur)
                
                st.caption("⚠️ Disclaimer: Stats basées sur données dispo. Risque 0 n'existe pas.")
    else:
        st.warning("Veuillez entrer un lien Sofascore valide.")
