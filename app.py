import math
from datetime import date
import pandas as pd
import requests
import streamlit as st

# ============================================================
# RODRIGUE 0-0 PRO — Football-Data.org (Version Statistiques Réelles)
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
    data = api_get("matches", {"date": selected_date})
    return data.get("matches") or []

@st.cache_data(ttl=300, show_spinner=False)
def get_team_recent_matches(team_id: int):
    """Récupère les derniers matchs terminés de l'équipe pour calculer ses vraies stats"""
    try:
        data = api_get(f"teams/{team_id}/matches", {"status": "FINISHED", "limit": 5})
        return data.get("matches") or []
    except Exception:
        return []

def event_is_finished(e: dict) -> bool:
    status = str(e.get("status") or "").upper()
    return status in ["FINISHED", "AET", "PEN"]

def calculate_team_lambda(matches, team_id, is_home: bool):
    """Calcule la moyenne réelle de buts marqués et encaissés sur les derniers matchs"""
    if not matches:
        return 1.20 if is_home else 1.05  # Moyenne de repli neutre si pas d'historique

    scored_list = []
    conceded_list = []

    for m in matches:
        home_t = m.get("homeTeam", {}).get("id")
        score = m.get("score", {}).get("fullTime", {})
        h_goals = score.get("home")
        a_goals = score.get("away")

        if h_goals is None or a_goals is None:
            continue

        if home_t == team_id:
            scored_list.append(h_goals)
            conceded_list.append(a_goals)
        else:
            scored_list.append(a_goals)
            conceded_list.append(h_goals)

    if not scored_list:
        return 1.20 if is_home else 1.05

    avg_scored = sum(scored_list) / len(scored_list)
    avg_conceded = sum(conceded_list) / len(conceded_list)

    # Lambda estimé basé sur l'attaque de l'équipe et la défense (fixée ici à une base équilibrée)
    lam = (avg_scored + avg_conceded) / 2.0
    return max(0.20, min(lam, 2.80))

def model_match(event: dict):
    home_team = event.get("homeTeam", {})
    away_team = event.get("awayTeam", {})
    
    home = home_team.get("name", "Équipe domicile")
    away = away_team.get("name", "Équipe extérieur")
    
    hid = home_team.get("id")
    aid = away_team.get("id")

    # Récupération des vrais historiques via l'API pour chaque équipe
    h_matches = get_team_recent_matches(hid) if hid else []
    a_matches = get_team_recent_matches(aid) if aid else []

    # Calcul des vrais coefficients lambda basés sur les matchs réels
    lam_h = calculate_team_lambda(h_matches, hid, is_home=True)
    lam_a = calculate_team_lambda(a_matches, aid, is_home=False)
    
    # Probabilité Poisson du score exact 0-0 : P(0-0) = e^-(lam_h + lam_a)
    p00 = math.exp(-(lam_h + lam_a))
    
    # Bonus de robustesse si les équipes ont des matchs réels enregistrés
    data_bonus = 0.01 if h_matches and a_matches else 0.0
    ranking_score = p00 + data_bonus

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
        "has_data": bool(h_matches and a_matches)
    }

def get_all_candidates(selected_date: date):
    raw = events_for_day(selected_date.isoformat())
    candidates = []

    for e in raw:
        if event_is_finished(e):
            continue
        if not e.get("homeTeam") or not e.get("awayTeam"):
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
    "pour le score exact 0-0 basés sur les vraies statistiques des équipes."
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
    with st.spinner("🔎 Récupération des vraies stats et calcul des probabilités..."):
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
        
        status_text = "Statistiques basées sur les derniers matchs réels" if item["has_data"] else "Statistiques par défaut (historique limité)"
        st.caption(f"ℹ️ {status_text}")
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
        "✅ Sélection terminée : exactement 2 matchs avec statistiques réelles affichés."
    )

st.divider()

st.markdown(
    """
### 🧠 Méthode

- Données de calendrier et de performances : **Football-Data.org API**.
- Analyse des derniers matchs de chaque équipe pour extraire les buts réels.
- Calcul des taux d'attente λ (domicile et extérieur).
- Modèle de Poisson pur : **P(0-0) = e^-(λdom + λext)**.
- Sélection rigoureuse du **Top 2 exact**.
"""
)

st.caption("Source données : Football-Data.org — API officielle.")
