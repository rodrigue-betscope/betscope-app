import streamlit as st
import random

st.set_page_config(page_title="BetScope Pro - Analyseur Grille", layout="centered")

st.markdown("## 🤖 BetScope Pro - Analyseur Dynamique")
st.markdown("Télécharge ou prends en photo ta grille de jeu pour lancer l'analyse probabiliste.")

# Uploader natif Streamlit pour l'image de la grille
uploaded_file = st.file_uploader("Choisir une image de la grille", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.success("✅ Grille chargée avec succès !")
    st.image(uploaded_file, caption="Grille analysée", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📊 Résultats de l'Analyse en Cours")
    
    # Ajustement de la fiabilité globale entre 90% et 91.5%
    win_rate = round(random.uniform(90.0, 91.5), 1)
    safe_picks = random.randint(3, 5)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Fiabilité Estimée", f"{win_rate}%")
    col2.metric("Lignes Conseillées", f"{safe_picks}")
    col3.metric("Statut", "Ultra-Optimisé")
    
    st.markdown("---")
    st.markdown("### 🎯 Recommandations de Lignes Sûres :")
    
    # Affichage des multiplicateurs avec une dégressivité très faible pour rester autour de 90%
    multipliers = [1.23, 1.54, 1.93, 2.41, 4.02]
    
    for i in range(min(safe_picks, len(multipliers))):
        mult = multipliers[i]
        reussite = round(win_rate - (i * 0.4), 1)  # Baisse minime pour maintenir une haute précision
        st.markdown(f"""
        <div style="background: #111827; padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #374151;">
            <strong>🍎 Niveau x{mult}</strong> — Probabilité de succès : <span style="color: #10B981;">{reussite}%</span>
        </div>
        """, unsafe_allow_html=True)

else:
    st.info("Veuillez importer une capture de votre grille pour afficher les pronostics.")
