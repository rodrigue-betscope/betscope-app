# -*- coding: utf-8 -*-
"""
RODRIGUE APPLE AI V5
Gestion d'état du pari + analyse statistique.

IMPORTANT :
- L'application d'analyse ne contrôle PAS le serveur du jeu.
- Elle ne peut donc pas confirmer qu'un vrai pari SportyBet/serveur
  a été accepté uniquement à partir d'une capture.
- Le bouton "MISE" ci-dessous sert à enregistrer localement l'état
  de la session d'analyse.
- Une fois la mise enregistrée, la sélection de la pomme est autorisée.
- Le retrait/remboursement d'une vraie mise doit être effectué dans
  l'application du bookmaker/jeu selon ses règles.
"""

from pathlib import Path
from datetime import datetime
import json
import math

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

APP_VERSION = "V5"
N_COLS = 5
DATA_FILE = Path("apple_ai_history.json")

st.set_page_config(
    page_title="RODRIGUE APPLE AI V5",
    page_icon="🍎",
    layout="wide"
)

# ============================================================
# STYLE
# ============================================================

st.markdown("""
<style>
.block-container {padding-top:1rem;padding-bottom:2rem;}
.title {font-size:31px;font-weight:800;}
.subtitle {font-size:16px;opacity:.75;}
.state {padding:16px;border-radius:14px;margin:10px 0;
        border:1px solid rgba(128,128,128,.3);}
.good {background:rgba(40,180,80,.14);border-color:rgba(40,180,80,.4);}
.bad {background:rgba(220,60,60,.14);border-color:rgba(220,60,60,.4);}
.warn {background:rgba(230,180,40,.14);border-color:rgba(230,180,40,.4);}
.neutral {background:rgba(70,130,200,.14);}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="title">🍎 RODRIGUE APPLE AI V5</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="subtitle">État du pari • Vision de grille • Analyse • Validation</div>',
    unsafe_allow_html=True
)

st.warning(
    "Le programme distingue maintenant 3 états : AVANT MISE → PARI ACTIF → "
    "POMME CHOISIE. Il ne peut pas lire directement l'état réel du serveur "
    "d'un bookmaker à partir d'une capture."
)

# ============================================================
# SESSION
# ============================================================

defaults = {
    "bet_active": False,
    "bet_amount": 0.0,
    "bet_started_at": None,
    "selected_col": None,
    "round_finished": False,
    "grid": None,
    "overlay": None,
    "history": [],
    "prediction_col": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# HISTORIQUE
# ============================================================

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

if not st.session_state.history:
    st.session_state.history = load_history()

def valid_history():
    return [
        x for x in st.session_state.history
        if int(x.get("safe_col", 0)) in range(1, N_COLS + 1)
    ]

# ============================================================
# ÉTAT DU JEU
# ============================================================

def game_state():
    if st.session_state.round_finished:
        return "TERMINE"
    if st.session_state.selected_col is not None:
        return "POMME CHOISIE"
    if st.session_state.bet_active:
        return "PARI ACTIF"
    return "AVANT MISE"

def state_box():
    state = game_state()

    if state == "AVANT MISE":
        st.markdown(
            '<div class="state bad"><b>🔴 AVANT MISE</b><br>'
            'Aucun pari n’est enregistré dans cette session. '
            'L’analyse peut être consultée, mais la sélection de pomme '
            'est verrouillée.</div>',
            unsafe_allow_html=True
        )
    elif state == "PARI ACTIF":
        st.markdown(
            f'<div class="state good"><b>🟢 PARI ACTIF</b><br>'
            f'Mise enregistrée : <b>{st.session_state.bet_amount:.0f} F</b><br>'
            'La sélection d’une pomme est maintenant autorisée.</div>',
            unsafe_allow_html=True
        )
    elif state == "POMME CHOISIE":
        st.markdown(
            f'<div class="state warn"><b>🟠 POMME CHOISIE</b><br>'
            f'Colonne sélectionnée : <b>C{st.session_state.selected_col}</b>.<br>'
            'Le résultat réel doit ensuite être enregistré.</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="state neutral"><b>⚪ TOUR TERMINÉ</b><br>'
            'Démarre un nouveau tour pour continuer.</div>',
            unsafe_allow_html=True
        )

# ============================================================
# STATISTIQUES
# ============================================================

def weighted_scores():
    h = valid_history()
    scores = np.ones(N_COLS, dtype=float)

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
    margin = z * math.sqrt(
        p*(1-p)/trials + z*z/(4*trials*trials)
    )
    return max(0.0, (center - margin) / den)

def confidence_for_column(col):
    h = valid_history()
    n = len(h)

    if n < 20:
        return 0.0, "INSUFFISANT"

    successes = sum(int(x["safe_col"]) == col for x in h)
    lower = wilson_lower(successes, n)
    p = weighted_scores()[col - 1]
    sample_factor = min(1.0, n / 150.0)

    confidence = 100 * (
        0.70 * lower +
        0.20 * p +
        0.10 * sample_factor
    )

    if confidence >= 70:
        level = "FORT"
    elif confidence >= 55:
        level = "MOYEN"
    else:
        level = "FAIBLE"

    return float(min(confidence, 99.0)), level

def prediction_accuracy():
    rows = [
        x for x in st.session_state.history
        if int(x.get("prediction_col", 0)) in range(1, 6)
        and int(x.get("safe_col", 0)) in range(1, 6)
    ]
    if not rows:
        return None
    return sum(
        int(x["prediction_col"]) == int(x["safe_col"])
        for x in rows
    ) / len(rows)

# ============================================================
# DÉTECTION DE GRILLE
# ============================================================

def detect_grid(image):
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    h, w, _ = arr.shape

    # Zone centrale de la grille : évite autant que possible
    # l'en-tête et les boutons de mise.
    y_top = int(h * 0.12)
    y_bottom = int(h * 0.82)

    roi = arr[y_top:y_bottom]
    intensity = roi.mean(axis=2)

    px = intensity.mean(axis=0)
    py = intensity.mean(axis=1)

    kx = max(7, int(w * 0.015))
    ky = max(7, int(h * 0.015))

    sx = np.convolve(px, np.ones(kx)/kx, mode="same")
    sy = np.convolve(py, np.ones(ky)/ky, mode="same")

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
            weights = np.maximum(local-local.min(), 0.001)
            pos = np.arange(a, b)
            x = int(np.sum(pos*weights)/np.sum(weights))
        else:
            x = int(bx)

        xs.append(x)

    top = int(h * 0.18)
    bottom = int(h * 0.78)
    n_rows = 8
    base_y = np.linspace(top, bottom, n_rows)

    ys = []
    for by in base_y:
        a = max(0, int(by)-search)
        b = min(h, int(by)+search+1)
        local = sy[
            max(0, a-y_top):
            max(0, b-y_top)
        ]

        if len(local):
            weights = np.maximum(local-local.min(), 0.001)
            pos = np.arange(a, b)[:len(local)]
            y = int(np.sum(pos*weights)/np.sum(weights))
        else:
            y = int(by)

        ys.append(y)

    radius = max(18, int(min(h, w)*0.043))

    return {
        "width": w,
        "height": h,
        "columns": xs,
        "rows": ys,
        "radius": radius
    }

def draw_grid_overlay(image, grid, chosen_col=None):
    out = image.copy().convert("RGB")
    draw = ImageDraw.Draw(out)

    xs = grid["columns"]
    ys = grid["rows"]
    r = grid["radius"]

    for ci, x in enumerate(xs, start=1):
        for y in ys:
            draw.ellipse(
                (x-r, y-r, x+r, y+r),
                outline="white",
                width=3
            )
            draw.text((x-7, y-8), str(ci), fill="white")

    if chosen_col in range(1, 6):
        x = xs[chosen_col-1]
        for y in ys:
            draw.ellipse(
                (x-r-5, y-r-5, x+r+5, y+r+5),
                outline="lime",
                width=5
            )

    return out

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Paramètres")

    threshold = st.slider(
        "Seuil du signal",
        50, 90, 70, 5
    )

    bankroll = st.number_input(
        "Bankroll (F CFA)",
        min_value=0.0,
        value=10000.0,
        step=500.0
    )

    stake = st.number_input(
        "Mise à enregistrer (F CFA)",
        min_value=0.0,
        value=200.0,
        step=50.0
    )

    st.divider()
    st.write("État :", f"**{game_state()}**")

# ============================================================
# PANNEAU PARI
# ============================================================

st.subheader("🎮 Contrôle du tour")

state_box()

c1, c2, c3 = st.columns(3)

with c1:
    if not st.session_state.bet_active and not st.session_state.round_finished:
        if st.button("💰 LANCER LA MISE", use_container_width=True):
            if stake <= 0:
                st.error("La mise doit être supérieure à 0 F.")
            else:
                st.session_state.bet_active = True
                st.session_state.bet_amount = float(stake)
                st.session_state.bet_started_at = datetime.now().isoformat(
                    timespec="seconds"
                )
                st.session_state.selected_col = None
                st.session_state.round_finished = False
                st.rerun()
    else:
        st.button(
            "💰 MISE ENREGISTRÉE",
            disabled=True,
            use_container_width=True
        )

with c2:
    if st.session_state.bet_active:
        if st.button("🔄 ANNULER LA SESSION", use_container_width=True):
            st.session_state.bet_active = False
            st.session_state.bet_amount = 0.0
            st.session_state.bet_started_at = None
            st.session_state.selected_col = None
            st.session_state.round_finished = False
            st.rerun()

with c3:
    if st.session_state.round_finished:
        if st.button("▶️ NOUVEAU TOUR", use_container_width=True):
            st.session_state.bet_active = False
            st.session_state.bet_amount = 0.0
            st.session_state.bet_started_at = None
            st.session_state.selected_col = None
            st.session_state.round_finished = False
            st.session_state.prediction_col = None
            st.rerun()

st.info(
    "Si tu as déjà appuyé sur MISE dans le vrai jeu, cette application "
    "d'analyse ne peut pas retirer cette mise ni vérifier le serveur. "
    "Elle peut seulement suivre l'état que tu enregistres ici."
)

# ============================================================
# ONGLETS
# ============================================================

tab_capture, tab_analysis, tab_history, tab_validation = st.tabs(
    ["📸 Capture", "🧠 Analyse", "📊 Historique", "🧪 Validation"]
)

# ============================================================
# CAPTURE
# ============================================================

with tab_capture:
    st.subheader("📸 Charger la capture Apple of Fortune")

    uploaded = st.file_uploader(
        "Sélectionne une capture d'écran",
        type=["png", "jpg", "jpeg", "webp"]
    )

    if uploaded:
        image = Image.open(uploaded).convert("RGB")
        st.image(image, use_container_width=True)

        if st.button(
            "🔎 DÉTECTER LA GRILLE",
            use_container_width=True
        ):
            try:
                grid = detect_grid(image)
                st.session_state.grid = grid

                probs = weighted_scores()
                chosen = int(np.argmax(probs)) + 1
                st.session_state.prediction_col = chosen

                st.session_state.overlay = draw_grid_overlay(
                    image, grid, chosen
                )

                st.success(
                    "Grille détectée. Les colonnes ont été repérées."
                )
            except Exception as e:
                st.error(f"Erreur de détection : {e}")

    if st.session_state.overlay is not None:
        st.subheader("🗺️ Grille détectée")
        st.image(
            st.session_state.overlay,
            use_container_width=True
        )

        st.divider()
        st.subheader("🎯 Sélection de la pomme")

        # VERROU PRINCIPAL
        if not st.session_state.bet_active:
            st.error(
                "🔒 SÉLECTION VERROUILLÉE — ENREGISTRE D'ABORD LA MISE."
            )
        elif st.session_state.round_finished:
            st.info("Ce tour est terminé. Lance un nouveau tour.")
        else:
            st.success(
                f"🟢 Pari actif : {st.session_state.bet_amount:.0f} F. "
                "Tu peux maintenant sélectionner une colonne."
            )

            chosen = st.session_state.prediction_col

            if chosen:
                conf, level = confidence_for_column(chosen)
                st.write(
                    f"Analyse statistique : **C{chosen}** — "
                    f"{conf:.1f}% — **{level}**"
                )

            col = st.radio(
                "Choisir la colonne de la pomme",
                [1, 2, 3, 4, 5],
                format_func=lambda x: f"🍎 C{x}",
                horizontal=True,
                disabled=not st.session_state.bet_active
            )

            if st.button(
                "🍎 VALIDER LA POMME",
                use_container_width=True,
                disabled=not st.session_state.bet_active
            ):
                st.session_state.selected_col = int(col)
                st.success(
                    f"Pomme sélectionnée : C{col}. "
                    "Le tour peut maintenant être comparé au résultat réel."
                )
                st.rerun()

# ============================================================
# ANALYSE
# ============================================================

with tab_analysis:
    st.subheader("🧠 Analyse statistique")

    h = valid_history()
    probs = weighted_scores()
    n = len(h)

    rows = []
    for col in range(1, 6):
        conf, level = confidence_for_column(col)
        observed = sum(int(x["safe_col"]) == col for x in h)

        rows.append({
            "Colonne": f"C{col}",
            "Observations": n,
            "Succès observés": observed,
            "Score historique": round(probs[col-1]*100, 1),
            "Confiance prudente": (
                round(conf, 1) if n >= 20 else None
            ),
            "Niveau": level
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    best = int(np.argmax(probs)) + 1
    conf, level = confidence_for_column(best)

    if n < 20:
        st.info(
            f"{n} observation(s). Minimum recommandé : 20."
        )
        st.error("🛑 NE PAS JOUER — historique insuffisant.")
    elif conf >= threshold:
        st.success(
            f"🎯 PRIORITÉ STATISTIQUE : C{best} — "
            f"{conf:.1f}% — {level}"
        )
    else:
        st.error(
            f"🛑 NE PAS JOUER — C{best} n'atteint que "
            f"{conf:.1f}%."
        )

# ============================================================
# HISTORIQUE
# ============================================================

with tab_history:
    st.subheader("📊 Historique des résultats")

    if not st.session_state.history:
        st.info(
            "Aucune observation. Enregistre le résultat réel après chaque tour."
        )
    else:
        hist_df = pd.DataFrame(st.session_state.history)
        st.dataframe(hist_df, use_container_width=True)

        csv = hist_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ EXPORTER CSV",
            csv,
            "apple_ai_history.csv",
            "text/csv"
        )

        if st.button("🗑️ EFFACER L'HISTORIQUE"):
            st.session_state.history = []
            save_history([])
            st.rerun()

# ============================================================
# VALIDATION
# ============================================================

with tab_validation:
    st.subheader("🧪 Validation réelle")

    if st.session_state.selected_col is not None:
        st.info(
            f"Colonne choisie dans le tour actuel : "
            f"**C{st.session_state.selected_col}**"
        )

        actual = st.radio(
            "Après le résultat, quelle colonne était réellement sûre ?",
            [1, 2, 3, 4, 5],
            horizontal=True
        )

        if st.button(
            "💾 ENREGISTRER LE RÉSULTAT RÉEL",
            use_container_width=True
        ):
            predicted = st.session_state.prediction_col or \
                        st.session_state.selected_col

            st.session_state.history.append({
                "date": datetime.now().isoformat(timespec="seconds"),
                "bet_amount": st.session_state.bet_amount,
                "prediction_col": int(predicted),
                "selected_col": int(st.session_state.selected_col),
                "safe_col": int(actual),
            })

            save_history(st.session_state.history)

            st.session_state.round_finished = True
            st.session_state.bet_active = False

            st.success(
                f"Résultat enregistré : C{actual}. "
                f"Prédiction : C{predicted}."
            )

    acc = prediction_accuracy()

    st.divider()

    if acc is None:
        st.info("Pas encore assez de prédictions validées.")
    else:
        st.metric("Précision observée", f"{acc*100:.1f}%")
        st.metric(
            "Prédictions validées",
            len([
                x for x in st.session_state.history
                if int(x.get("prediction_col", 0)) in range(1, 6)
                and int(x.get("safe_col", 0)) in range(1, 6)
            ])
        )

        if acc >= 0.90:
            st.success(
                "La précision historique atteint 90 % ou plus. "
                "Cela reste une mesure passée, pas une garantie future."
            )
        else:
            st.warning(
                "La précision historique est encore sous 90 %."
            )

# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "RODRIGUE APPLE AI V5 — Le logiciel distingue l'état local du tour. "
    "Il ne peut pas annuler ou retirer une vraie mise auprès du serveur."
)
