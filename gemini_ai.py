import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

def analyse_ia(donnees):
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = f"""
Tu es BetScope Pro, expert en analyse football.

Analyse ces données réelles API-Football :

{donnees}

Donne un rapport professionnel :

📌 Forme récente
📌 H2H
📌 Blessures
📌 Statistiques attaque/défense
📌 Over 1.5
📌 Over 2.5
📌 Under
📌 BTTS
📌 Mi-temps probable
📌 Deuxième mi-temps
📌 Score exact probable
📌 Risques du pari

Réponds en français.
Donne un niveau de confiance mais aucune garantie.
"""

    resultat = model.generate_content(prompt)
    return resultat.text
