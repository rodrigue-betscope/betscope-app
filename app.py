import math
import time
from datetime import date, datetime, timedelta

import pandas as pd
import requests
import streamlit as st

# ============================================================
# RODRIGUE 0-0 PRO — TheSportsDB
# Sélectionne EXACTEMENT 2 matchs avec la probabilité modélisée
# la plus élevée d'un score final 0-0.
#
# IMPORTANT :
# - Aucun modèle ne peut garantir un score exact.
# - TheSportsDB fournit les données, le modèle calcule un classement.
# - La version gratuite de TheSportsDB a des limites de requêtes.
# ============================================================

st.set_page_config(
    page_title="Rodrigue 0-0 PRO",
    page_icon="⚽",
    layout="wide",
)

API_KEY = "0b5a0d95508247ed93aa7c9cd536f58f"
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"

# Cache court pour éviter de dépasser inutilement les limites API.
@st.cache_data(ttl=300, show_spinner=False)
def api_get(endpoint: str, params: dict):
    url = f"{BASE_URL}/{endpoint}"
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=300, show_spinner=False)
def events_for_day(selected_date: str):
    data = api_get(
        "eventsday.php",
        {"d": selected_date, "s": "Soccer"},
    )
    return data.get("events") or []

@st.cache_data(ttl=300, show_spinner=False)
def last_team_event(team_id: str):
    if not team_id:
        return None
    try:
        data = api_get("eventslast.php", {"id": team_id})
        events = data.get("results") or data.get("events") or []
        return events[0] if events else None
    except Exception:
        return None

def as_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def event_is_finished(e: dict) -> bool:
    status = str(e.get("strStatus") or "").lower()
    if any(x in status for x in ["finished", "ft", "after", "aet", "pen"]):
        return True

    # Les champs de score sont généralement remplis après le match.
    hs = e.get("intHomeScore")
    as_ = e.get("intAwayScore")
    if hs not in (None, "") and as_ not in (None, ""):
        return True

    return False

def recent_goal_estimate(team_event: dict, team_id: str):
    """
    Avec la clé gratuite, TheSportsDB peut limiter les historiques.
    On utilise donc la dernière rencontre disponible comme information
    complémentaire, fortement régularisée vers une moyenne neutre.
    """
    if not team_event:
        return None

    home_id = str(team_event.get("idHomeTeam") or "")
    away_id = str(team_event.get("idAwayTeam") or "")
    hs = as_float(team_event.get("intHomeScore"))
    aws = as_float(team_event.get("intAwayScore"))

    if hs is None or aws is None:
        return None

    if str(team_id) == home_id:
        return hs, aws
    if str(team_id) == away_id:
        return aws, hs

    return None

def poisson_pmf_zero(lam: float) -> float:
    return math.exp(-max(0.01, lam))

def shrink(value, baseline, weight=0.35):
    return baseline * (1 - weight) + value * weight

def model_match(event: dict):
    """
    Modèle 0-0 :
    1) construit une estimation des buts attendus pour chaque équipe;
    2) régularise fortement quand les données historiques sont limitées;
    3) calcule P(0-0)=exp(-lambda_home-lambda_away);
    4) applique de petits ajustements seulement quand les informations
       disponibles sont cohérentes.

    Ce n'est PAS une garantie de résultat.
    """
    home = str(event.get("strHomeTeam") or "Équipe domicile")
    away = str(event.get("strAwayTeam") or "Équipe extérieur")
    hid = str(event.get("idHomeTeam") or "")
    aid = str(event.get("idAwayTeam") or "")

    h_last = last_team_event(hid)
    a_last = last_team_event(aid)

    h_data = recent_goal_estimate(h_last, hid)
    a_data = recent_goal_estimate(a_last, aid)

    # Prior conservateur de buts par équipe.
    # Le prior empêche un seul match historique de sur-ajuster le modèle.
    HOME_BASE = 1.25
    AWAY_BASE = 1.10

    h_scored = h_conceded = None
    a_scored = a_conceded = None

    if h_data:
        h_scored, h_conceded = h_data
    if a_data:
        a_scored, a_conceded = a_data

    # Si données disponibles : moyenne très régularisée.
    # Attaque équipe + défense adverse.
    if h_scored is not None and a_conceded is not None:
        lam_h = 0.50 * shrink(h_scored, HOME_BASE) + 0.50 * shrink(a_conceded, HOME_BASE)
    else:
        lam_h = HOME_BASE

    if a_scored is not None and h_conceded is not None:
        lam_a = 0.50 * shrink(a_scored, AWAY_BASE) + 0.50 * shrink(h_conceded, AWAY_BASE)
    else:
        lam_a = AWAY_BASE

    # Si les deux dernières données montrent une faible production offensive,
    # on baisse légèrement lambda. Si elles montrent une attaque forte, on
    # augmente légèrement. Bornes pour éviter les valeurs absurdes.
    if h_scored is not None and a_scored is not None:
        avg_scored = (h_scored + a_scored) / 2.0
        if avg_scored <= 0.5:
            lam_h *= 0.86
            lam_a *= 0.86
        elif avg_scored >= 2.5:
            lam_h *= 1.10
            lam_a *= 1.10

    lam_h = min(max(lam_h, 0.20), 2.80)
    lam_a = min(max(lam_a, 0.20), 2.60)

    p00 = poisson_pmf_zero(lam_h + lam_a)

    # Petit bonus de stabilité si les deux derniers matchs disponibles
    # étaient sans but pour l'équipe concernée.
    zero_signal = 0.0
    if h_data and h_data[0] == 0:
        zero_signal += 0.025
    if a_data and a_data[0] == 0:
        zero_signal += 0.025

    p00 = min(p00 + zero_signal, 0.90)

    # Score de sélection : probabilité 0-0 principalement.
    # On favorise aussi les matchs avec données historiques disponibles.
    data_bonus = 0.0
    if h_data:
        data_bonus += 0.01
    if a_data:
        data_bonus += 0.01

    ranking_score = p00 + data_bonus

    return {
        "home": home,
        "away": away,
        "lambda_home": lam_h,
        "lambda_away": lam_a,
        "p00": p00,
        "ranking_score": ranking_score,
        "home_data": bool(h_data),
        "away_data": bool(a_data),
        "league": event.get("strLeague") or "Compétition inconnue",
        "time": event.get("strTime") or event.get("strTimeLocal") or "",
        "event_id": event.get("idEvent"),
    }

def get_all_candidates(selected_date: date):
    raw = events_for_day(selected_date.isoformat())
    candidates = []

    for e in raw:
        if str(e.get("strSport") or "").lower() != "soccer":
            continue
        if event_is_finished(e):
            continue

        # Évite les événements sans deux équipes.
        if not e.get("strHomeTeam") or not e.get("strAwayTeam"):
            continue

        try:
            candidates.append(model_match(e))
        except Exception:
            # Un événement défectueux ne doit pas bloquer toute l'analyse.
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
            st.error(f"Erreur API TheSportsDB : {e}")
            st.stop()
        except requests.RequestException as e:
            st.error(f"Impossible de joindre TheSportsDB : {e}")
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
            f"**Heure :** {item['time'] or 'non fournie'}"
        )

        data_quality = (
            "données récentes disponibles pour les deux équipes"
            if item["home_data"] and item["away_data"]
            else "historique partiel — estimation davantage régularisée"
        )
        st.caption(f"ℹ️ {data_quality}. ID événement : {item['event_id']}")

        st.divider()

    # Tableau interne de contrôle : uniquement les 2 sélectionnés.
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

- Données de calendrier : **TheSportsDB Free API**.
- Sélection automatique de la date choisie.
- Filtrage des matchs de football non terminés.
- Estimation des buts attendus λ domicile / extérieur.
- Probabilité Poisson du score exact : **P(0-0) = e^-(λdom + λext)**.
- Classement de tous les matchs disponibles.
- Affichage final limité à **2 matchs exactement**.

⚠️ **Important :** un score exact 0-0 est un événement difficile à prédire. 
Un pourcentage élevé ne signifie pas que le 0-0 est certain.
"""
)

st.caption("Source données : TheSportsDB — API officielle. Utilisation responsable.")
