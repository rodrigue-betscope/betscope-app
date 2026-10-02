#!/usr/bin/env python3
"""
Prédictions de football : modèle de Poisson pondéré dans le temps.
Autonome : dépend uniquement de numpy et pandas.

Utilisation :
  python predictions_sportives.py --demo
  python predictions_sportives.py --csv matchs.csv --domicile "PSG" --exterieur "Lyon" --cotes 1.60 4.00 5.50
  python predictions_sportives.py --csv matchs.csv --backtest

Format du CSV : date,domicile,exterieur,buts_dom,buts_ext
(date au format AAAA-MM-JJ)

IMPORTANT : aucun modèle ne garantit 80 % de réussite sur toutes les
prédictions. Le script mesure la précision réelle par backtest : fiez-vous
à ce chiffre, pas à une promesse.
"""
import argparse
import math

import numpy as np
import pandas as pd

MAX_BUTS = 10


# ----------------------------------------------------------------- modèle
class ModelePoisson:
    def __init__(self, demi_vie_jours=180, prior_matchs=3):
        self.demi_vie = demi_vie_jours
        self.prior = prior_matchs  # lissage vers la moyenne de la ligue

    def fit(self, df):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        ref = df["date"].max()
        w = 0.5 ** ((ref - df["date"]).dt.days / self.demi_vie)
        df["w"] = w

        self.moy_dom = np.average(df["buts_dom"], weights=w)
        self.moy_ext = np.average(df["buts_ext"], weights=w)
        moy = (self.moy_dom + self.moy_ext) / 2

        equipes = set(df["domicile"]) | set(df["exterieur"])
        self.att, self.dfn = {}, {}
        for t in equipes:
            d = df[df["domicile"] == t]
            e = df[df["exterieur"] == t]
            poids = d["w"].sum() + e["w"].sum() + self.prior
            marques = (d["buts_dom"] * d["w"]).sum() + (e["buts_ext"] * e["w"]).sum() + self.prior * moy
            encaisses = (d["buts_ext"] * d["w"]).sum() + (e["buts_dom"] * e["w"]).sum() + self.prior * moy
            self.att[t] = marques / poids / moy
            self.dfn[t] = encaisses / poids / moy
        return self

    def matrice_scores(self, dom, ext):
        if dom not in self.att or ext not in self.att:
            raise ValueError(f"Équipe inconnue : {dom} ou {ext}")
        lam_d = self.moy_dom * self.att[dom] * self.dfn[ext]
        lam_e = self.moy_ext * self.att[ext] * self.dfn[dom]
        k = np.arange(MAX_BUTS + 1)
        fact = np.array([math.factorial(int(i)) for i in k], dtype=float)
        p_d = np.exp(-lam_d) * lam_d ** k / fact
        p_e = np.exp(-lam_e) * lam_e ** k / fact
        m = np.outer(p_d, p_e)
        return m / m.sum()

    def probas_1n2(self, dom, ext):
        m = self.matrice_scores(dom, ext)
        p1 = np.tril(m, -1).sum()
        pn = np.trace(m)
        p2 = np.triu(m, 1).sum()
        return np.array([p1, pn, p2])

    def score_probable(self, dom, ext):
        m = self.matrice_scores(dom, ext)
        i, j = np.unravel_index(m.argmax(), m.shape)
        return int(i), int(j)


# ------------------------------------------------------- cotes et valeur
def probas_implicites(cotes):
    """Probabilités du bookmaker, marge retirée."""
    brut = 1 / np.array(cotes, dtype=float)
    return brut / brut.sum()


def analyser_match(modele, dom, ext, cotes=None):
    p = modele.probas_1n2(dom, ext)
    noms = ["1 (victoire domicile)", "N (nul)", "2 (victoire extérieur)"]
    k = int(p.argmax())
    res = {
        "match": f"{dom} - {ext}",
        "pronostic": noms[k],
        "confiance_%": round(100 * p[k], 1),
        "score_probable": "%d-%d" % modele.score_probable(dom, ext),
        "probas_%": dict(zip(["1", "N", "2"], np.round(100 * p, 1))),
    }
    if cotes is not None:
        cotes = np.array(cotes, dtype=float)
        edge = p * cotes - 1  # espérance de gain par unité misée
        j = int(edge.argmax())
        res["marge_bookmaker_%"] = round(100 * (1 / cotes).sum() - 100, 1)
        res["meilleure_valeur"] = {
            "issue": ["1", "N", "2"][j],
            "cote": float(cotes[j]),
            "avantage_%": round(100 * edge[j], 1),
            "a_de_la_valeur": bool(edge[j] > 0.05),
        }
    return res


# -------------------------------------------------------------- backtest
def backtest(df, min_train=60, seuil_confiance=0.60):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    ok, n, ok_s, n_s, briers = 0, 0, 0, 0, []
    for i in range(min_train, len(df)):
        m = df.iloc[i]
        modele = ModelePoisson().fit(df.iloc[:i])
        if m["domicile"] not in modele.att or m["exterieur"] not in modele.att:
            continue
        p = modele.probas_1n2(m["domicile"], m["exterieur"])
        reel = 0 if m["buts_dom"] > m["buts_ext"] else (1 if m["buts_dom"] == m["buts_ext"] else 2)
        n += 1
        ok += int(p.argmax() == reel)
        if p.max() >= seuil_confiance:
            n_s += 1
            ok_s += int(p.argmax() == reel)
        y = np.zeros(3)
        y[reel] = 1
        briers.append(((p - y) ** 2).sum())
    return {
        "matchs_testes": n,
        "precision_globale_%": round(100 * ok / n, 1) if n else None,
        f"matchs_confiance>={int(seuil_confiance*100)}%": n_s,
        "precision_confiance_elevee_%": round(100 * ok_s / n_s, 1) if n_s else None,
        "brier_moyen": round(float(np.mean(briers)), 4) if briers else None,
    }


# ------------------------------------------------------------ données démo
def donnees_demo(n=600, seed=1):
    rng = np.random.default_rng(seed)
    equipes = [f"Equipe_{c}" for c in "ABCDEFGHIJKLMNOPQRST"]
    force = {t: rng.normal(0, 0.3) for t in equipes}
    dates = pd.date_range("2024-08-01", periods=n, freq="12h")
    lignes = []
    for d in dates:
        a, b = rng.choice(equipes, 2, replace=False)
        lam_a = math.exp(0.3 + force[a] - force[b] * 0.5)
        lam_b = math.exp(0.0 + force[b] - force[a] * 0.5)
        lignes.append((d.date(), a, b, rng.poisson(lam_a), rng.poisson(lam_b)))
    return pd.DataFrame(lignes, columns=["date", "domicile", "exterieur", "buts_dom", "buts_ext"])


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--domicile")
    ap.add_argument("--exterieur")
    ap.add_argument("--cotes", nargs=3, type=float, metavar=("C1", "CN", "C2"))
    ap.add_argument("--backtest", action="store_true")
    a = ap.parse_args()

    if a.demo:
        df = donnees_demo()
        print("Mode démo (données simulées).")
    elif a.csv:
        df = pd.read_csv(a.csv)
    else:
        ap.error("Fournir --csv ou --demo")

    if a.backtest or a.demo:
        print("Backtest :", backtest(df))

    modele = ModelePoisson().fit(df)
    if a.demo and not a.domicile:
        a.domicile, a.exterieur, a.cotes = "Equipe_A", "Equipe_B", [2.0, 3.4, 3.8]
    if a.domicile and a.exterieur:
        print(analyser_match(modele, a.domicile, a.exterieur, a.cotes))


if __name__ == "__main__":
    main()
