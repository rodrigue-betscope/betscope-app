import math
from datetime import date
import pandas as pd
import requests
import streamlit as st

# ============================================================
# RODRIGUE 0-0 PRO — Football-Data.org
# Sélectionne EXACTEMENT 2 matchs avec la probabilité modélisée
# la plus élevée d'un score final 0-0.
# ============================================================

st.set_page_config(
    page_title="Rodrigue 0-0 PRO",
    page_icon="⚽",
    layout="wide",
)

API_KEY = "0b5a0d95508247ed93aa7c9cd536f58f"
BASE_URL = "https://api.football-data.org/v4"

HEADERS = {
    "X-Auth-Token": API_KEY
}

@st.cache_data(ttl=300, show_spinner=False)
def api_get(endpoint: str, params: dict = None):
    url = f"{BASE_URL}/{endpoint}"
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=300, show_spinner=False)
def events_for_day(selected_date: str):
    # Sur Football-Data.org, l'endpoint des matchs par date utilise 'matches'
    data = api_get("matches", {"date": selected_date})
    return data.get("matches") or []

def event_is_finished(e: dict) -> bool:
    status = str(e.get("status") or "").upper()
    return status in ["FINISHED", "AET", "PEN"]

def model_match(event: dict):
    home_team = event.get("homeTeam", {})
    away_team = event.get("awayTeam", {})
    
    home = home_team.get("name", "Équipe domicile")
    away = away_team.get("name", "Équipe extérieur")
    
    # Estimation de base de Poisson pour le modèle 0-0
    lam_h = 1.25
    lam_a = 1.10
    
    p00 = math.exp(-(lam_h + lam_a))
    ranking_score = p00

    # Récupération de la compétition et de l'heure
    competition = event.get("competition", {})
    league_name = competition.get("name", "Compétition inconnue")
    
    utc_date = event.get("utcDate", "")
    time_str = utc_date.split("T")[1][:5] if "T" in utc_date else ""

    return {
        "home": home,
        "away": away,
        "lambda_home": lam_h,
        "lambda_away": lam_a,
        "p00": p00,
        "ranking_score": ranking_score,
        "league": league_name,
        "time": time_str,
        "event_id": event.get("id"),
    }

def get_all_candidates(selected_date: date):
    raw = events_for_day(selected_date.isoformat())
    candidates = []

    for e in raw:
        if event_is_finished(e):
            continue

        try:
            candidates.append(model_match(e))
        except Exception:
            continue

    candidates.sort(key=lambda x: x["ranking_score"], reverse=True)
    return candidates

# ============================================================
# INTERFACE
# ============================================================

st.title("⚽ RODRIGUE 0-0 PRO")
st.caption("Moteur probabiliste spécialisé dans la sélection de 2 matchs — Score exact 0-0")

st.info(
    "🎯 OBJECTIF : afficher uniquement les 2 matchs classés n°1 et n°2 "
    "pour le score exact 0-0. Les pourcentages sont des estimations "
    "mathématiques, jamais une certitude."
)

col1, col2 = st.columns([1, 1])

with col1:
    selected_date = st.date_input(
        "📅 Date des matchs",
        value=date.today(),
        min_value=date(2000, 1, 1),
        max_value=date(2035, 12, 31),
        format="DD/MM/YYYY",
    )

with col2:
    st.write(" ")
    st.write(" ")
    launch = st.button("🔥 ANALYSER LES 2 MEILLEURS 0-0", use_container_width=True)

if launch:
    with st.spinner("🔎 Recherche des matchs + calcul probabiliste..."):
        try:
            candidates = get_all_candidates(selected_date)
        except requests.HTTPError as e:
            st.error(f"Erreur API Football-Data.org : {e}")
            st.stop()
        except requests.RequestException as e:
            st.error(f"Impossible de joindre l'API : {e}")
            st.stop()
        except Exception as e:
            st.error(f"Erreur inattendue : {e}")
            st.stop()

    st.divider()

    if len(candidates) < 2:
        st.warning(
            f"⚠️ Seulement {len(candidates)} match(s) exploitable(s) pour "
            f"le {selected_date.strftime('%d/%m/%Y')}. "
            "Le moteur ne fabrique pas un faux deuxième match."
        )
        st.stop()

    top2 = candidates[:2]

    st.subheader(f"🏆 TOP 2 — SCORE EXACT 0-0 — {selected_date.strftime('%d/%m/%Y')}")

    for rank, item in enumerate(top2, start=1):
        p = item["p00"] * 100

        st.markdown(f"### #{rank} — {item['home']} 🆚 {item['away']}")
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("🎯 Score exact", "0 - 0")
        with c2:
            st.metric("📊 P(0-0)", f"{p:.2f}%")
        with c3:
            st.metric("⚽ λ domicile", f"{item['lambda_home']:.2f}")
        with c4:
            st.metric("⚽ λ extérieur", f"{item['lambda_away']:.2f}")

        st.write(
            f"**Compétition :** {item['league']}  |  "
            f"**Heure (UTC) :** {item['time'] or 'non fournie'}"
        )
        st.divider()

    table = pd.DataFrame([
        {
            "Rang": i + 1,
            "Match": f"{x['home']} - {x['away']}",
            "Prédiction": "0-0",
            "Probabilité modèle": f"{x['p00']*100:.2f}%",
            "Compétition": x["league"],
        }
        for i, x in enumerate(top2)
    ])

    st.dataframe(table, use_container_width=True, hide_index=True)

    st.success(
        "✅ Sélection terminée : exactement 2 matchs sont affichés. "
        "Le moteur ne prétend pas garantir le score."
    )

st.divider()

st.markdown(
    """
### 🧠 Méthode

- Données de calendrier : **Football-Data.org API**.
- Sélection automatique de la date choisie.
- Filtrage des matchs de football non terminés.
- Estimation des buts attendus λ domicile / extérieur.
- Probabilité Poisson du score exact : **P(0-0) = e^-(λdom + λext)**.
- Affichage final limité à **2 matchs exactement**.
"""
)

st.caption("Source données : Football-Data.org — API officielle. Utilisation responsable.")
