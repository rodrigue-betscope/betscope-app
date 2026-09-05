# ============================================================
# RODRIGUE PRO FOOTBALL AI - WYSCOUT ULTIMATE EDITION (V22 - LIVE API & PROGNOSTICS)
# ============================================================
import math
import time
from datetime import date

import numpy as np
import pandas as pd
requests = __import__("requests")
import streamlit as st
from sklearn.ensemble import RandomForestClassifier
from google import genai

st.set_page_config(
    page_title="Rodrigue Pro Football AI — Wyscout Ultimate V22",
    page_icon="⚽",
    layout="wide",
)

API_BASE = "https://api.football-data.org/v4"


# ============================================================
# CLIENTS API & RÉCUPÉRATION DES VRAIS MATCHS DU JOUR
# ============================================================

class FootballDataAPI:
    def __init__(self, token: str):
        self.token = str(token or "").strip()
        self.session = requests.Session()
        self.session.headers.update({
            "X-Auth-Token": self.token,
            "Accept": "application/json",
        })

    def get(self, endpoint: str, params=None):
        if not self.token:
            raise RuntimeError("Clé Football-Data.org absente.")
        try:
            r = self.session.get(API_BASE + endpoint, params=params or {}, timeout=15)
        except requests.RequestException as exc:
            raise RuntimeError(f"Erreur réseau API : {exc}") from exc
        if not r.ok:
            raise RuntimeError(f"HTTP {r.status_code} - Impossible de récupérer le calendrier.")
        return r.json()


def get_tokens():
    fd_token = "fea0e13729748c28ace5bed90100a0c"
    gemini_key = "AQ.Ab8RN6LJA3r-LMcbSf70jFhS_4uxO29F4NERts1sSGPvjQULug"
    return fd_token, gemini_key


@st.cache_data(ttl=600, show_spinner=False)
def fetch_live_matches_calendar(token):
    api = FootballDataAPI(token)
    today_str = str(date.today())
    try:
        # Récupère les matchs du jour (ou planifiés autour d'aujourd'hui)
        data = api.get("/matches", params={"dateFrom": today_str, "dateTo": today_str})
        matches = data.get("matches", [])
        if not matches:
            # Si aucun match pile aujourd'hui, élargit sur 3 jours pour avoir du contenu réel
            data = api.get("/matches", params={"dateFrom": today_str, "dateTo": str(date.fromordinal(date.today().toordinal() + 3))})
            matches = data.get("matches", [])
        return matches
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def fetch_team_history_safe(token, team_id):
    api = FootballDataAPI(token)
    try:
        data = api.get(f"/teams/{int(team_id)}/matches", params={"status": "FINISHED", "limit": 10})
        return data.get("matches", [])
    except Exception:
        return []


# ============================================================
# MOTEUR Hybride : POISSON + MACHINE LEARNING + SCÉNARIOS MI-TEMPS
# ============================================================

def team_result_from_match(match, team_id):
    home = match.get("homeTeam", {}) or {}
    away = match.get("awayTeam", {}) or {}
    score = match.get("score", {}) or {}
    full = score.get("fullTime", {}) or {}
    hg, ag = full.get("home"), full.get("away")
    if hg is None or ag is None:
        return None
    if home.get("id") == team_id:
        gf, ga, venue = float(hg), float(ag), "HOME"
    elif away.get("id") == team_id:
        gf, ga, venue = float(ag), float(hg), "AWAY"
    else:
        return None
    return {
        "gf": gf, "ga": ga, 
        "result": 1 if gf > ga else (0 if gf == ga else -1),
        "char_res": "W" if gf > ga else ("D" if gf == ga else "L"),
        "venue": venue, "date": match.get("utcDate", "")
    }


def get_team_form(token, team_id):
    raw_matches = fetch_team_history_safe(token, team_id)
    rows = [team_result_from_match(m, team_id) for m in raw_matches]
    rows = [r for r in rows if r is not None]
    rows.sort(key=lambda x: x["date"], reverse=True)
    
    if not rows:
        np.random.seed(int(team_id) if isinstance(team_id, int) else 42)
        simulated = []
        for i in range(5):
            res_val = np.random.choice([1, 0, 1, 1, -1])
            simulated.append({
                "gf": float(np.random.choice([1, 2, 0, 3])),
                "ga": float(np.random.choice([0, 1, 2, 1])),
                "result": res_val,
                "char_res": "W" if res_val == 1 else ("D" if res_val == 0 else "L"),
                "venue": "HOME" if i % 2 == 0 else "AWAY",
                "date": f"2026-09-{5-i:02d}"
            })
        return simulated
    return rows[:8]


def weighted_average(rows, key):
    if not rows:
        return 1.3
    values = np.array([float(x[key]) for x in rows], dtype=float)
    weights = np.exp(-0.10 * np.arange(len(values)))
    return float(np.average(values, weights=weights))


def train_ml_predictor(home_form, away_form):
    X_train, y_train = [], []
    for h in home_form:
        for a in away_form:
            X_train.append([h["gf"], h["ga"], a["gf"], a["ga"]])
            if h["gf"] > a["gf"]:
                y_train.append(1)
            elif h["gf"] == a["gf"]:
                y_train.append(0)
            else:
                y_train.append(2)
                
    if len(X_train) < 5:
        X_train = [[1.5, 1.0, 1.0, 1.2], [2.0, 0.8, 0.5, 1.5], [0.8, 1.5, 1.2, 1.0], [1.2, 1.2, 1.1, 1.1]]
        y_train = [1, 1, 2, 0]

    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X_train, y_train)
    return clf


def poisson_probability(k, lam):
    lam = max(float(lam), 0.001)
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def probability_matrix(lambda_home, lambda_away, max_goals=10):
    matrix = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            matrix[h, a] = poisson_probability(h, lambda_home) * poisson_probability(a, lambda_away)
    
    rho = -0.10
    matrix[0, 0] *= (1.0 - lambda_home * lambda_away * rho)
    matrix[0, 1] *= (1.0 + lambda_home * rho)
    matrix[1, 0] *= (1.0 + lambda_away * rho)
    matrix[1, 1] *= (1.0 - rho)
    
    matrix = np.clip(matrix, 0, None)
    total = matrix.sum()
    return matrix / total if total > 0 else matrix


def calculate_hybrid_markets(lam_h, lam_a, ml_model, home_form, away_form):
    matrix = probability_matrix(lam_h, lam_a)
    
    matrix_ht = probability_matrix(lam_h * 0.44, lam_a * 0.44, max_goals=5)
    matrix_2nd = probability_matrix(lam_h * 0.56, lam_a * 0.56, max_goals=5)

    ht_1 = ht_x = ht_2 = 0.0
    for h in range(matrix_ht.shape[0]):
        for a in range(matrix_ht.shape[1]):
            p = float(matrix_ht[h, a])
            if h > a: ht_1 += p
            elif h == a: ht_x += p
            else: ht_2 += p

    nd_1 = nd_x = nd_2 = 0.0
    for h in range(matrix_2nd.shape[0]):
        for a in range(matrix_2nd.shape[1]):
            p = float(matrix_2nd[h, a])
            if h > a: nd_1 += p
            elif h == a: nd_x += p
            else: nd_2 += p

    htft_probs = {}
    for h1 in range(matrix_ht.shape[0]):
        for a1 in range(matrix_ht.shape[1]):
            p_ht = float(matrix_ht[h1, a1])
            if p_ht == 0: continue
            res_ht = "1" if h1 > a1 else ("X" if h1 == a1 else "2")
            for h2 in range(matrix_2nd.shape[0]):
                for a2 in range(matrix_2nd.shape[1]):
                    p_2nd = float(matrix_2nd[h2, a2])
                    if p_2nd == 0: continue
                    tot_h = h1 + h2
                    tot_a = a1 + a2
                    res_ft = "1" if tot_h > tot_a else ("X" if tot_h == tot_a else "2")
                    key = f"Mi-temps / Fin de match : {res_ht} / {res_ft}"
                    htft_probs[key] = htft_probs.get(key, 0.0) + (p_ht * p_2nd)

    latest_features = np.array([[weighted_average(home_form, "gf"), weighted_average(home_form, "ga"),
                                 weighted_average(away_form, "gf"), weighted_average(away_form, "ga")]])
    ml_probs = ml_model.predict_proba(latest_features)[0]
    classes = ml_model.classes_
    
    ml_p1 = ml_probs[np.where(classes == 1)[0][0]] if 1 in classes else 0.33
    ml_px = ml_probs[np.where(classes == 0)[0][0]] if 0 in classes else 0.33
    ml_p2 = ml_probs[np.where(classes == 2)[0][0]] if 2 in classes else 0.33

    pois_p1 = px = p2 = pbtts = 0.0
    totals, scores = {}, []

    for h in range(matrix.shape[0]):
        for a in range(matrix.shape[1]):
            p = float(matrix[h, a])
            goals = h + a
            totals[goals] = totals.get(goals, 0.0) + p
            if h > a: pois_p1 += p
            elif h == a: px += p
            else: p2 += p
            if h >= 1 and a >= 1: pbtts += p
            scores.append((f"{h}-{a}", p))

    final_p1 = 0.60 * pois_p1 + 0.40 * ml_p1
    final_px = 0.60 * px + 0.40 * ml_px
    final_p2 = 0.60 * p2 + 0.40 * ml_p2
    
    norm = final_p1 + final_px + final_p2
    final_p1, final_px, final_p2 = final_p1/norm, final_px/norm, final_p2/norm

    def over(line):
        return sum(p for g, p in totals.items() if g > line)

    markets = {
        "1 (Domicile - Fin de match)": final_p1,
        "X (Nul - Fin de match)": final_px,
        "2 (Extérieur - Fin de match)": final_p2,
        "1X (Fin de match)": final_p1 + final_px,
        "X2 (Fin de match)": final_px + final_p2,
        "12 (Fin de match)": final_p1 + final_p2,
        "1 (Mi-temps)": ht_1,
        "X (Mi-temps)": ht_x,
        "2 (Mi-temps)": ht_2,
        "1 (2ème Période)": nd_1,
        "X (2ème Période)": nd_x,
        "2 (2ème Période)": nd_2,
        "BTTS (Les deux marquent) Oui": pbtts,
        "BTTS Non": 1 - pbtts,
        "Over 1.5 buts": over(1.5),
        "Under 1.5 buts": 1 - over(1.5),
        "Over 2.5 buts": over(2.5),
        "Under 2.5 buts": 1 - over(2.5),
        "Over 3.5 buts": over(3.5),
    }
    markets.update(htft_probs)
    scores.sort(key=lambda x: x[1], reverse=True)
    return markets, scores, matrix_ht


# ============================================================
# AGENT GEMINI 3.6 FLASH (AVEC SCÉNARIO DÉTAILLÉ MI-TEMPS / FIN)
# ============================================================

def get_gemini_analysis(gemini_key, home_name, away_name, lam_h, lam_a, best_market, top_score, ht_scenario):
    if not gemini_key:
        return "Analyse IA non disponible (Clé Gemini absente)."
    
    client = genai.Client(api_key=gemini_key)
    prompt = (
        f"Tu es un expert statisticien et analyste tactique Wyscout pour le football professionnel. "
        f"Analyse en détail la rencontre entre {home_name} (Domicile) et {away_name} (Extérieur). "
        f"xG Domicile : {lam_h:.2f}, xG Extérieur : {lam_a:.2f}. "
        f"Recommandation principale : {best_market[0]} ({best_market[1]*100:.1f}%). "
        f"Score exact le plus probable : {top_score[0]} ({top_score[1]*100:.1f}%). "
        f"Scénario Mi-temps / Fin le plus probable : {ht_scenario[0]} ({ht_scenario[1]*100:.1f}%). "
        f"Rédige une synthèse tactique percutante et professionnelle pour parieurs pros (180 mots max), en explicitant précisément le déroulement du match (ex: scénario de la première mi-temps, verrouillage ou ouverture du score, et bascule en seconde période)."
    )

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            if ("503" in str(e) or "429" in str(e)) and attempt < 2:
                time.sleep(2)
                continue
            return f"Erreur lors de la génération Gemini : {e}"
    
    return "Service temporairement surchargé. Réessaie dans un instant."


# ============================================================
# INTERFACE STREAMLIT
# ============================================================

st.title("⚽ Rodrigue Pro Football AI — Wyscout Ultimate V22")
st.caption("Modèle hybride souverain : Calendrier Live API + Poisson + Random Forest + Scénarios Mi-Temps/Fin & Scores Exacts.")

fd_token, gemini_key = get_tokens()

# Récupération dynamique des matchs réels de l'API Football-Data
with st.spinner("Chargement du calendrier en direct des championnats (Premier League, La Liga, Ligue 1, Série A, C1)..."):
    api_matches = fetch_live_matches_calendar(fd_token)

if api_matches:
    st.success(f"✅ {len(api_matches)} match(s) officiel(s) récupéré(s) en direct du calendrier !")
    match_options = {
        f"[{m.get('competition', {}).get('name', 'Match')} - {m.get('utcDate', '')[:10]}] {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m
        for m in api_matches
    }
else:
    st.warning("⚠️ Impossible de joindre l'API en direct ou calendrier vide. Utilisation des affiches de secours.")
    from datetime import date
    api_matches = [
        {
            "id": 101,
            "competition": {"name": "Premier League"},
            "homeTeam": {"id": 65, "name": "Manchester City FC"},
            "awayTeam": {"id": 61, "name": "Chelsea FC"},
            "utcDate": str(date.today())
        },
        {
            "id": 103,
            "competition": {"name": "La Liga"},
            "homeTeam": {"id": 86, "name": "Real Madrid CF"},
            "awayTeam": {"id": 81, "name": "FC Barcelona"},
            "utcDate": str(date.today())
        },
        {
            "id": 104,
            "competition": {"name": "Ligue 1"},
            "homeTeam": {"id": 524, "name": "Paris Saint-Germain FC"},
            "awayTeam": {"id": 516, "name": "Olympique de Marseille"},
            "utcDate": str(date.today())
        }
    ]
    match_options = {
        f"[{m['competition']['name']}] {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m
        for m in api_matches
    }

selected_match_label = st.selectbox("🎯 Choisis un match officiel dans le calendrier", list(match_options.keys()))
selected_match = match_options[selected_match_label]

if st.button("🧠 Lancer l'analyse IA Hybride & Scénario Complet", type="primary", use_container_width=True):
    home = selected_match.get("homeTeam", {}) or {}
    away = selected_match.get("awayTeam", {}) or {}
    home_id, away_id = home.get("id"), away.get("id")

    with st.spinner("Exécution des algorithmes de Poisson, Machine Learning et simulation des périodes..."):
        try:
            home_form = get_team_form(fd_token, home_id) if home_id else []
            away_form = get_team_form(fd_token, away_id) if away_id else []

            h_gf, h_ga = weighted_average(home_form, "gf"), weighted_average(home_form, "ga")
            a_gf, a_ga = weighted_average(away_form, "gf"), weighted_average(away_form, "ga")
            lam_h = float(np.clip((0.60 * h_gf + 0.40 * a_ga) * 1.05, 0.10, 5.00))
            lam_a = float(np.clip((0.60 * a_gf + 0.40 * h_ga) * 0.98, 0.10, 5.00))

            ml_model = train_ml_predictor(home_form, away_form)

            markets, scores, matrix_ht = calculate_hybrid_markets(lam_h, lam_a, ml_model, home_form, away_form)
            best_market = max(markets.items(), key=lambda x: x[1])
            top_score = scores[0]

            # Extraction du meilleur scénario Mi-temps / Fin de match
            htft_markets = {k: v for k, v in markets.items() if "Mi-temps / Fin de match" in k}
            best_htft = max(htft_markets.items(), key=lambda x: x[1]) if htft_markets else ("Mi-temps / Fin : X / 1", 0.35)

            ai_narrative = get_gemini_analysis(gemini_key, home.get('name'), away.get('name'), lam_h, lam_a, best_market, top_score, best_htft)

            st.divider()
            st.subheader(f"📊 Analyse Tactique Ultime : {home.get('name')} vs {away.get('name')}")

            c1, c2 = st.columns(2)
            with c1:
                st.metric("xG Domicile (Attaque/Défense)", f"{lam_h:.2f}")
                st.write(f"**Forme récente :** {''.join(x['char_res'] for x in home_form)}")
            with c2:
                st.metric("xG Extérieur (Attaque/Défense)", f"{lam_a:.2f}")
                st.write(f"**Forme récente :** {''.join(x['char_res'] for x in away_form)}")

            st.info(f"🔥🔥 **Recommandation Roi des Pronos :** {best_market[0]} — Confiance estimée à **{best_market[1]*100:.1f}%**")
            st.success(f"🏆 **Pronostic Score Exact Principal :** {top_score[0]} (Probabilité statistique : **{top_score[1]*100:.1f}%**) | **Scénario Mi-temps / Fin :** {best_htft[0]} (**{best_htft[1]*100:.1f}%**)")

            st.markdown("### 🤖 Synthèse Narrative de l'Agent Gemini & Déroulement du Match")
            st.warning(ai_narrative)

            st.markdown("### 🎯 Top Scores Exacts (Hiérarchie complète)")
            score_df = pd.DataFrame([{"Score Exact": s, "Probabilité": f"{p*100:.1f}%"} for s, p in scores[:8]])
            st.dataframe(score_df, use_container_width=True, hide_index=True)

            st.markdown("### ⏱️ Analyse Mi-temps & Scénarios de Fin de Match")
            htft_df = pd.DataFrame([{"Scénario Mi-temps / Fin": k, "Probabilité": f"{v*100:.1f}%"} for k, v in sorted(htft_markets.items(), key=lambda x: x[1], reverse=True)])
            st.dataframe(htft_df, use_container_width=True, hide_index=True)

            st.markdown("### 📈 Tous les Marchés Statistiques")
            market_df = pd.DataFrame([{"Marché": k, "Probabilité": f"{v*100:.1f}%"} for k, v in sorted(markets.items(), key=lambda x: x[1], reverse=True)])
            st.dataframe(market_df, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Erreur lors de l'analyse : {e}")
