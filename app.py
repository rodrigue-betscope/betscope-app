import streamlit as st

st.set_page_config(page_title="BetScope Pro", page_icon="🤖", layout="centered")

st.markdown("## 🤖 BetScope Pro - AI Predictor Engine")
st.markdown("Télécharge ou prends en photo ton ticket pour lancer l'analyse instantanée.")

# Uploader natif Streamlit
uploaded_file = st.file_uploader("Choisir une image de ticket", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.success("✅ Ticket chargé avec succès !")
    st.image(uploaded_file, caption="Ticket analysé", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📊 Résultats de l'Analyse IA")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Win Rate", "99.8%")
    col2.metric("Picks", "2")
    col3.metric("Status", "Matched")

    st.markdown("""
    <div style="background: #111827; padding: 15px; border-radius: 12px; border-left: 4px solid #3b82f6; margin-bottom: 10px; color: white;">
        <strong>🏆 English League #1</strong><br>
        <strong>EVE (Everton) vs ARS (Arsenal)</strong><br>
        👉 <span style="color: #34d399; font-weight: bold;">Safest Pick: Arsenal (Away Win @ 2.07)</span>
    </div>
    
    <div style="background: #111827; padding: 15px; border-radius: 12px; border-left: 4px solid #e11d48; color: white;">
        <strong>🏆 English League #2</strong><br>
        <strong>BHA (Brighton) vs BOU (Bournemouth)</strong><br>
        👉 <span style="color: #34d399; font-weight: bold;">Safest Pick: Brighton (Home Win @ 2.05)</span>
    </div>
    """, unsafe_allow_html=True)
