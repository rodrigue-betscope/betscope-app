# app.py
import io
import math
import re
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

# Configuration de la page principale
st.set_page_config(
    page_title="ROI DE POISSON — Analyse Pro",
    page_icon="⚽",
    layout="wide",
)

# -------------------------------------------------------------------------
# Outils mathématiques & Distribution de Poisson
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
    """Convertit les cotes décimales en probabilités implicites normalisées."""
    inv = np.array([1.0 / max(o, 1.01) for o in odds], dtype=float)
    return inv / inv.sum()

def recent_team_stats(rows: List[Dict]) -> Dict[str, float]:
    """Stats pondérées: le match le plus récent pèse le plus (jusqu'à 5 matchs)."""
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
    """Approximation des lambdas à partir du marché 1X2."""
    target = np.array([p1, px, p2])
    best = (1.35, 1.10)
    best_loss = 1e9

    for lh in np.arange(0.25, 3.51, 0.05):
        for la in np.arange(0.20, 3.21, 0.05):
            mat = poisson_matrix(float(lh), float(la), 8)
            home = np.tril(mat, -1).sum()   # i > j
            draw = np.trace(mat)
            away = np.triu(mat, 1).sum()    # i < j
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
    """Mélange les probabilités du marché et la forme statistique récente."""
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

def score_table(mat: np.ndarray, top_n: int = 12) -> pd.DataFrame:
    items = []
    for h in range(mat.shape[0]):
        for a in range(mat.shape[1]):
            items.append((f"{h}-{a}", float(mat[h, a] * 100.0)))
    items.sort(key=lambda x: x[1], reverse=True)
    return pd.DataFrame(items[:top_n], columns=["Score", "Probabilité %"])

def compute_htft_probs(lam_h: float, lam_a: float) -> pd.DataFrame:
    """Simule le marché Mi-Temps / Fin du Match (MT-Fin) via Poisson."""
    # En moyenne, 45% des buts surviennent en MT1, et 55% en MT2
    lh_m1, la_m1 = lam_h * 0.45, lam_a * 0.45
    lh_m2, la_m2 = lam_h * 0.55, lam_a * 0.55

    m1 = poisson_matrix(lh_m1, la_m1, max_goals=4)
    m2 = poisson_matrix(lh_m2, la_m2, max_goals=4)

    # Catégorisation des issues de chaque période
    p1_m1 = np.tril(m1, -1).sum()
    px_m1 = np.trace(m1)
    p2_m1 = np.triu(m1, 1).sum()

    p1_m2 = np.tril(m2, -1).sum()
    px_m2 = np.trace(m2)
    p2_m2 = np.triu(m2, 1).sum()

    # Combinaisons de scénarios MT / FM
    scenarios = [
        ("1/1", p1_m1 * p1_m2), ("1/X", p1_m1 * px_m2), ("1/2", p1_m1 * p2_m2),
        ("X/1", px_m1 * p1_m2), ("X/X", px_m1 * px_m2), ("X/2", px_m1 * p2_m2),
        ("2/1", p2_m1 * p1_m2), ("2/X", p2_m1 * px_m2), ("2/2", p2_m1 * p2_m2)
    ]
    
    df = pd.DataFrame(scenarios, columns=["Scénario MT/FM", "Probabilité %"])
    df["Probabilité %"] = round(df["Probabilité %"] * 100, 2)
    return df.sort_values(by="Probabilité %", ascending=False)

def market_probs_from_matrix(mat: np.ndarray) -> Dict[str, float]:
    return {
        "1": float(np.tril(mat, -1).sum()),
        "X": float(np.trace(mat)),
        "2": float(np.triu(mat, 1).sum()),
    }

def over_prob(mat: np.ndarray, line: float) -> float:
    p = 0.0
    for h in range(mat.shape[0]):
        for a in range(mat.shape[1]):
            if h + a > line:
                p += mat[h, a]
    return p

def btts_prob(mat: np.ndarray) -> float:
    return float(mat[1:, 1:].sum())

def confidence_index(market: np.ndarray, model: np.ndarray, top_prob: float, sample_n: int, edge: float) -> Tuple[float, str]:
    agreement = 1.0 - float(np.mean(np.abs(market - model))) / 0.50
    agreement = clamp(agreement, 0.0, 1.0)
    sample_factor = clamp(sample_n / 10.0, 0.0, 1.0)
    top_factor = clamp((top_prob - 0.30) / 0.45, 0.0, 1.0)
    edge_factor = clamp(edge / 0.20, 0.0, 1.0)
    
    score = 100.0 * (0.38 * agreement + 0.18 * sample_factor + 0.29 * top_factor + 0.15 * edge_factor)

    if score >= 82: label = "TRÈS FORTE 🔥🔥🔥"
    elif score >= 72: label = "FORTE 🔥🔥"
    elif score >= 60: label = "MOYENNE ⚠️"
    else: label = "PRUDENCE 🛑"

    return score, label

# -------------------------------------------------------------------------
# OCR Facultatif
# -------------------------------------------------------------------------
def ocr_image(image: Image.Image) -> str:
    try:
        import pytesseract
        return pytesseract.image_to_string(image, config="--psm 6")
    except Exception:
        return "Tesseract n'est pas installé ou configuré sur ce système."

# -------------------------------------------------------------------------
# Interface Utilisateur Streamlit
# -------------------------------------------------------------------------
st.title("⚽ ROI DE POISSON — Analyse Pro")
st.caption("Analyse stratégique combinant modélisation de Poisson, cotes du marché, forme récente et gestion des blessures.")

with st.sidebar:
    st.header("⚙️ Paramètres Généraux")
    home_advantage = st.slider("Avantage domicile (%)", -10, 15, 5)
    max_goals = st.slider("Nombre de buts maximum simulés", 6, 12, 8)
    st.info("⚠️ Les modèles mathématiques procurent des indicateurs de tendance. Aucun algorithme ne garantit un succès à 100%.")

tab1, tab2, tab3 = st.tabs(["📷 1. Captures d'écran (OCR)", "📊 2. Données du Match", "🧠 3. Analyse & Résultats"])

with tab1:
    st.subheader("Extraction visuelle optionnelle")
    c1, c2 = st.columns(2)
    with c1:
        img_score = st.file_uploader("Capture Score exact", type=["png", "jpg", "jpeg"], key="score_img")
        if img_score:
            image1 = Image.open(img_score)
            st.image(image1, caption="Aperçu Score Exact", use_container_width=True)
            txt1 = ocr_image(image1)
            with st.expander("Texte brut extrait (OCR)"):
                st.code(txt1)
    with c2:
        img_htft = st.file_uploader("Capture MT-Fin", type=["png", "jpg", "jpeg"], key="htft_img")
        if img_htft:
            image2 = Image.open(img_htft)
            st.image(image2, caption="Aperçu MT-Fin", use_container_width=True)
            txt2 = ocr_image(image2)
            with st.expander("Texte brut extrait (OCR)"):
                st.code(txt2)

with tab2:
    st.subheader("Saisie manuelle des données du match")
    
    col_odds, col_injuries = st.columns(2)
    with col_odds:
        st.markdown("**Cotes du Marché 1X2**")
        o1 = st.number_input("Cote Victoire Domicile (1)", min_value=1.01, value=2.10, step=0.05)
        ox = st.number_input("Cote Match Nul (X)", min_value=1.01, value=3.40, step=0.05)
        o2 = st.number_input("Cote Victoire Extérieur (2)", min_value=1.01, value=3.50, step=0.05)
    with col_injuries:
        st.markdown("**Impact des Blessures (Attaque)**")
        inj_home = st.slider("Impact Équipe Domicile (%)", -35, 20, 0, help="Négatif = Attaque affaiblie")
        inj_away = st.slider("Impact Équipe Extérieur (%)", -35, 20, 0)

    st.markdown("---")
    st.markdown("**Historique Récent (Forme & xG des 5 derniers matchs)**")
    
    ch, ca = st.columns(2)
    with ch:
        st.markdown("*Équipe à Domicile*")
        h_rows = []
        for i in range(1, 4):
            c_a, c_b = st.columns(2)
            gf = c_a.number_input(f"Match -{i} : Buts Marqués", min_value=0, value=1, key=f"h_gf_{i}")
            ga = c_b.number_input(f"Match -{i} : Buts Encaissés", min_value=0, value=1, key=f"h_ga_{i}")
            h_rows.append({"gf": gf, "ga": ga, "xgf": gf * 1.1, "xga": ga * 0.9})
            
    with ca:
        st.markdown("*Équipe à l'Extérieur*")
        a_rows = []
