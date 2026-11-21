# -*- coding: utf-8 -*-
"""RODRIGUE PRO MT/FT ENGINE ELITE
A transparent, educational half-time/full-time probability calculator.
No predictions or profits are guaranteed. Lambda inputs are assumptions unless
estimated from verified data outside this tool.
Run: streamlit run rodrigue_mtft_engine_elite.py
"""
import math
from itertools import product
import pandas as pd
import streamlit as st


st.set_page_config(page_title="RODRIGUE PRO MT/FT ELITE", page_icon="⚽", layout="wide")

COMBOS = ["1/1", "X/1", "2/1", "1/X", "X/X", "2/X", "1/2", "X/2", "2/2"]


def poisson_pmf(k: int, lam: float) -> float:
    if lam < 0:
        raise ValueError("Lambda must be non-negative")
    if lam == 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def outcome(h: int, a: int) -> str:
    return "1" if h > a else "2" if h < a else "X"


def calculate_mtft(lh1, la1, lh2, la2, max_goals=10):
    # Independent Poisson assumptions for each team and each half.
    # Truncate at max_goals per half and renormalize retained mass.
    half_home_1 = [poisson_pmf(k, lh1) for k in range(max_goals + 1)]
    half_away_1 = [poisson_pmf(k, la1) for k in range(max_goals + 1)]
    half_home_2 = [poisson_pmf(k, lh2) for k in range(max_goals + 1)]
    half_away_2 = [poisson_pmf(k, la2) for k in range(max_goals + 1)]

    combos = {c: 0.0 for c in COMBOS}
    paths = {c: [] for c in COMBOS}
    total_mass = 0.0

    for h1, a1, h2, a2 in product(range(max_goals + 1), repeat=4):
        p = half_home_1[h1] * half_away_1[a1] * half_home_2[h2] * half_away_2[a2]
        if p <= 0:
            continue
        mt = outcome(h1, a1)
        ft = outcome(h1 + h2, a1 + a2)
        combo = f"{mt}/{ft}"
        combos[combo] += p
        total_mass += p
        paths[combo].append({
            "Pause": f"{h1}-{a1}",
            "2e mi-temps": f"{h2}-{a2}",
            "Final": f"{h1+h2}-{a1+a2}",
            "Probabilité trajet (%)": p * 100,
        })

    # Renormalize truncated distributions so probabilities sum to 100%.
    if total_mass > 0:
        combos = {c: p / total_mass for c, p in combos.items()}
        for c in paths:
            for row in paths[c]:
                row["Probabilité trajet (%)"] /= total_mass
    return combos, paths, total_mass



def implied_prob(odds):
    return 1.0 / odds if odds and odds > 1.0 else None



st.title("⚽ RODRIGUE PRO — MT/FT ENGINE ELITE")
st.caption("Calcul probabiliste transparent • 9 scénarios • scores possibles • comparaison aux cotes • pas de garantie de gain")
st.warning("Ce calcul est un modèle, pas une certitude. Les lambdas saisis ci-dessous sont des hypothèses. Ne mise pas de l'argent nécessaire à tes dépenses.")

with st.expander("📘 Comprendre les 9 marchés", expanded=False):
    st.markdown("**1** = domicile mène/gagne • **X** = nul • **2** = extérieur mène/gagne. Le premier signe concerne la mi-temps, le second le résultat final.")
    st.write("1/1 Domicile–Domicile | X/1 Nul–Domicile | 2/1 Extérieur–Domicile")
    st.write("1/X Domicile–Nul | X/X Nul–Nul | 2/X Extérieur–Nul")
    st.write("1/2 Domicile–Extérieur | X/2 Nul–Extérieur | 2/2 Extérieur–Extérieur")

st.subheader("1) Entrer les buts attendus (λ) par période")
colh, cola = st.columns(2)
with colh:
    st.markdown("### 🏠 Équipe domicile")
    home_ht = st.number_input("λ domicile — 1re mi-temps", 0.0, 5.0, 0.70, 0.05, key="hht")
    home_2h = st.number_input("λ domicile — 2e mi-temps", 0.0, 5.0, 0.85, 0.05, key="h2")
with cola:
    st.markdown("### ✈️ Équipe extérieure")
    away_ht = st.number_input("λ extérieur — 1re mi-temps", 0.0, 5.0, 0.40, 0.05, key="aht")
    away_2h = st.number_input("λ extérieur — 2e mi-temps", 0.0, 5.0, 0.55, 0.05, key="a2")

st.subheader("2) Vérification de la valeur avec une cote bookmaker (facultatif)")
selected_combo = st.selectbox("Marché à comparer", COMBOS)
book_odds = st.number_input("Cote décimale", min_value=1.01, max_value=1000.0, value=3.00, step=0.05)

if st.button("🧮 CALCULER ET CLASSER", type="primary", use_container_width=True):
    probs, score_paths, retained = calculate_mtft(home_ht, away_ht, home_2h, away_2h)
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    results_df = pd.DataFrame([{"Rang": i+1, "MT/FT": c, "Probabilité modèle (%)": round(p*100, 2),
                               "Cote juste (sans marge)": round(1/p, 2) if p > 0 else None}
                              for i, (c, p) in enumerate(ranked)])
    st.subheader("Classement des 9 scénarios")
    st.dataframe(results_df, hide_index=True, use_container_width=True)
    st.bar_chart(results_df.set_index("MT/FT")["Probabilité modèle (%)"])

    p = probs[selected_combo]
    fair_odds = 1 / p if p > 0 else float("inf")
    book_implied = implied_prob(book_odds)
    ev = p * book_odds - 1
    st.subheader(f"Comparaison de {selected_combo}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Probabilité modèle", f"{p*100:.2f}%")
    c2.metric("Cote juste théorique", f"{fair_odds:.2f}")
    c3.metric("Probabilité implicite cote", f"{book_implied*100:.2f}%")
    c4.metric("EV théorique", f"{ev*100:+.2f}%")
    if ev > 0:
        st.info("La cote est supérieure à la cote juste selon ce modèle. Cela ne prouve pas qu'il existe un avantage réel : la calibration du modèle et la qualité des données doivent être vérifiées.")
    else:
        st.warning("Selon ces lambdas, la cote ne montre pas d'espérance de valeur positive. Ce calcul ne tient pas compte de la marge bookmaker ni des erreurs de modèle.")

    st.subheader("Scores / trajectoires les plus probables par marché")
    for combo, prob in ranked:
        with st.expander(f"{combo} — {prob*100:.2f}%"):
            paths = sorted(score_paths[combo], key=lambda r: r["Probabilité trajet (%)"], reverse=True)
            # Display top 8 trajectories, each probability is the joint path probability.
            frame = pd.DataFrame(paths[:8])
            if not frame.empty:
                frame["Probabilité trajet (%)"] = frame["Probabilité trajet (%)"].round(3)
                st.dataframe(frame, hide_index=True, use_container_width=True)
            else:
                st.caption("Aucune trajectoire retenue.")
    st.caption(f"Masse de probabilité retenue avant normalisation : {retained*100:.5f}%. La troncature des buts est corrigée par renormalisation.")
    st.markdown("**Rappel méthodologique :** ce moteur suppose des buts indépendants entre équipes et périodes. Il ne modélise pas encore les dépendances (carton rouge, score qui change la tactique, corrélation), ni la qualité des données ou la calibration historique. Le modèle ne doit pas être considéré comme validé avant un backtest sur des matchs non utilisés pour le réglage.")
else:
    st.info("Renseigne les quatre lambdas, puis lance le calcul pour afficher le classement. Les valeurs par défaut sont fictives et servent à tester l'outil.")

st.divider()
st.caption("RODRIGUE PRO MT/FT ELITE • Outil d'analyse statistique, pas un conseil de pari ni une garantie de rendement.")
