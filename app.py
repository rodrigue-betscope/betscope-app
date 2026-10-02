"""Prédictions de football : loi de Poisson (xG) + IA + cotes. Streamlit."""
import math

import numpy as np
import pandas as pd
import streamlit as st

MAX_BUTS = 10
COLONNES = ["xg_dom", "xg_ext", "cote1", "coten", "cote2", "resultat"]


# ------------------------------------------------------------ Poisson
def matrice_poisson(lam_d, lam_e):
    k = np.arange(MAX_BUTS + 1)
    fact = np.array([math.factorial(int(i)) for i in k], dtype=float)
    p_d = np.exp(-lam_d) * lam_d ** k / fact
    p_e = np.exp(-lam_e) * lam_e ** k / fact
    m = np.outer(p_d, p_e)
    return m / m.sum()


def probas_1n2(m):
    return np.array([np.tril(m, -1).sum(), np.trace(m), np.triu(m, 1).sum()])


def probas_marche(cotes):
    """Probabilités implicites des cotes, marge du bookmaker retirée."""
    brut = 1 / np.array(cotes, dtype=float)
    return brut / brut.sum()


def caracteristiques(xg_d, xg_e, cotes):
    pp = probas_1n2(matrice_poisson(xg_d, xg_e))
    pm = probas_marche(cotes)
    return np.concatenate([[xg_d, xg_e, xg_d - xg_e], pp, pm])


# ----------------------------------------------------------------- IA
class RegressionSoftmax:
    """Petit modèle d'apprentissage (régression logistique multiclasse)."""

    def __init__(self, lr=0.1, iters=1500, l2=0.01):
        self.lr, self.iters, self.l2 = lr, iters, l2

    @staticmethod
    def _softmax(z):
        z = z - z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)

    def fit(self, X, y):
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        Z = (X - self.mu) / self.sd
        n, d = Z.shape
        Y = np.eye(3)[y]
        self.W, self.b = np.zeros((d, 3)), np.zeros(3)
        for _ in range(self.iters):
            G = self._softmax(Z @ self.W + self.b) - Y
            self.W -= self.lr * (Z.T @ G / n + self.l2 * self.W)
            self.b -= self.lr * G.mean(0)
        return self

    def predict_proba(self, X):
        return self._softmax(((X - self.mu) / self.sd) @ self.W + self.b)


def preparer(df):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    manquantes = [c for c in COLONNES if c not in df.columns]
    if manquantes:
        raise ValueError("Colonnes manquantes : " + ", ".join(manquantes))
    for c in COLONNES[:5]:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "."), errors="coerce")
    df["resultat"] = df["resultat"].astype(str).str.strip().str.upper().replace({"X": "N"})
    df = df.dropna(subset=COLONNES)
    df = df[df["resultat"].isin(["1", "N", "2"]) & (df["cote1"] > 1) & (df["coten"] > 1) & (df["cote2"] > 1)]
    X = np.array([caracteristiques(r.xg_dom, r.xg_ext, [r.cote1, r.coten, r.cote2])
                  for r in df.itertuples()])
    y = df["resultat"].map({"1": 0, "N": 1, "2": 2}).to_numpy()
    return X, y


def entrainer_ia(df):
    """Entraîne l'IA sur les vrais résultats ; mesure la précision sur les 20 % les plus récents."""
    X, y = preparer(df)
    if len(y) < 50:
        raise ValueError(f"Il faut au moins 50 matchs valides (trouvés : {len(y)}).")
    coupe = int(len(y) * 0.8)
    test = RegressionSoftmax().fit(X[:coupe], y[:coupe])
    info = {
        "n": len(y),
        "acc_ia": float((test.predict_proba(X[coupe:]).argmax(1) == y[coupe:]).mean()),
        "acc_poisson": float((X[coupe:, 3:6].argmax(1) == y[coupe:]).mean()),
    }
    return RegressionSoftmax().fit(X, y), info


# ------------------------------------------------------------ interface
st.set_page_config(page_title="Prédictions foot", page_icon="⚽")
st.title("⚽ Prédictions de football")
st.caption("Loi de Poisson (xG) + IA + cotes. Aucune garantie de gain.")

c1, c2 = st.columns(2)
dom = c1.text_input("Équipe à domicile", value="")
ext = c2.text_input("Équipe à l'extérieur", value="")

x1, x2 = st.columns(2)
xg_d = x1.number_input("xG domicile", min_value=0.0, max_value=6.0, value=1.40, step=0.05)
xg_e = x2.number_input("xG extérieur", min_value=0.0, max_value=6.0, value=1.10, step=0.05)

st.write("Cotes du bookmaker")
k1, kn, k2 = st.columns(3)
cote1 = k1.number_input("Cote 1", min_value=1.01, value=2.00, step=0.05)
coten = kn.number_input("Cote N", min_value=1.01, value=3.40, step=0.05)
cote2 = k2.number_input("Cote 2", min_value=1.01, value=3.80, step=0.05)

with st.expander("IA : apprentissage sur vos résultats réels (optionnel)"):
    st.write("CSV avec les colonnes : xg_dom, xg_ext, cote1, coten, cote2, resultat (1, N ou 2). "
             "Minimum 50 matchs réels, du plus ancien au plus récent.")
    st.download_button("Télécharger le modèle de CSV",
                       "xg_dom,xg_ext,cote1,coten,cote2,resultat\n1.8,0.9,1.70,3.80,5.00,1\n",
                       file_name="modele_historique.csv")
    fichier = st.file_uploader("Votre historique", type="csv")

ia, info = None, None
if fichier is not None:
    try:
        ia, info = entrainer_ia(pd.read_csv(fichier))
        st.success(f"IA entraînée sur {info['n']} matchs. Sur les 20 % les plus récents : "
                   f"IA {100 * info['acc_ia']:.0f} %, Poisson seul {100 * info['acc_poisson']:.0f} %.")
    except Exception as e:
        st.error(f"IA non activée : {e}")

if st.button("Analyser le match"):
    nom_d, nom_e = dom.strip() or "Domicile", ext.strip() or "Extérieur"
    cotes = np.array([cote1, coten, cote2], dtype=float)
    m = matrice_poisson(xg_d, xg_e)
    p_poi, p_mar = probas_1n2(m), probas_marche(cotes)
    colonnes = {"Poisson (%)": p_poi, "Marché (%)": p_mar}
    if ia is not None:
        colonnes["IA (%)"] = ia.predict_proba(caracteristiques(xg_d, xg_e, cotes)[None, :])[0]
    p = np.mean(list(colonnes.values()), axis=0)  # moyenne des composantes actives
    colonnes["Combiné (%)"] = p
    edge = p * cotes - 1

    noms = [f"Victoire {nom_d}", "Match nul", f"Victoire {nom_e}"]
    k = int(p.argmax())
    st.subheader(f"{nom_d} - {nom_e}")
    st.success(f"Pronostic : {noms[k]}  |  Confiance : {100 * p[k]:.1f} %")

    tab = pd.DataFrame({n: 100 * v for n, v in colonnes.items()}, index=["1", "N", "2"])
    tab["Cote"], tab["Avantage (%)"] = cotes, 100 * edge
    st.dataframe(tab.round(1))

    top = np.argsort(m.ravel())[::-1][:5]
    st.write("Scores les plus probables (Poisson) : " + " | ".join(
        f"{i // (MAX_BUTS + 1)}-{i % (MAX_BUTS + 1)} ({100 * m.ravel()[i]:.0f} %)" for i in top))
    tot = np.add.outer(np.arange(MAX_BUTS + 1), np.arange(MAX_BUTS + 1))
    st.write(f"Plus de 2,5 buts : {100 * m[tot > 2.5].sum():.0f} %  |  "
             f"Les deux équipes marquent : {100 * m[1:, 1:].sum():.0f} %")
    if ia is None:
        st.info("IA non activée : ajoutez votre historique réel ci-dessus pour la coupler à Poisson.")
    j = int(edge.argmax())
    if edge[j] > 0.05:
        st.info(f"Meilleure valeur : issue {['1', 'N', '2'][j]} (avantage {100 * edge[j]:.1f} %)")
    else:
        st.warning("Aucune valeur nette dans ces cotes : prudence.")
