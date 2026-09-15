# -*- coding: utf-8 -*-
"""
RODRIGUE APPLE AI — Analyseur statistique Apple of Fortune
------------------------------------------------------------
Interface Streamlit pour :
- charger une capture d'écran ;
- détecter une grille 5 colonnes ;
- enregistrer les résultats observés ;
- calculer des probabilités empiriques par colonne ;
- mesurer la précision réelle du modèle ;
- produire un score de confiance et un mode "NE PAS JOUER"
- gérer une mise et une limite de perte.

IMPORTANT :
Ce programme ne peut pas prédire avec certitude un tirage aléatoire côté serveur.
Le "90 %" n'est jamais forcé : l'application affiche la précision réellement
mesurée sur les données enregistrées.
"""

import io
import json
import math
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

# OpenCV est optionnel : l'application continue à fonctionner sans lui.
try:
    import cv2
    CV2_OK = True
except Exception:
    CV2_OK = False


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "RODRIGUE APPLE AI"
N_COLS = 5
DATA_FILE = Path("apple_ai_history.json")

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🍎",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 0;
    }
    .sub-title {
        opacity: .75;
        margin-top: 0;
    }
    .box {
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,.25);
        margin-bottom: 12px;
    }
    .safe {
        padding: 16px;
        border-radius: 12px;
        background: rgba(50,180,80,.15);
        border: 1px solid rgba(50,180,80,.45);
    }
    .danger {
        padding: 16px;
        border-radius: 12px;
        background: rgba(220,50,50,.15);
        border: 1px solid rgba(220,50,50,.45);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(f'<div class="main-title">🍎 {APP_NAME}</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Analyse statistique • Vision de grille • Validation réelle</div>',
    unsafe_allow_html=True,
)

st.warning(
    "Aucune IA ne peut garantir 90 % sur un jeu dont le résultat est généré "
    "aléatoirement côté serveur. Ce programme mesure la performance réelle du "
    "modèle et refuse de donner une fausse confiance."
)


# ============================================================
# STOCKAGE
# ============================================================

def load_history():
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history(history):
    DATA_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if "history" not in st.session_state:
    st.session_state.history = load_history()


# ============================================================
# OUTILS STATISTIQUES
# ============================================================

def wilson_lower_bound(successes, trials, z=1.96):
    """Borne basse Wilson à 95 %, utile pour éviter une confiance artificielle."""
    if trials <= 0:
        return 0.0

    p = successes / trials
    denominator = 1 + z**2 / trials
    center = p + z**2 / (2 * trials)
    margin = z * math.sqrt((p * (1 - p) / trials) + z**2 / (4 * trials**2))
    return max(0.0, (center - margin) / denominator)


def empirical_column_stats(history):
    """
    Chaque observation doit contenir:
      safe_col = colonne effectivement sûre (1..5)
    """
    rows = []
    for col in range(1, N_COLS + 1):
        obs = [x for x in history if x.get("safe_col") in range(1, N_COLS + 1)]
        trials = len(obs)
        successes = sum(1 for x in obs if x.get("safe_col") == col)

        # Probabilité empirique + lissage de Laplace.
        p = (successes + 1) / (trials + N_COLS)
        lower = wilson_lower_bound(successes, trials)

        rows.append(
            {
                "Colonne": col,
                "Observations": trials,
                "Succès": successes,
                "Fréquence observée": p,
                "Borne Wilson 95%": lower,
            }
        )

    return pd.DataFrame(rows)


def recent_weights(history, decay=0.92):
    """Poids exponentiels : observations récentes légèrement prioritaires."""
    valid = [x for x in history if x.get("safe_col") in range(1, N_COLS + 1)]
    weights = []

    for i, item in enumerate(valid):
        age = len(valid) - 1 - i
        weights.append(decay ** age)

    return valid, np.array(weights, dtype=float)


def weighted_probabilities(history):
    valid, weights = recent_weights(history)

    if not valid:
        return np.ones(N_COLS) / N_COLS

    scores = np.ones(N_COLS)  # Laplace smoothing
    for item, w in zip(valid, weights):
        scores[int(item["safe_col"]) - 1] += w

    return scores / scores.sum()


def bootstrap_accuracy(history, simulations=1000):
    """
    Estime l'incertitude de la précision observée par bootstrap.
    """
    valid = [x for x in history if x.get("prediction_col") in range(1, N_COLS + 1)
             and x.get("safe_col") in range(1, N_COLS + 1)]

    if len(valid) < 5:
        return None

    correct = np.array(
        [int(x["prediction_col"] == x["safe_col"]) for x in valid],
        dtype=float,
    )

    rng = np.random.default_rng(42)
    samples = []

    for _ in range(simulations):
        sample = rng.choice(correct, size=len(correct), replace=True)
        samples.append(sample.mean())

    return {
        "accuracy": float(correct.mean()),
        "low": float(np.percentile(samples, 2.5)),
        "high": float(np.percentile(samples, 97.5)),
        "n": len(correct),
    }


def model_confidence(history, selected_col):
    """
    Score de confiance volontairement conservateur.
    Il combine :
      - fréquence récente ;
      - historique global ;
      - quantité d'observations ;
      - borne Wilson.
    """
    valid = [
        x for x in history
        if x.get("safe_col") in range(1, N_COLS + 1)
    ]

    if len(valid) < 10:
        return {
            "confidence": 20.0,
            "probability": 20.0,
            "status": "DONNÉES INSUFFISANTES",
            "reason": "Il faut davantage de parties observées.",
        }

    probs = weighted_probabilities(history)
    p = float(probs[selected_col - 1])

    trials = len(valid)
    successes = sum(
        1 for x in valid if x.get("safe_col") == selected_col
    )
    lower = wilson_lower_bound(successes, trials)

    # Score prudent : on pénalise les petits échantillons.
    sample_factor = min(1.0, trials / 100.0)
    confidence = 100.0 * (
        0.55 * lower +
        0.25 * p +
        0.20 * sample_factor
    )

    confidence = max(0.0, min(99.0, confidence))

    if confidence >= 70:
        status = "SIGNAL STATISTIQUE FORT"
    elif confidence >= 55:
        status = "SIGNAL MOYEN"
    else:
        status = "NE PAS JOUER"

    return {
        "confidence": confidence,
        "probability": p * 100,
        "status": status,
        "reason": f"{trials} observations analysées ; borne Wilson = {lower*100:.1f} %.",
    }


# ============================================================
# VISION DE LA CAPTURE
# ============================================================

def detect_grid(image):
    """
    Détection indicative d'une grille de 5 colonnes.
    Elle ne prétend pas reconnaître quelle pomme est gagnante.
    Retourne des centres approximatifs des cercles détectés.
    """
    if not CV2_OK:
        return None, "OpenCV n'est pas installé."

    arr = np.array(image.convert("RGB"))
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 7)

    h, w = gray.shape[:2]

    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(30, int(w * 0.08)),
        param1=100,
        param2=35,
        minRadius=max(15, int(min(h, w) * 0.025)),
        maxRadius=max(30, int(min(h, w) * 0.10)),
    )

    if circles is None:
        return None, "Aucun cercle suffisamment net détecté."

    circles = np.round(circles[0]).astype(int)

    # Garder les cercles dans la zone centrale où se trouve généralement la grille.
    filtered = []
    for x, y, r in circles:
        if 0.10*w < x < 0.95*w and 0.08*h < y < 0.90*h:
            filtered.append((int(x), int(y), int(r)))

    if len(filtered) < 5:
        return filtered, f"{len(filtered)} éléments détectés ; grille incomplète."

    # Regroupement approximatif en 5 colonnes par position X.
    filtered = sorted(filtered, key=lambda p: p[1])

    return filtered, f"{len(filtered)} cercles détectés. Vérification visuelle recommandée."


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Paramètres")

    min_conf = st.slider(
        "Confiance minimale pour un signal",
        min_value=50,
        max_value=90,
        value=70,
        step=5,
    )

    bankroll = st.number_input(
        "Solde disponible (F CFA)",
        min_value=0.0,
        value=10000.0,
        step=500.0,
    )

    mise = st.number_input(
        "Mise envisagée (F CFA)",
        min_value=0.0,
        value=200.0,
        step=50.0,
    )

    max_loss = st.slider(
        "Perte maximale relative autorisée",
        1,
        20,
        5,
        help="Protection de gestion de bankroll ; ne prédit pas le résultat.",
    )

    st.caption(
        "Le seuil ne transforme pas un jeu aléatoire en jeu prévisible."
    )


# ============================================================
# ONGLETS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs(
    ["📸 Capture", "🧠 Analyse", "📊 Historique", "🧪 Validation"]
)


# ============================================================
# TAB 1 — CAPTURE
# ============================================================

with tab1:
    st.subheader("📸 Charger la capture Apple of Fortune")

    uploaded = st.file_uploader(
        "Sélectionne une capture d'écran",
        type=["png", "jpg", "jpeg", "webp"],
    )

    if uploaded:
        image = Image.open(uploaded).convert("RGB")
        st.image(image, caption="Capture chargée", use_container_width=True)

        if st.button("🔎 Détecter la grille", use_container_width=True):
            detections, message = detect_grid(image)

            if detections is None:
                st.error(message)
            else:
                st.info(message)

                if len(detections) > 0:
                    df_det = pd.DataFrame(
                        detections,
                        columns=["X", "Y", "Rayon"]
                    )
                    st.dataframe(df_det, use_container_width=True)

                    st.caption(
                        "La détection localise les éléments graphiques. "
                        "Elle ne peut pas déterminer mathématiquement la future case gagnante."
                    )

    st.divider()

    st.subheader("➕ Enregistrer un résultat réellement observé")

    c1, c2, c3 = st.columns(3)

    with c1:
        safe_col = st.selectbox(
            "Colonne réellement sûre",
            list(range(1, N_COLS + 1)),
            index=0,
        )

    with c2:
        prediction_col = st.selectbox(
            "Colonne prédite avant le résultat",
            list(range(1, N_COLS + 1)),
            index=0,
        )

    with c3:
        niveau = st.selectbox(
            "Niveau du signal",
            ["faible", "moyen", "fort"],
            index=1,
        )

    if st.button("💾 Enregistrer cette observation", use_container_width=True):
        st.session_state.history.append(
            {
                "date": datetime.now().isoformat(timespec="seconds"),
                "safe_col": int(safe_col),
                "prediction_col": int(prediction_col),
                "signal": niveau,
            }
        )
        save_history(st.session_state.history)
        st.success("Observation enregistrée.")


# ============================================================
# TAB 2 — ANALYSE
# ============================================================

with tab2:
    st.subheader("🧠 Analyse statistique")

    history = st.session_state.history
    stats = empirical_column_stats(history)

    if len(history) == 0:
        st.info(
            "Aucune observation. Commence par enregistrer les résultats "
            "réellement observés."
        )
    else:
        probs = weighted_probabilities(history)

        table = stats.copy()
        table["Probabilité récente pondérée"] = probs

        st.dataframe(
            table.style.format(
                {
                    "Fréquence observée": "{:.1%}",
                    "Borne Wilson 95%": "{:.1%}",
                    "Probabilité récente pondérée": "{:.1%}",
                }
            ),
            use_container_width=True,
        )

        selected = int(
            np.argmax(probs) + 1
        )

        result = model_confidence(history, selected)

        st.markdown(
            f"""
            <div class="box">
            <h3>🎯 Colonne statistiquement prioritaire : {selected}</h3>
            <p>Probabilité empirique pondérée : <b>{result["probability"]:.1f}%</b></p>
            <p>Score de confiance prudent : <b>{result["confidence"]:.1f}%</b></p>
            <p>{result["reason"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if result["confidence"] >= min_conf:
            st.markdown(
                f'<div class="safe">🟢 <b>{result["status"]}</b><br>'
                f'Le modèle dépasse ton seuil de {min_conf}%.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="danger">🔴 <b>NE PAS JOUER</b><br>'
                f'Le signal ({result["confidence"]:.1f}%) est inférieur au seuil '
                f'de {min_conf}%.</div>',
                unsafe_allow_html=True,
            )

        # Gestion de bankroll.
        risk = 0 if bankroll <= 0 else 100 * mise / bankroll

        st.write("")
        st.subheader("💰 Gestion de la mise")
        st.metric("Mise / bankroll", f"{risk:.1f}%")

        if risk > max_loss:
            st.error(
                f"Mise trop élevée selon ton plafond de {max_loss}% de bankroll."
            )
        else:
            st.success("Mise dans la limite configurée.")

        st.caption(
            "Cette section gère le risque financier ; elle n'améliore pas "
            "la probabilité mathématique d'une case aléatoire."
        )


# ============================================================
# TAB 3 — HISTORIQUE
# ============================================================

with tab3:
    st.subheader("📊 Historique des observations")

    history = st.session_state.history

    if not history:
        st.info("Historique vide.")
    else:
        df = pd.DataFrame(history)
        st.dataframe(df, use_container_width=True)

        if st.button("🗑️ Effacer tout l'historique"):
            st.session_state.history = []
            save_history([])
            st.rerun()

        st.download_button(
            "⬇️ Exporter CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="apple_ai_history.csv",
            mime="text/csv",
        )


# ============================================================
# TAB 4 — VALIDATION
# ============================================================

with tab4:
    st.subheader("🧪 La précision réelle du modèle")

    validation = bootstrap_accuracy(st.session_state.history)

    if validation is None:
        st.info(
            "Il faut au moins 5 observations avec une colonne prédite et "
            "une colonne réellement sûre pour calculer la précision."
        )
    else:
        acc = validation["accuracy"] * 100
        low = validation["low"] * 100
        high = validation["high"] * 100

        a, b, c = st.columns(3)

        with a:
            st.metric("Précision observée", f"{acc:.1f}%")
        with b:
            st.metric("Intervalle bootstrap bas", f"{low:.1f}%")
        with c:
            st.metric("Intervalle bootstrap haut", f"{high:.1f}%")

        if acc >= 90:
            st.success(
                "La précision observée est ≥ 90 % sur cet historique. "
                "Cela ne constitue toutefois pas une garantie pour les prochaines parties."
            )
        else:
            st.warning(
                f"La précision observée est de {acc:.1f} %. "
                "Le modèle ne démontre donc pas actuellement une précision de 90 %."
            )

        st.caption(
            f"Échantillon : {validation['n']} prédictions validées. "
            "L'intervalle bootstrap montre l'incertitude autour de cette mesure."
        )

    st.divider()

    st.subheader("📌 Règle anti-fausse-confiance")

    st.write(
        """
        Le programme ne fait jamais ceci :

        **« 90 % de confiance » uniquement parce qu'une case semble plus favorable.**

        Il exige des observations et compare ensuite les prédictions aux résultats
        réellement obtenus. Si les données ne prouvent pas la performance, le
        système affiche **NE PAS JOUER**.
        """
    )


# ============================================================
# PIED DE PAGE
# ============================================================

st.divider()
st.caption(
    "RODRIGUE APPLE AI — outil statistique expérimental. "
    "Les résultats passés ne garantissent pas les résultats futurs."
)
