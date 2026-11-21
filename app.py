
import math
import streamlit as st
import pandas as pd


# =========================================
# RODRIGUE PRO — CALCUL DES 9 MT/FT
# =========================================

def poisson(k, lam):
    """Probabilité de k buts avec un taux attendu lambda."""
    if lam < 0:
        return 0.0
    if lam == 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def signe(score_home, score_away):
    if score_home > score_away:
        return "1"
    elif score_home == score_away:
        return "X"
    return "2"


def calcul_mt_ft(
    lambda_home_mt,
    lambda_away_mt,
    lambda_home_2h,
    lambda_away_2h,
    max_goals=8
):
    """
    Calcule les probabilités des 9 combinaisons MT/FT.

    Les lambdas sont les buts attendus (xG modélisés)
    pour chaque équipe et chaque période.
    """

    combinaisons = [
        "1/1", "X/1", "2/1",
        "1/X", "X/X", "2/X",
        "1/2", "X/2", "2/2"
    ]

    probabilites = {c: 0.0 for c in combinaisons}
    scores_possibles = {c: [] for c in combinaisons}

    # Scores de la première mi-temps
    for h_mt in range(max_goals + 1):
        for a_mt in range(max_goals + 1):

            p_mt = (
                poisson(h_mt, lambda_home_mt)
                * poisson(a_mt, lambda_away_mt)
            )

            resultat_mt = signe(h_mt, a_mt)

            # Scores de la deuxième mi-temps
            for h_2h in range(max_goals + 1):
                for a_2h in range(max_goals + 1):

                    p_2h = (
                        poisson(h_2h, lambda_home_2h)
                        * poisson(a_2h, lambda_away_2h)
                    )

                    # Score final
                    h_ft = h_mt + h_2h
                    a_ft = a_mt + a_2h

                    resultat_ft = signe(h_ft, a_ft)

                    combo = f"{resultat_mt}/{resultat_ft}"
                    p_total = p_mt * p_2h

                    probabilites[combo] += p_total

                    if p_total >= 0.0005:
                        scores_possibles[combo].append({
                            "MT": f"{h_mt}-{a_mt}",
                            "FT": f"{h_ft}-{a_ft}",
                            "Probabilité": p_total
                        })

    # Normalisation pour corriger la très petite masse
    # de probabilité omise au-delà de max_goals
    total = sum(probabilites.values())

    if total > 0:
        for combo in probabilites:
            probabilites[combo] /= total

        for combo in scores_possibles:
            for item in scores_possibles[combo]:
                item["Probabilité"] /= total

    return probabilites, scores_possibles


# =========================================
# AFFICHAGE STREAMLIT
# =========================================

st.subheader("⚽ RODRIGUE PRO — MT/FT POISSON")

st.caption(
    "Modèle probabiliste basé sur les buts attendus "
    "en première et deuxième mi-temps."
)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏠 Domicile")
    home_mt = st.number_input(
        "Buts attendus — 1re MT",
        min_value=0.0, max_value=5.0,
        value=0.75, step=0.05
    )
    home_2h = st.number_input(
        "Buts attendus — 2e MT",
        min_value=0.0, max_value=5.0,
        value=0.85, step=0.05
    )

with col2:
    st.markdown("### ✈️ Extérieur")
    away_mt = st.number_input(
        "Buts attendus — 1re MT",
        min_value=0.0, max_value=5.0,
        value=0.35, step=0.05
    )
    away_2h = st.number_input(
        "Buts attendus — 2e MT",
        min_value=0.0, max_value=5.0,
        value=0.55, step=0.05
    )

if st.button("🔎 CALCULER LES 9 MT/FT", use_container_width=True):

    probs, scores = calcul_mt_ft(
        home_mt,
        away_mt,
        home_2h,
        away_2h
    )

    classement = sorted(
        probs.items(),
        key=lambda x: x[1],
        reverse=True
    )

    st.markdown("## 📊 Classement des 9 combinaisons")

    df = pd.DataFrame([
        {
            "Rang": i + 1,
            "MT/FT": combo,
            "Probabilité (%)": round(prob * 100, 2)
        }
        for i, (combo, prob) in enumerate(classement)
    ])

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.bar_chart(
        df.set_index("MT/FT")["Probabilité (%)"]
    )

    meilleure = classement[0]

    st.success(
        f"Scénario le plus probable : {meilleure[0]} "
        f"({meilleure[1] * 100:.2f} %)"
    )

    st.markdown("## 🎯 Scores associés aux scénarios")

    for combo, prob in classement:

        with st.expander(
            f"{combo} — {prob * 100:.2f} %"
        ):
            liste = sorted(
                scores[combo],
                key=lambda x: x["Probabilité"],
                reverse=True
            )

            if liste:
                df_scores = pd.DataFrame(liste[:10])
                df_scores["Probabilité (%)"] = (
                    df_scores["Probabilité"] * 100
                ).round(2)

                st.dataframe(
                    df_scores[
                        ["MT", "FT", "Probabilité (%)"]
                    ],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.write("Pas de score significatif affiché.")

    st.info(
        "Les probabilités sont des estimations mathématiques, "
        "pas des garanties. Vérifie la qualité des lambdas, "
        "les absences, la forme, et les données du match."
    )
