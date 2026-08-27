import math
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# RODRIGUE MT/FT PRO
# FOOTBALL-DATA.ORG v4
# ============================================================

st.set_page_config(
    page_title="Rodrigue MT/FT PRO",
    page_icon="⚽",
    layout="wide",
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://api.football-data.org/v4"
TZ = ZoneInfo("Africa/Douala")

DEFAULT_API_KEY = "0b5a0d95508247ed93aa7c9cd536f58f"

try:
    API_KEY = st.secrets.get(
        "FOOTBALL_DATA_API_KEY",
        DEFAULT_API_KEY,
    )
except Exception:
    API_KEY = DEFAULT_API_KEY


COMPETITIONS = {
    "PL": "Premier League",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "PD": "La Liga",
    "FL1": "Ligue 1",
    "DED": "Eredivisie",
    "PPL": "Primeira Liga",
    "CL": "Champions League",
}


session = requests.Session()
session.headers.update(
    {
        "X-Auth-Token": API_KEY,
        "Accept": "application/json",
        "User-Agent": "Rodrigue-MTFT-Pro/1.0",
    }
)


# ============================================================
# REQUÊTE API
# ============================================================

def api_get(endpoint, params=None, retry=True):
    url = f"{BASE_URL}{endpoint}"
    try:
        response = session.get(
            url,
            params=params or {},
            timeout=30,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Erreur réseau : {e}")

    if response.status_code == 401:
        raise RuntimeError("❌ Clé Football-Data.org invalide.")
    if response.status_code == 403:
        raise RuntimeError("❌ Accès refusé à cette compétition.")
    if response.status_code == 429:
        if retry:
            time.sleep(12)
            return api_get(endpoint, params, retry=False)
        raise RuntimeError("❌ Limite de requêtes atteinte.")

    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, show_spinner=False)
def get_matches_for_date(selected_date, competitions_list):
    if not competitions_list:
        return []
    comps_str = ",".join(competitions_list)
    data = api_get(
        "/matches",
        {
            "dateFrom": selected_date,
            "dateTo": selected_date,
            "competitions": comps_str,
        },
    )
    return data.get("matches", [])


@st.cache_data(ttl=1800, show_spinner=False)
def get_team_history(team_id, before_date, limit=20):
    end_date = datetime.strptime(before_date, "%Y-%m-%d").date() - timedelta(days=1)
    start_date = end_date - timedelta(days=180)
    data = api_get(
        f"/teams/{team_id}/matches",
        {
            "dateFrom": start_date.isoformat(),
            "dateTo": end_date.isoformat(),
            "status": "FINISHED",
            "limit": limit,
        },
    )
    matches = data.get("matches", [])
    matches.sort(key=lambda x: x.get("utcDate", ""), reverse=True)
    return matches[:limit]


def get_score(match, period="fullTime"):
    score = match.get("score", {})
    period_score = score.get(period, {})
    home = period_score.get("home")
    away = period_score.get("away")
    if home is None or away is None:
        return None, None
    try:
        return int(home), int(away)
    except Exception:
        return None, None


def calculate_team_stats(matches, team_id):
    full_for, full_against = [], []
    ht_for, ht_against = [], []
    home_for, home_against = [], []
    away_for, away_against = [], []
    valid = 0

    for index, match in enumerate(matches):
        home_team = match.get("homeTeam", {})
        away_team = match.get("awayTeam", {})
        home_id = home_team.get("id")
        away_id = away_team.get("id")

        if home_id != team_id and away_id != team_id:
            continue

        fh, fa = get_score(match, "fullTime")
        hh, ha = get_score(match, "halfTime")

        if fh is None or fa is None or hh is None or ha is None:
            continue

        valid += 1
        weight = max(0.35, 1.0 - index * 0.035)

        if home_id == team_id:
            full_for.append((fh, weight))
            full_against.append((fa, weight))
            ht_for.append((hh, weight))
            ht_against.append((ha, weight))
            home_for.append((fh, weight))
            home_against.append((fa, weight))
        else:
            full_for.append((fa, weight))
            full_against.append((fh, weight))
            ht_for.append((ha, weight))
            ht_against.append((hh, weight))
            away_for.append((fa, weight))
            away_against.append((fh, weight))

    def weighted_avg(values):
        if not values:
            return None
        numerator = sum(v * w for v, w in values)
        denominator = sum(w for _, w in values)
        if denominator <= 0:
            return None
        return numerator / denominator

    return {
        "matches": valid,
        "full_for": weighted_avg(full_for),
        "full_against": weighted_avg(full_against),
        "ht_for": weighted_avg(ht_for),
        "ht_against": weighted_avg(ht_against),
        "home_for": weighted_avg(home_for),
        "home_against": weighted_avg(home_against),
        "away_for": weighted_avg(away_for),
        "away_against": weighted_avg(away_against),
    }


def expected_goals(home_stats, away_stats):
    values_home = []
    if home_stats["home_for"] is not None:
        values_home.append(home_stats["home_for"])
    if away_stats["away_against"] is not None:
        values_home.append(away_stats["away_against"])

    values_away = []
    if away_stats["away_for"] is not None:
        values_away.append(away_stats["away_for"])
    if home_stats["home_against"] is not None:
        values_away.append(home_stats["home_against"])

    if not values_home or not values_away:
        return None, None

    lambda_home = np.mean(values_home) * 1.05
    lambda_away = np.mean(values_away) * 0.97

    return float(np.clip(lambda_home, 0.10, 4.50)), float(np.clip(lambda_away, 0.10, 4.00))


def poisson(goals, expected):
    return math.exp(-expected) * (expected ** goals) / math.factorial(goals)


def dixon_coles(home, away, lh, la, rho=-0.08):
    if home == 0 and away == 0:
        return 1 - lh * la * rho
    if home == 0 and away == 1:
        return 1 + lh * rho
    if home == 1 and away == 0:
        return 1 + la * rho
    if home == 1 and away == 1:
        return 1 - rho
    return 1.0


def mtft_probability(home_stats, away_stats, lh, la):
    ht_factor = 0.46
    lh_ht = lh * ht_factor
    la_ht = la * ht_factor
    lh_2h = lh - lh_ht
    la_2h = la - la_ht

    markets = {
        "1/1": 0.0, "X/1": 0.0, "2/1": 0.0,
        "1/X": 0.0, "X/X": 0.0, "2/X": 0.0,
        "1/2": 0.0, "X/2": 0.0, "2/2": 0.0,
    }

    max_goals = 7
    for h_ht in range(max_goals + 1):
        p_h_ht = poisson(h_ht, lh_ht)
        for a_ht in range(max_goals + 1):
            p_a_ht = poisson(a_ht, la_ht)
            p_ht = p_h_ht * p_a_ht

            if h_ht > a_ht:
                ht = "1"
            elif h_ht < a_ht:
                ht = "2"
            else:
                ht = "X"

            for h2 in range(max_goals + 1):
                p_h2 = poisson(h2, lh_2h)
                for a2 in range(max_goals + 1):
                    p_a2 = poisson(a2, la_2h)
                    probability = p_ht * p_h2 * p_a2

                    hf = h_ht + h2
                    af = a_ht + a2
                    if hf > af:
                        ft = "1"
                    elif hf < af:
                        ft = "2"
                    else:
                        ft = "X"

                    probability *= dixon_coles(hf, af, lh, la)
                    markets[f"{ht}/{ft}"] += probability

    total = sum(markets.values())
    if total > 0:
        markets = {k: v / total for k, v in markets.items()}
    return markets


def quality_score(home_stats, away_stats):
    home_matches = home_stats["matches"]
    away_matches = away_stats["matches"]
    match_quality = min(100, (min(home_matches, 10) + min(away_matches, 10)) * 5)
    
    fields = ["full_for", "full_against", "ht_for", "ht_against"]
    data_count = sum(1 for f in fields if home_stats.get(f) is not None) + sum(1 for f in fields if away_stats.get(f) is not None)
    field_quality = (data_count / 8) * 100
    return 0.65 * match_quality + 0.35 * field_quality


def analyze_match(match, selected_date):
    home_team = match.get("homeTeam", {})
    away_team = match.get("awayTeam", {})
    home_id = home_team.get("id")
    away_id = away_team.get("id")

    if not home_id or not away_id:
        return None

    history_home = get_team_history(home_id, selected_date, 20)
    history_away = get_team_history(away_id, selected_date, 20)

    home_stats = calculate_team_stats(history_home, home_id)
    away_stats = calculate_team_stats(history_away, away_id)

    if home_stats["matches"] < 3 or away_stats["matches"] < 3:
        return None

    lh, la = expected_goals(home_stats, away_stats)
    if lh is None or la is None:
        return None

    probabilities = mtft_probability(home_stats, away_stats, lh, la)
    ranked = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
    quality = quality_score(home_stats, away_stats)
    selection_score = (ranked[0][1] * 100 * 0.75) + (quality * 0.25)

    return {
        "id": match.get("id"),
        "home": home_team.get("name", "Domicile"),
        "away": away_team.get("name", "Extérieur"),
        "competition": match.get("competition", {}).get("name", "Compétition"),
        "utcDate": match.get("utcDate", ""),
        "lh": lh,
        "la": la,
        "quality": quality,
        "selection_score": selection_score,
        "probabilities": ranked,
        "home_matches": home_stats["matches"],
        "away_matches": away_stats["matches"],
    }


# ============================================================
# INTERFACE STREAMLIT
# ============================================================

st.title("⚽ RODRIGUE MT/FT PRO")
st.subheader("🔥 Football-Data.org • Poisson • MT/FT")

with st.sidebar:
    st.header("⚙️ Configuration")
    today = datetime.now(TZ).date()
    selected_date = st.date_input("📅 Date des matchs", value=today)
    selected_competitions = st.multiselect(
        "🏆 Compétitions",
        options=list(COMPETITIONS.keys()),
        default=["PL", "BL1", "SA", "PD", "FL1", "DED", "PPL"],
        format_func=lambda x: COMPETITIONS[x],
    )
    max_matches = st.slider("⚽ Nombre de matchs max", min_value=3, max_value=20, value=6)

if st.button("🚀 ANALYSER LES VRAIS MATCHS", type="primary", use_container_width=True):
    try:
        date_string = selected_date.isoformat()
        
        with st.spinner("🔎 Récupération des matchs..."):
            matches = get_matches_for_date(date_string, selected_competitions)

        valid_statuses = ["TIMED", "SCHEDULED", "LIVE", "IN_PLAY", "PAUSED"]
        filtered_matches = [m for m in matches if m.get("status") in valid_statuses]

        if not filtered_matches and matches:
            filtered_matches = [m for m in matches if m.get("status") not in ["CANCELLED", "POSTPONED"]]

        if not filtered_matches:
            st.error(f"❌ Aucun match disponible pour la date du {selected_date} dans les compétitions sélectionnées.")
            st.info("💡 **Astuce :** Vérifie si les championnats choisis ont des matchs programmés aujourd'hui, ou essaie de sélectionner d'autres ligues dans la barre latérale.")
            st.stop()

        matches = filtered_matches[:max_matches]
        results = []
        progress = st.progress(0)
        status_text = st.empty()

        for index, match in enumerate(matches):
            home = match.get("homeTeam", {}).get("name", "?")
            away = match.get("awayTeam", {}).get("name", "?")
            status_text.write(f"🔎 Analyse : {home} — {away}")

            try:
                result = analyze_match(match, date_string)
                if result:
                    results.append(result)
            except Exception:
                pass

            progress.progress((index + 1) / len(matches))

        status_text.empty()

        if not results:
            st.error("❌ Impossible de calculer les probabilités (historique insuffisant pour ces équipes sur l'API).")
            st.stop()

        results.sort(key=lambda x: x["selection_score"], reverse=True)
        top3 = results[:3]

        st.success(f"🏆 {len(results)} matchs analysés avec succès !")

        for rank, result in enumerate(top3, 1):
            ranked = result["probabilities"]
            best_market, best_prob = ranked[0]
            second_market, second_prob = ranked[1]
            third_market, third_prob = ranked[2]

            st.markdown("---")
            st.subheader(f"🏆 #{rank} {result['home']} — {result['away']}")
            st.caption(f"🏆 {result['competition']}")

            c1, c2, c3 = st.columns(3)
            c1.metric("🎯 MT/FT", best_market)
            c2.metric("📊 Probabilité", f"{best_prob * 100:.2f}%")
            c3.metric("🧠 Qualité", f"{result['quality']:.0f}%")

            c4, c5 = st.columns(2)
            c4.metric("⚽ Buts dom. attendus", f"{result['lh']:.2f}")
            c5.metric("⚽ Buts ext. attendus", f"{result['la']:.2f}")

            st.write(f"🥈 Alternative : **{second_market}** — {second_prob * 100:.2f}%")
            st.write(f"🥉 Alternative : **{third_market}** — {third_prob * 100:.2f}%")

            table = pd.DataFrame(
                [{"Rang": i + 1, "MT/FT": m, "Probabilité": f"{p * 100:.2f}%"} for i, (m, p) in enumerate(ranked)]
            )
            st.dataframe(table, hide_index=True, use_container_width=True)

        st.markdown("---")
        st.warning("⚠️ Les pourcentages sont des estimations statistiques et ne garantissent pas un gain à 100%.")
        st.info("💯 Conseil : Privilégie les championnats majeurs avec beaucoup d'historique.")

    except Exception as e:
        st.error(f"❌ Une erreur est survenue : {e}")
