"""
stats_calculator.py
====================
Calcul des statistiques d'equipe (forme recente, moyennes ponderees)
a partir d'un historique de matchs.

Principe : les matchs les plus recents doivent peser plus lourd que les
matchs anciens dans le calcul de la forme actuelle d'une equipe. On
utilise une ponderation lineaire decroissante (le match le plus recent
a le poids le plus fort).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from poisson_model import TeamStats


@dataclass
class ResultatMatch:
    """Represente le resultat d'un match historique pour une equipe donnee."""

    buts_marques: int
    buts_encaisses: int
    a_domicile: bool
    adversaire: str = ""

    def __post_init__(self) -> None:
        if self.buts_marques < 0 or self.buts_encaisses < 0:
            raise ValueError("Les buts ne peuvent pas etre negatifs.")


def valider_historique(historique: List[ResultatMatch]) -> None:
    """Verifie que l'historique fourni est exploitable mathematiquement."""
    if not historique:
        raise ValueError(
            "L'historique de matchs est vide : impossible de calculer une "
            "moyenne fiable. Fournissez au moins 3 matchs recents."
        )
    if len(historique) < 3:
        raise ValueError(
            f"Seulement {len(historique)} match(s) fourni(s). Un minimum de "
            "3 matchs est requis pour une estimation statistique minimale, "
            "5 a 10 matchs sont recommandes pour une fiabilite correcte."
        )


def poids_lineaires_decroissants(n: int) -> List[float]:
    """Genere une liste de n poids lineairement decroissants, normalises
    pour sommer a 1.0. Le premier element de la liste correspond au match
    le PLUS ANCIEN, le dernier au match le PLUS RECENT (poids maximal).

    Exemple pour n=5 : poids bruts [1, 2, 3, 4, 5] -> normalises.
    """
    if n <= 0:
        raise ValueError("n doit etre > 0")
    poids_bruts = list(range(1, n + 1))
    total = sum(poids_bruts)
    return [w / total for w in poids_bruts]


def moyenne_ponderee(
    valeurs: List[float], poids: Optional[List[float]] = None
) -> float:
    """Calcule une moyenne ponderee. Si aucun poids n'est fourni, utilise
    une ponderation lineaire decroissante donnant plus d'importance aux
    valeurs recentes (supposees en fin de liste).
    """
    if not valeurs:
        raise ValueError("Liste de valeurs vide.")
    if poids is None:
        poids = poids_lineaires_decroissants(len(valeurs))
    if len(poids) != len(valeurs):
        raise ValueError("Le nombre de poids doit correspondre au nombre de valeurs.")
    if abs(sum(poids) - 1.0) > 1e-6:
        raise ValueError("Les poids doivent sommer a 1.0.")

    return sum(v * w for v, w in zip(valeurs, poids))


def calculer_forme_equipe(
    nom_equipe: str,
    historique: List[ResultatMatch],
    filtrer_domicile: Optional[bool] = None,
    ponderation_recente: bool = True,
) -> TeamStats:
    """Calcule les statistiques de forme d'une equipe a partir de son
    historique de matchs recents.

    Args:
        nom_equipe: nom affiche de l'equipe.
        historique: liste de ResultatMatch, ordonnee du plus ANCIEN
            au plus RECENT (important pour la ponderation).
        filtrer_domicile: si True, ne garde que les matchs a domicile ;
            si False, ne garde que les matchs a l'exterieur ; si None,
            garde tous les matchs (recommande si peu de matchs disponibles).
        ponderation_recente: si True, pondere les matchs recents plus
            fortement (recommande). Si False, moyenne simple.

    Returns:
        TeamStats pret a etre injecte dans le modele Poisson.
    """
    valider_historique(historique)

    if filtrer_domicile is not None:
        historique_filtre = [
            m for m in historique if m.a_domicile == filtrer_domicile
        ]
        if len(historique_filtre) >= 3:
            historique = historique_filtre
        # Sinon on garde l'historique complet (pas assez de matchs filtres
        # pour etre statistiquement significatif) -- on le signale au
        # niveau de l'appelant via matchs_analyses.

    buts_marques = [float(m.buts_marques) for m in historique]
    buts_encaisses = [float(m.buts_encaisses) for m in historique]

    if ponderation_recente and len(historique) >= 3:
        moy_marques = moyenne_ponderee(buts_marques)
        moy_encaisses = moyenne_ponderee(buts_encaisses)
    else:
        moy_marques = sum(buts_marques) / len(buts_marques)
        moy_encaisses = sum(buts_encaisses) / len(buts_encaisses)

    return TeamStats(
        nom=nom_equipe,
        buts_marques_moyenne=round(moy_marques, 3),
        buts_encaisses_moyenne=round(moy_encaisses, 3),
        matchs_analyses=len(historique),
    )


def indice_regularite(historique: List[ResultatMatch]) -> float:
    """Calcule un indice de regularite (0 a 100) base sur l'ecart-type
    des buts marques : une equipe reguliere a une variance faible.

    Utile pour moduler la CONFIANCE affichee a l'utilisateur (une equipe
    tres irreguliere merite un avertissement, pas une fausse certitude).
    """
    valider_historique(historique)
    buts = [m.buts_marques for m in historique]
    n = len(buts)
    moyenne = sum(buts) / n
    variance = sum((b - moyenne) ** 2 for b in buts) / n
    ecart_type = variance ** 0.5

    # Normalisation empirique : un ecart-type de 0 -> 100 (parfaitement
    # regulier), un ecart-type >= 2.5 buts -> 0 (tres irregulier).
    indice = max(0.0, 100.0 - (ecart_type / 2.5) * 100.0)
    return round(indice, 1)


if __name__ == "__main__":
    # Test rapide avec un historique fictif mais realiste
    historique_test = [
        ResultatMatch(buts_marques=1, buts_encaisses=1, a_domicile=False),
        ResultatMatch(buts_marques=2, buts_encaisses=0, a_domicile=True),
        ResultatMatch(buts_marques=0, buts_encaisses=1, a_domicile=False),
        ResultatMatch(buts_marques=3, buts_encaisses=1, a_domicile=True),
        ResultatMatch(buts_marques=1, buts_encaisses=0, a_domicile=True),
    ]

    stats = calculer_forme_equipe("Test FC", historique_test)
    print(f"Stats calculees : {stats}")

    reg = indice_regularite(historique_test)
    print(f"Indice de regularite : {reg}/100")
