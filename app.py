# -*- coding: utf-8 -*-
"""
RODRIGUE APPLE AI V4 — Analyseur Apple of Fortune
==================================================
Version mobile Streamlit, sans OpenCV obligatoire.

Fonctions :
- import d'une capture ;
- détection automatique d'une grille 5 colonnes ;
- tableau C1..C5 avec score et risque ;
- historique d'observations ;
- apprentissage statistique à partir des résultats réellement observés ;
- validation hors-échantillon simple ;
- gestion de bankroll ;
- bouton "NE PAS JOUER" si le modèle n'a pas de preuve suffisante.

IMPORTANT :
Une capture d'écran ne révèle pas le prochain résultat caché.
Le programme n'invente donc pas une probabilité de 90 %.
"""

from pathlib import Path
from datetime import datetime
import json
import math

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

APP_VERSION = "V4"
N_COLS = 5
DATA_FILE = Path("apple_ai_history.json")

st.set_page_config(
    page_title="RODRIGUE APPLE AI V4",
    page_icon="🍎",
    layout="wide",
)

# ------------------------- STYLE -------------------------

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
.title {font-size:32px;font-weight:800;}
.subtitle {font-size:16px;opacity:.75;}
.card {padding:14px;border-radius:14px;border:1px solid rgba(128,128,128,.25);margin:8px 0;}
.good {padding:15px;border-radius:14px;background:rgba(40,170,70,.14);border:1px solid rgba(40,170,70,.35);}
.bad {padding:15px;border-radius:14px;background:rgba(220,60,60,.14);border:1px solid rgba(220,60,60,.35);}
.warn {padding:15px;border-radius:14px;background:rgba(220,170,40,.14);border:1px solid rgba(220,170,40,.35);}
.colbox {text-align:center;padding:12px;border-radius:12px;border:1px solid rgba(128,128,128,.25);}
.small {font-size:12px;opacity:.7;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🍎 RODRIGUE APPLE AI V4</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Vision de grille • Score statistique • Validation réelle</div>',
    unsafe_allow_html=True
)

st.warning(
    "Le système analyse l'écran et les données historiques. Il ne peut pas "
    "connaître une case cachée générée aléatoirement par le serveur. "
    "Le seuil de 90 % n'est jamais simulé."
)

# ------------------------- HISTORIQUE -------------------------

def load_history():
    try:
        if DATA_FILE.exists():
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []

def save_history(history):
    DATA_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

if "history" not in st.session_state:
    st.session_state.history = load_history()

# ------------------------- STATISTIQUES -------------------------

def valid_history():
    return [
        x for x in st.session_state.history
        if int(x.get("safe_col", 0)) in range(1, N_COLS + 1)
    ]

def weighted_scores():
    h = valid_history()
    scores = np.ones(N_COLS, dtype=float)  # lissage Laplace

    # Les observations récentes ont légèrement plus de poids.
    for i, item in enumerate(h):
        age = len(h) - 1 - i
        weight = 0.94 ** age
        scores[int(item["safe_col"]) - 1] += weight

    return scores / scores.sum()

def wilson_lower(successes, trials, z=1.96):
    if trials <= 0:
        return 0.0
    p = successes / trials
    den = 1 + z*z/trials
    center = p + z*z/(2*trials)
    margin = z * math.sqrt(p*(1-p)/trials + z*z/(4*trials*trials))
    return max(0.0, (center - margin) / den)

def prediction_accuracy():
    rows = [
        x for x in st.session_state.history
        if int(x.get("prediction_col", 0)) in range(1, N_COLS+1)
        and int(x.get("safe_col", 0)) in range(1, N_COLS+1)
    ]
    if not rows:
        return None
    return sum(
        int(x["prediction_col"]) == int(x["safe_col"])
        for x in rows
    ) / len(rows)

def confidence_for_column(col):
    h = valid_history()
    n = len(h)

    if n < 20:
        return 0.0, "INSUFFISANT"

    successes = sum(int(x["safe_col"]) == col for x in h)
    lower = wilson_lower(successes, n)
    p = weighted_scores()[col - 1]

    # Confiance prudente : la borne statistique domine le score.
    sample_factor = min(1.0, n / 150.0)
    confidence = 100 * (0.70 * lower + 0.20 * p + 0.10 * sample_factor)

    if confidence >= 70:
        level = "FORT"
    elif confidence >= 55:
        level = "MOYEN"
    else:
        level = "FAIBLE"

    return float(min(confidence, 99.0)), level

# ------------------------- DÉTECTION IMAGE -------------------------

def detect_grid(image):
    """
    Détection géométrique robuste pour l'interface Apple of Fortune.
    Elle localise les 5 colonnes sans prétendre lire une pomme cachée.
    """
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    h, w, _ = arr.shape

    # Sur ce type d'écran, la grille occupe approximativement le centre.
    # On évite les boutons et la barre de mise.
    y_top = int(h * 0.12)
    y_bottom = int(h * 0.82)

    # Recherche des variations verticales dans la zone de grille.
    roi = arr[y_top:y_bottom]
    intensity = roi.mean(axis=2)

    # Profils X/Y + lissage.
    px = intensity.mean(axis=0)
    py = intensity.mean(axis=1)

    kx = max(7, int(w * 0.015))
    ky = max(7, int(h * 0.015))

    sx = np.convolve(px, np.ones(kx)/kx, mode="same")
    sy = np.convolve(py, np.ones(ky)/ky, mode="same")

    # Pour 5 colonnes, on privilégie les positions régulières.
    # Elles sont ensuite ajustées très légèrement au profil de luminosité.
    left = int(w * 0.24)
    right = int(w * 0.91)
    base_x = np.linspace(left, right, N_COLS)

    xs = []
    search = max(10, int(w * 0.045))
    for bx in base_x:
        a = max(0, int(bx)-search)
        b = min(w, int(bx)+search+1)
        local = sx[a:b]
        if len(local):
            # centre de gravité des variations.
            weights = np.maximum(local - local.min(), 0.001)
            pos = np.arange(a, b)
            x = int(np.sum(pos * weights) / np.sum(weights))
        else:
            x = int(bx)
        xs.append(x)

    # Lignes : les objets sont généralement espacés régulièrement.
    top = int(h * 0.18)
    bottom = int(h * 0.78)
    n_rows = 8
    base_y = np.linspace(top, bottom, n_rows)

    ys = []
    for by in base_y:
        a = max(0, int(by)-search)
        b = min(h, int(by)+search+1)
        local = sy[max(0, a-y_top):max(0, b-y_top)]
        if len(local):
            weights = np.maximum(local - local.min(), 0.001)
            pos = np.arange(a, b)[:len(local)]
            y = int(np.sum(pos * weights) / np.sum(weights))
        else:
            y = int(by)
        ys.append(y)

    radius = max(18, int(min(h, w) * 0.043))

    points = [(int(x), int(y), radius) for y in ys for x in xs]

    return {
        "width": w,
        "height": h,
        "columns": xs,
        "rows": ys,
        "points": points,
    }

def draw_grid_overlay(image, grid, chosen_col=None):
    out = image.copy().convert("RGB")
    draw = ImageDraw.Draw(out)

    xs = grid["columns"]
    ys = grid["rows"]
    r = max(15, int(min(out.size) * 0.043))

    for ci, x in enumerate(xs, start=1):
        for ri, y in enumerate(ys, start=1):
            box = (x-r, y-r, x+r, y+r)
            # Marquage sobre : on utilise le même tracé pour toutes les cases.
            draw.ellipse(box, outline="white", width=3)
            draw.text((x-7, y-8), str(ci), fill="white")

    if chosen_col in range(1, N_COLS+1):
        x = xs[chosen_col-1]
        for y in ys:
            draw.ellipse(
                (x-r-5, y-r-5, x+r+5, y+r+5),
                outline="lime",
                width=5
            )

    return out

# ------------------------- SCORE VISUEL / STATISTIQUE -------------------------

def make_analysis():
    h = valid_history()
    probs = weighted_scores()
    rows = []

    for col in range(1, N_COLS+1):
        conf, level = confidence_for_column(col)
        observed = sum(int(x["safe_col"]) == col for x in h)
        rows.append({
            "Colonne": f"C{col}",
            "Observations": len(h),
            "Succès observés": observed,
            "Score historique": round(probs[col-1]*100, 1),
            "Confiance prudente": round(conf, 1),
            "Niveau": level,
        })

    df = pd.DataFrame(rows)
    return df, probs

# ------------------------- SIDEBAR -------------------------

with st.sidebar:
    st.header("⚙️ Réglages")

    threshold = st.slider(
        "Seuil de confiance",
        50, 90, 70, 5
    )

    bankroll = st.number_input(
        "Bankroll (F CFA)",
        min_value=0.0,
        value=10000.0,
        step=500.0
    )

    stake = st.number_input(
        "Mise (F CFA)",
        min_value=0.0,
        value=200.0,
        step=50.0
    )

    st.caption(
        "Le seuil contrôle uniquement l'affichage du signal. "
        "Il ne modifie pas les probabilités mathématiques."
    )

# ------------------------- ONGLETS -------------------------

tab_capture, tab_analysis, tab_history, tab_validation = st.tabs(
    ["📸 Capture", "🧠 Analyse", "📊 Historique", "🧪 Validation"]
)

# ========================= CAPTURE =========================

with tab_capture:
    st.subheader("📸 Charger la capture Apple of Fortune")

    uploaded = st.file_uploader(
        "Sélectionne une capture d'écran",
        type=["png", "jpg", "jpeg", "webp"],
        key="capture_upload"
    )

    if uploaded:
        image = Image.open(uploaded).convert("RGB")
        st.image(image, use_container_width=True)

        if st.button("🔎 ANALYSER AUTOMATIQUEMENT", use_container_width=True):
            try:
                grid = detect_grid(image)
                st.session_state.grid = grid

                df, probs = make_analysis()
                chosen = int(np.argmax(probs)) + 1
                st.session_state.chosen_col = chosen

                overlay = draw_grid_overlay(image, grid, chosen)
                st.session_state.overlay = overlay

                st.success("Grille détectée. Analyse statistique terminée.")
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")

    if "overlay" in st.session_state:
        st.subheader("🗺️ Grille détectée")
        st.image(
            st.session_state.overlay,
            caption="Repères de grille — ils ne révèlent pas les cases cachées.",
            use_container_width=True
        )

        df, probs = make_analysis()
        chosen = int(np.argmax(probs)) + 1
        st.session_state.chosen_col = chosen

        # ---------- RESULTAT PRINCIPAL ----------
        n = len(valid_history())

        if n < 20:
            st.markdown(
                '<div class="bad"><b>🛑 NE PAS JOUER</b><br>'
                f'Données insuffisantes : {n}/20 observations minimum.</div>',
                unsafe_allow_html=True
            )
        else:
            conf, level = confidence_for_column(chosen)

            if conf >= threshold:
                st.markdown(
                    f'<div class="good"><b>🎯 COLONNE PRIORITAIRE : C{chosen}</b><br>'
                    f'Confiance statistique prudente : <b>{conf:.1f}%</b><br>'
                    f'Niveau : <b>{level}</b></div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="bad"><b>🛑 NE PAS JOUER</b><br>'
                    f'C{chosen} : {conf:.1f}% de confiance, sous ton seuil de '
                    f'{threshold}%.</div>',
                    unsafe_allow_html=True
                )

        st.subheader("📊 Les 5 colonnes")
        cols = st.columns(5)

        for i, c in enumerate(cols, start=1):
            conf, level = confidence_for_column(i)
            score = probs[i-1] * 100

            if n < 20:
                shown_conf = "—"
                level = "INSUFFISANT"
            else:
                shown_conf = f"{conf:.1f}%"

            with c:
                st.markdown(
                    f'<div class="colbox"><b>C{i}</b><br>'
                    f'Score : <b>{score:.1f}%</b><br>'
                    f'Confiance : <b>{shown_conf}</b><br>'
                    f'<span class="small">{level}</span></div>',
                    unsafe_allow_html=True
                )

        # ---------- ENREGISTREMENT RAPIDE ----------
        st.divider()
        st.subheader("➕ Résultat réellement observé")

        st.caption(
            "Après avoir joué et vu le résultat, touche uniquement la colonne "
            "qui était réellement sûre. Cela permet au modèle de mesurer ses "
            "performances au lieu d'inventer une réussite."
        )

        actual = st.radio(
            "Quelle colonne était réellement sûre ?",
            [1, 2, 3, 4, 5],
            horizontal=True,
            key="actual_col"
        )

        if st.button("💾 ENREGISTRER + APPRENDRE", use_container_width=True):
            predicted = int(st.session_state.get("chosen_col", 1))
            st.session_state.history.append({
                "date": datetime.now().isoformat(timespec="seconds"),
                "safe_col": int(actual),
                "prediction_col": predicted,
            })
            save_history(st.session_state.history)
            st.success(
                f"Résultat enregistré : C{actual}. "
                f"Prédiction du modèle : C{predicted}."
            )
            st.rerun()

# ========================= ANALYSE =========================

with tab_analysis:
    st.subheader("🧠 Analyse statistique")

    df, probs = make_analysis()
    n = len(valid_history())

    st.dataframe(df, use_container_width=True)

    best = int(np.argmax(probs)) + 1
    conf, level = confidence_for_column(best)

    if n < 20:
        st.info(
            f"Le modèle dispose de {n} observation(s). "
            "Il faut au minimum 20 observations pour commencer à afficher "
            "une confiance statistique."
        )
        st.markdown(
            '<div class="bad"><b>🛑 NE PAS JOUER</b><br>'
            'Pas assez de données validées.</div>',
            unsafe_allow_html=True
        )
    elif conf >= threshold:
        st.markdown(
            f'<div class="good"><b>🎯 PRIORITÉ : C{best}</b><br>'
            f'Confiance : <b>{conf:.1f}%</b> — {level}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="bad"><b>🛑 NE PAS JOUER</b><br>'
            f'Meilleure colonne C{best} : {conf:.1f}% seulement.</div>',
            unsafe_allow_html=True
        )

    st.caption(
        "Un score statistique supérieur aux autres colonnes ne signifie pas "
        "que la prochaine case est connue à l'avance."
    )

# ========================= HISTORIQUE =========================

with tab_history:
    st.subheader("📊 Historique")

    if not st.session_state.history:
        st.info("Aucune observation enregistrée.")
    else:
        hist_df = pd.DataFrame(st.session_state.history)
        st.dataframe(hist_df, use_container_width=True)

        csv = hist_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Exporter CSV",
            csv,
            "apple_ai_history.csv",
            "text/csv"
        )

        if st.button("🗑️ Effacer l'historique"):
            st.session_state.history = []
            save_history([])
            st.rerun()

# ========================= VALIDATION =========================

with tab_validation:
    st.subheader("🧪 Validation réelle")

    acc = prediction_accuracy()

    if acc is None:
        st.info("Aucune prédiction validée pour le moment.")
    else:
        n = len([
            x for x in st.session_state.history
            if int(x.get("prediction_col", 0)) in range(1, 6)
            and int(x.get("safe_col", 0)) in range(1, 6)
        ])

        st.metric("Précision observée", f"{acc*100:.1f}%")
        st.metric("Prédictions validées", n)

        if acc >= 0.90:
            st.success(
                "La précision observée atteint au moins 90 % sur cet historique. "
                "Cela ne garantit pas les prochaines parties."
            )
        else:
            st.warning(
                "Le modèle n'atteint pas encore 90 % sur les données disponibles."
            )

    st.divider()

    risk = 0 if bankroll <= 0 else 100 * stake / bankroll
    st.metric("Mise / bankroll", f"{risk:.1f}%")

    if risk > 5:
        st.error("⚠️ La mise dépasse 5 % de la bankroll.")
    else:
        st.success("Gestion de mise : dans la limite de 5 %.")

# ------------------------- FOOTER -------------------------

st.divider()
st.caption(
    "RODRIGUE APPLE AI V4 • La performance affichée est calculée à partir "
    "des résultats réellement enregistrés."
)
