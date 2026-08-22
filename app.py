# app.py
import io
import math
import re
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

# Configuration de l'application
st.set_page_config(
    page_title="ROI DE POISSON — Analyse Pro",
    page_icon="⚽",
    layout="wide",
)

# -------------------------------------------------------------------------
# LOGIQUE MATHÉMATIQUE & FONCTIONS DE CALCUL
# -------------------------------------------------------------------------
def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def poisson_matrix(lam_home: float, lam_away: float, max_goals: int = 8) -> np.ndarray:
    ph = np.array([poisson_pmf(i, lam_home) for i in range(max_goals + 1)])
    pa = np.array([poisson_pmf(j, lam_away) for j in range(max_goals + 1)])
    m = np.outer(ph, pa)
    s = m.sum()
    if s > 0:
        m /= s
    return m

def normalize_odds(odds: List[float]) -> np.ndarray:
    inv = np.array([1.0 / max(o, 1.01) for o in odds], dtype=float)
    return inv / inv.sum()

def recent_team_stats(rows: List[Dict]) -> Dict[str, float]:
    if not rows:
        return {"gf": 1.35, "ga": 1.35, "xgf": 1.35, "xga": 1.35, "n": 0}
    
    n_matchs = min(len(rows), 5)
    all_weights = np.array([1.00, 0.92, 0.84, 0.76, 0.68])
    weights = all_weights[:n_matchs]
    weights = weights / weights.sum()

    gf = sum(rows[i]["gf"] * weights[i] for i in range(n_matchs))
    ga = sum(rows[i]["ga"] * weights[i] for i in range(n_matchs))
    xgf = sum(rows[i]["xgf"] * weights[i] for i in range(n_matchs))
    xga = sum(rows[i]["xga"] * weights[i] for i in range(n_matchs))

    return {"gf": gf, "ga": ga, "xgf": xgf, "xga": xga, "n": len(rows)}

def market_expected_goals(p1: float, px: float, p2: float) -> Tuple[float, float]:
    target = np.array([p1, px, p2])
    best = (1.35, 1.10)
    best_loss = 1e9

    for lh in np.arange(0.25, 3.51, 0.05):
        for la in np.arange(0.20, 3.21, 0.05):
            mat = poisson_matrix(float(lh), float(la), 8)
            home = np.tril(mat, -1).sum()
            draw = np.trace(mat)
            away = np.triu(mat, 1).sum()
            probs = np.array([home, draw, away])
            loss = float(np.sum((probs - target) ** 2))
            if loss < best_loss:
                best_loss = loss
                best = (float(lh), float(la))
    return best

def blend_lambdas(
    market_lh: float, market_la: float,
    home_stats: Dict[str, float], away_stats: Dict[str, float],
    home_advantage: float, injury_home: float, injury_away: float,
) -> Tuple[float, float]:
    home_form_attack = 0.55 * home_stats["gf"] + 0.45 * home_stats["xgf"]
    away_defense = 0.55 * away_stats["ga"] + 0.45 * away_stats["xga"]
    
    away_form_attack = 0.55 * away_stats["gf"] + 0.45 * away_stats["xgf"]
    home_defense = 0.55 * home_stats["ga"] + 0.45 * home_stats["xga"]

    form_home = 0.58 * home_form_attack + 0.42 * away_defense
    form_away = 0.58 * away_form_attack + 0.42 * home_defense

    lh = 0.62 * market_lh + 0.38 * form_home
    la = 0.62 * market_la + 0.38 * form_away

    lh *= 1.0 + clamp(home_advantage / 100.0, -0.10, 0.15)
    lh *= 1.0 + clamp(injury_home / 100.0, -0.35, 0.20)
    la *= 1.0 + clamp(injury_away / 100.0, -0.35, 0.20)

    return clamp(lh, 0.15, 4.50), clamp(la, 0.15, 4.50)

def score_table(mat: np.ndarray, top_n: int = 10) -> pd.DataFrame:
    items = []
    for h in range(mat.shape[0]):
        for a in range(mat.shape[1]):
            items.append((f"{h} - {a}", float(mat[h, a] * 100.0)))
    items.sort(key=lambda x: x[1], reverse=True)
    df = pd.DataFrame(items[:top_n], columns=["Score Exact", "Probabilité"])
    df["Probabilité"] = df["Probabilité"].map("{:,.2f} %".format)
    return df

def compute_htft_probs(lam_h: float, lam_a: float) -> pd.DataFrame:
    lh_m1, la_m1 = lam_h * 0.45, lam_a * 0.45
    lh_m2, la_m2 = lam_h * 0.55, lam_a * 0.55

    m1 = poisson_matrix(lh_m1, la_m1, max_goals=4)
    m2 = poisson_matrix(lh_m2, la_m2, max_goals=4)

    p1_m1, px_m1, p2_m1 = np.tril(m1, -1).sum(), np.trace(m1), np.triu(m1, 1).sum()
    p1_m2, px_m2, p2_m2 = np.tril(m2, -1).sum(), np.trace(m2), np.triu(m2, 1).sum()

    scenarios = [
        ("1/1", p1_m1 * p1_m2), ("1/X", p1_m1 * px_m2), ("1/2", p1_m1 * p2_m2),
        ("X/1", px_m1 * p1_m2), ("X/X", px_m1 * px_m2), ("X/2", px_m1 * p2_m2),
        ("2/1", p2_m1 * p1_m2), ("2/X", p2_m1 * px_m2), ("2/2", p2_m1 * p2_m2)
    ]
    
    df = pd.DataFrame(scenarios, columns=["Marché MT-Fin", "Probabilité"])
    df["Probabilité"] = (df["Probabilité"] * 100).map("{:,.2f} %".format)
    return df.sort_values(by="Probabilité", ascending=False)

def market_probs_from_matrix(mat: np.ndarray) -> Dict[str, float]:
    return {
        "1": float(np.tril(mat, -1).sum()),
        "X": float(np.trace(mat)),
        "2": float(np.triu(mat, 1).sum()),
    }

def confidence_index(market: np.ndarray, model: np.ndarray, top_prob: float, sample_n: int, edge: float) -> Tuple[float, str, str]:
    agreement = 1.0 - float(np.mean(np.abs(market - model))) / 0.50
    agreement = clamp(agreement, 0.0, 1.0)
    sample_factor = clamp(sample_n / 10.0, 0.0, 1.0)
    top_factor = clamp((top_prob - 0.30) / 0.45, 0.0, 1.0)
    edge_factor = clamp(edge / 0.20, 0.0, 1.0)
    
    score = 100.0 * (0.38 * agreement + 0.18 * sample_factor + 0.29 * top_factor + 0.15 * edge_factor)
    score = clamp(score, 0.0, 100.0)

    # CORRECTION : Utilisation de la variable 'score' et non 'conf_score' qui n'existait pas encore ici
    if score >= 95:
        label = "SIGNAL EXCEPTIONNEL"
        color = "inverse"
    elif score >= 90:
        label = "SIGNAL TRÈS FORT"
        color = "normal"
    elif score >= 80:
        label = "SIGNAL FORT"
        color = "normal"
    else:
        label = "PRUDENCE / PAS DE PARI"
        color = "off"

    return round(score, 1), label, color

# -------------------------------------------------------------------------
# INTERFACE UTILISATEUR
# -------------------------------------------------------------------------
st.title("⚽ ROI DE POISSON — Analyse Pro Stratégique")
st.caption("Mise en valeur exclusive des marchés Score Exact et Mi-Temps/Fin (MT-Fin) avec filtres de signaux stricts.")

with st.sidebar:
    st.header("⚙️ Paramètres d'Ajustement")
    home_advantage = st.slider("Avantage domicile (%)", -10, 15, 5)
    max_goals = st.slider("Nombre de buts max simulés", 6, 12, 8)
    st.markdown("---")
    st.markdown("**Échelle des Signaux :**")
    st.markdown("🔥 **95–100** : Signal Exceptionnel\n🟢 **90–94** : Signal Très Fort\n🟢 **80–89** : Signal Fort\n🔴 **<80** : Prudence / Pas de pari")

tab1, tab2, tab3 = st.tabs(["📷 1. Captures d'écran", "📊 2. Paramètres du match", "🧠 3. Signaux & Marchés Cibles"])

with tab1:
    st.subheader("Vérification visuelle")
    c1, c2 = st.columns(2)
    with c1:
        img_score = st.file_uploader("Capture Score exact", type=["png", "jpg", "jpeg"], key="score_img")
        if img_score: st.image(Image.open(img_score), use_container_width=True)
    with c2:
        img_htft = st.file_uploader("Capture MT-Fin", type=["png", "jpg", "jpeg"], key="htft_img")
        if img_htft: st.image(Image.open(img_htft), use_container_width=True)

with tab2:
    st.subheader("Données d'entrée (Traitement en arrière-plan)")
    col_odds, col_injuries = st.columns(2)
    with col_odds:
        st.markdown("**Cotes du Marché 1X2**")
        o1 = st.number_input("Cote Domicile (1)", min_value=1.01, value=2.10, step=0.05)
        ox = st.number_input("Cote Nul (X)", min_value=1.01, value=3.40, step=0.05)
        o2 = st.number_input("Cote Extérieur (2)", min_value=1.01, value=3.50, step=0.05)
    with col_injuries:
        st.markdown("**Impact Blessures (Attaque %)**")
        inj_home = st.slider("Impact Domicile (%)", -35, 20, 0)
        inj_away = st.slider("Impact Extérieur (%)", -35, 20, 0)

    st.markdown("---")
    st.markdown("**Forme récente (Calcul pondéré sur les derniers matchs)**")
    ch, ca = st.columns(2)
    with ch:
        st.markdown("*Forme Domicile (Buts Marqués / Encaissés)*")
        h_rows = []
        for i in range(1, 4):
            cx1, cx2 = st.columns(2)
            gf = cx1.number_input(f"Match -{i} : GF", min_value=0, value=2, key=f"h_gf_{i}")
            ga = cx2.number_input(f"Match -{i} : GA", min_value=0, value=1, key=f"h_ga_{i}")
            h_rows.append({"gf": gf, "ga": ga, "xgf": gf * 1.05, "xga": ga * 0.95})
    with ca:
        st.markdown("*Forme Extérieur (Buts Marqués / Encaissés)*")
        a_rows = []
        for i in range(1, 4):
            cx1, cx2 = st.columns(2)
            gf = cx1.number_input(f"Match -{i} : GF", min_value=0, value=1, key=f"a_gf_{i}")
            ga = cx2.number_input(f"Match -{i} : GA", min_value=0, value=1, key=f"a_ga_{i}")
            a_rows.append({"gf": gf, "ga": ga, "xgf": gf * 1.0, "xga": ga * 1.0})

with tab3:
    p_market = normalize_odds([o1, ox, o2])
    m_lh, m_la = market_expected_goals(p_market[0], p_market[1], p_market[2])
    
    h_stats = recent_team_stats(h_rows)
    a_stats = recent_team_stats(a_rows)
    final_lh, final_la = blend_lambdas(m_lh, m_la, h_stats, a_stats, home_advantage, inj_home, inj_away)
    
    mat_model = poisson_matrix(final_lh, final_la, max_goals)
    probs_model = market_probs_from_matrix(mat_model)
    
    top_score_prob = float(mat_model.max())
    edge = abs(probs_model["1"] - p_market[0])
    
    conf_score, conf_label, conf_color = confidence_index(
        p_market, 
        np.array([probs_model["1"], probs_model["X"], probs_model["2"]]), 
        top_score_prob, 
        h_stats["n"] + a_stats["n"], 
        edge
    )
    
    st.subheader("⚡ Évaluation Statistique Globale")
    
    # Gestion propre de l'affichage de fin de script
    if conf_score >= 95:
        st.success(f"Score de Confiance : {conf_score} / 100 — {conf_label}")
    elif conf_score >= 90:
        st.info(f"Score de Confiance : {conf_score} / 100 — {conf_label}")
    elif conf_score >= 80:
        st.warning(f"Score de Confiance : {conf_score} / 100 — {conf_label}")
    else:
        st.error(f"Score de Confiance : {conf_score} / 100 — {conf_label}")

    st.markdown("### 🎯 Marchés Cibles Recommandés")
    col_res1, col_res2 = st.columns(2)
    
    with col_res1:
        st.markdown("#### Top Scores Exacts")
        df_scores = score_table(mat_model, top_n=5)
        st.dataframe(df_scores, use_container_width=True)
        
    with col_res2:
        st.markdown("#### Probabilités Mi-Temps / Fin de Match")
        df_htft = compute_htft_probs(final_lh, final_la)
        st.dataframe(df_htft.head(5), use_container_width=True)
