"""
==============================================================================
BETSCOPE PRO — Analyse professionnelle de matchs de football
==============================================================================

Application Streamlit qui combine :
  - API-Football (données réelles : forme, H2H, statistiques d'équipe, cotes)
  - Un moteur de prédiction statistique (pas de hasard, calculs réels)
  - Gemini (rédaction du résumé en français, jamais de calcul de probas)
  - gTTS (résumé audio en français)

Architecture (tout dans ce seul fichier, mais séparé par sections/classes) :
  1. Configuration & constantes
  2. Modèles de données (dataclasses)
  3. Client API-Football (récupération des données brutes)
  4. Moteur de prédiction (calculs statistiques)
  5. Service Gemini (génération de texte à partir des stats)
  6. Service audio (gTTS)
  7. Utilitaires d'affichage / formatage
  8. Interface Streamlit (page principale)

Pour lancer :
    pip install -r requirements.txt
    streamlit run betscope_stats.py

Variables d'environnement requises (ou via st.secrets) :
    API_FOOTBALL_KEY   -> clé API-Football (RapidAPI ou api-football.com direct)
    GEMINI_API_KEY      -> clé Google Gemini
==============================================================================
"""

from __future__ import annotations

import os
import io
import json
import time
import logging
import datetime as dt
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from functools import lru_cache

import requests
import streamlit as st

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


# ==============================================================================
# 1. CONFIGURATION & CONSTANTES
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("betscope")


class Config:
    """Configuration centralisée de l'application."""

    APP_NAME = "BetScope Pro"
    APP_VERSION = "2.0.0"

    # API-Football : deux hôtes possibles selon l'offre souscrite.
    # "direct" = api-football.com direct, "rapidapi" = via RapidAPI.
    API_FOOTBALL_MODE = os.environ.get("API_FOOTBALL_MODE", "direct")

    API_FOOTBALL_HOST_DIRECT = "https://v3.football.api-sports.io"
    API_FOOTBALL_HOST_RAPIDAPI = "https://api-football-v1.p.rapidapi.com/v3"
    RAPIDAPI_HOST_HEADER = "api-football-v1.p.rapidapi.com"

    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

    REQUEST_TIMEOUT_SECONDS = 15
    MAX_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 1.5

    H2H_MATCH_COUNT = 5
    FORM_MATCH_COUNT = 5

    CACHE_TTL_SECONDS = 600  # 10 minutes

    AUDIO_LANGUAGE = "fr"
    AUDIO_TLD = "fr"  # accent français

    @staticmethod
    def get_secret(name: str, default: str = "") -> str:
        """Récupère une clé depuis st.secrets en priorité, sinon les variables d'env."""
        try:
            if name in st.secrets:
                return str(st.secrets[name])
        except Exception:
            pass
        return os.environ.get(name, default)

    @classmethod
    def api_football_key(cls) -> str:
        return cls.get_secret("API_FOOTBALL_KEY")

    @classmethod
    def gemini_api_key(cls) -> str:
        return cls.get_secret("GEMINI_API_KEY")

    @classmethod
    def api_football_base_url(cls) -> str:
        if cls.API_FOOTBALL_MODE == "rapidapi":
            return cls.API_FOOTBALL_HOST_RAPIDAPI
        return cls.API_FOOTBALL_HOST_DIRECT

    @classmethod
    def api_football_headers(cls) -> Dict[str, str]:
        key = cls.api_football_key()
        if cls.API_FOOTBALL_MODE == "rapidapi":
            return {
                "x-rapidapi-key": key,
                "x-rapidapi-host": cls.RAPIDAPI_HOST_HEADER,
            }
        return {"x-apisports-key": key}


# ==============================================================================
# 2. MODÈLES DE DONNÉES
# ==============================================================================

@dataclass
class TeamInfo:
    """Informations de base sur une équipe."""
    id: int
    name: str
    logo_url: str = ""
    country: str = ""


@dataclass
class FixtureInfo:
    """Informations sur une rencontre (match à venir ou passé)."""
    id: int
    date: str
    league_name: str
    league_country: str
    home_team: TeamInfo = None
    away_team: TeamInfo = None
    status_short: str = ""
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    venue: str = ""


@dataclass
class TeamForm:
    """Forme récente d'une équipe sur ses N derniers matchs."""
    team_id: int
    team_name: str
    matches_analyzed: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    clean_sheets: int = 0
    failed_to_score: int = 0
    form_string: str = ""  # ex: "WWDLW"

    @property
    def avg_goals_scored(self) -> float:
        if self.matches_analyzed == 0:
            return 0.0
        return round(self.goals_scored / self.matches_analyzed, 2)

    @property
    def avg_goals_conceded(self) -> float:
        if self.matches_analyzed == 0:
            return 0.0
        return round(self.goals_conceded / self.matches_analyzed, 2)

    @property
    def points_per_game(self) -> float:
        if self.matches_analyzed == 0:
            return 0.0
        points = self.wins * 3 + self.draws
        return round(points / self.matches_analyzed, 2)

    @property
    def win_rate(self) -> float:
        if self.matches_analyzed == 0:
            return 0.0
        return round(100 * self.wins / self.matches_analyzed, 1)


@dataclass
class H2HRecord:
    """Historique des confrontations directes entre deux équipes."""
    total_matches: int = 0
    team1_wins: int = 0
    team2_wins: int = 0
    draws: int = 0
    avg_total_goals: float = 0.0
    recent_results: List[str] = field(default_factory=list)  # descriptions courtes
    btts_rate: float = 0.0  # % de matchs où les deux équipes marquent
    over_2_5_rate: float = 0.0  # % de matchs à plus de 2.5 buts


@dataclass
class OddsSnapshot:
    """Cotes disponibles pour un match, pour un marché donné."""
    bookmaker: str = ""
    home_win: Optional[float] = None
    draw: Optional[float] = None
    away_win: Optional[float] = None
    over_2_5: Optional[float] = None
    under_2_5: Optional[float] = None
    btts_yes: Optional[float] = None
    btts_no: Optional[float] = None


@dataclass
class PredictionResult:
    """Résultat consolidé du moteur de prédiction pour un match."""
    fixture: FixtureInfo
    home_form: TeamForm
    away_form: TeamForm
    h2h: H2HRecord
    odds: Optional[OddsSnapshot]

    prob_home_win: float = 0.0
    prob_draw: float = 0.0
    prob_away_win: float = 0.0

    expected_goals_home: float = 0.0
    expected_goals_away: float = 0.0
    expected_total_goals: float = 0.0

    prob_btts: float = 0.0
    prob_over_2_5: float = 0.0

    confidence_level: str = "Moyenne"  # Faible / Moyenne / Élevée
    key_factors: List[str] = field(default_factory=list)

    recommended_bet: str = ""
    value_bet_detected: bool = False
    value_bet_explanation: str = ""


# ==============================================================================
# 3. CLIENT API-FOOTBALL
# ==============================================================================

class ApiFootballError(Exception):
    """Erreur levée lors d'un problème avec l'API-Football."""
    pass


class ApiFootballClient:
    """
    Client pour interagir avec API-Football v3.

    Toute la logique réseau, la gestion des erreurs et des retries
    est centralisée ici. Aucune autre partie du code ne doit faire
    d'appel HTTP direct à API-Football.
    """

    def __init__(self):
        self.base_url = Config.api_football_base_url()
        self.headers = Config.api_football_headers()
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Effectue un appel GET avec retries et gestion d'erreurs."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        params = params or {}
        last_error = None

        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                response = self.session.get(
                    url, params=params, timeout=Config.REQUEST_TIMEOUT_SECONDS
                )
                if response.status_code == 401 or response.status_code == 403:
                    raise ApiFootballError(
                        "Clé API invalide ou accès refusé. Vérifie API_FOOTBALL_KEY "
                        "et ton abonnement sur le dashboard API-Football."
                    )
                if response.status_code == 429:
                    raise ApiFootballError(
                        "Quota API dépassé (429). Vérifie ton quota journalier "
                        "sur le dashboard API-Football."
                    )
                response.raise_for_status()
                payload = response.json()

                errors = payload.get("errors")
                if errors:
                    # L'API renvoie parfois une liste, parfois un dict.
                    if isinstance(errors, dict) and len(errors) > 0:
                        raise ApiFootballError(f"Erreur API-Football : {errors}")
                    if isinstance(errors, list) and len(errors) > 0:
                        raise ApiFootballError(f"Erreur API-Football : {errors}")

                return payload

            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                logger.warning(
                    "Tentative %s/%s échouée pour %s : %s",
                    attempt, Config.MAX_RETRIES, endpoint, exc,
                )
                time.sleep(Config.RETRY_BACKOFF_SECONDS * attempt)
            except ApiFootballError:
                raise
            except ValueError as exc:
                raise ApiFootballError(f"Réponse JSON invalide de l'API : {exc}")

        raise ApiFootballError(
            f"Impossible de contacter API-Football après {Config.MAX_RETRIES} "
            f"tentatives. Dernière erreur : {last_error}"
        )

    # -- Recherche de matchs ---------------------------------------------

    def search_fixture_by_teams(
        self, team1_name: str, team2_name: str, season: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Cherche un match à venir entre deux équipes nommées."""
        team1_id = self.find_team_id(team1_name)
        if not team1_id:
            return None

        season = season or dt.date.today().year
        payload = self._get(
            "fixtures",
            {"team": team1_id, "season": season, "next": 20},
        )
        fixtures = payload.get("response", [])

        team2_lower = team2_name.strip().lower()
        for fixture in fixtures:
            home = fixture["teams"]["home"]["name"].lower()
            away = fixture["teams"]["away"]["name"].lower()
            if team2_lower in home or team2_lower in away:
                return fixture
        return None

    def get_fixture_by_id(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un match précis par son ID."""
        payload = self._get("fixtures", {"id": fixture_id})
        results = payload.get("response", [])
        return results[0] if results else None

    @lru_cache(maxsize=256)
    def find_team_id(self, team_name: str) -> Optional[int]:
        """Recherche l'ID d'une équipe à partir de son nom."""
        payload = self._get("teams", {"search": team_name})
        results = payload.get("response", [])
        if not results:
            return None
        return results[0]["team"]["id"]

    # -- Forme des équipes -------------------------------------------------

    def get_team_recent_fixtures(
        self, team_id: int, count: int = Config.FORM_MATCH_COUNT
    ) -> List[Dict[str, Any]]:
        """Récupère les N derniers matchs joués par une équipe."""
        payload = self._get(
            "fixtures", {"team": team_id, "last": count}
        )
        return payload.get("response", [])

    def get_team_statistics(
        self, team_id: int, league_id: int, season: int
    ) -> Dict[str, Any]:
        """Récupère les statistiques globales d'une équipe pour une saison."""
        payload = self._get(
            "teams/statistics",
            {"team": team_id, "league": league_id, "season": season},
        )
        return payload.get("response", {})

    # -- Confrontations directes (H2H) --------------------------------------

    def get_head_to_head(
        self, team1_id: int, team2_id: int, count: int = Config.H2H_MATCH_COUNT
    ) -> List[Dict[str, Any]]:
        """Récupère l'historique des confrontations directes."""
        payload = self._get(
            "fixtures/headtohead",
            {"h2h": f"{team1_id}-{team2_id}", "last": count},
        )
        return payload.get("response", [])

    # -- Cotes ---------------------------------------------------------------

    def get_odds_for_fixture(self, fixture_id: int) -> List[Dict[str, Any]]:
        """Récupère les cotes disponibles pour un match donné."""
        payload = self._get("odds", {"fixture": fixture_id})
        return payload.get("response", [])


# ==============================================================================
# 4. MOTEUR DE PRÉDICTION (calculs statistiques réels)
# ==============================================================================

class PredictionEngine:
    """
    Calcule des probabilités et des statistiques à partir de données réelles
    (forme récente, historique H2H, moyennes de buts).

    Aucune valeur ici n'est générée aléatoirement : tout est dérivé
    des données retournées par API-Football.
    """

    def __init__(self, client: ApiFootballClient):
        self.client = client

    # -- Construction des objets de forme -----------------------------------

    def build_team_form(self, team_id: int, team_name: str) -> TeamForm:
        """Construit un objet TeamForm à partir des derniers matchs joués."""
        fixtures = self.client.get_team_recent_fixtures(team_id)
        form = TeamForm(team_id=team_id, team_name=team_name)

        form_letters = []
        for fixture in fixtures:
            home_id = fixture["teams"]["home"]["id"]
            away_id = fixture["teams"]["away"]["id"]
            home_goals = fixture["goals"]["home"]
            away_goals = fixture["goals"]["away"]

            if home_goals is None or away_goals is None:
                continue  # match non joué / annulé

            is_home = home_id == team_id
            goals_for = home_goals if is_home else away_goals
            goals_against = away_goals if is_home else home_goals

            form.matches_analyzed += 1
            form.goals_scored += goals_for
            form.goals_conceded += goals_against

            if goals_against == 0:
                form.clean_sheets += 1
            if goals_for == 0:
                form.failed_to_score += 1

            if goals_for > goals_against:
                form.wins += 1
                form_letters.append("V")
            elif goals_for < goals_against:
                form.losses += 1
                form_letters.append("D")
            else:
                form.draws += 1
                form_letters.append("N")

        form.form_string = "".join(form_letters)
        return form

    # -- Construction de l'historique H2H ------------------------------------

    def build_h2h_record(
        self, team1_id: int, team2_id: int
    ) -> H2HRecord:
        """Construit l'historique des confrontations directes."""
        matches = self.client.get_head_to_head(team1_id, team2_id)
        record = H2HRecord()

        total_goals_sum = 0
        btts_count = 0
        over_2_5_count = 0
        valid_matches = 0

        for match in matches:
            home_id = match["teams"]["home"]["id"]
            home_goals = match["goals"]["home"]
            away_goals = match["goals"]["away"]

            if home_goals is None or away_goals is None:
                continue

            valid_matches += 1
            total_goals = home_goals + away_goals
            total_goals_sum += total_goals

            if home_goals > 0 and away_goals > 0:
                btts_count += 1
            if total_goals > 2.5:
                over_2_5_count += 1

            home_won = home_goals > away_goals
            away_won = away_goals > home_goals

            if home_won and home_id == team1_id:
                record.team1_wins += 1
            elif home_won and home_id == team2_id:
                record.team2_wins += 1
            elif away_won and home_id == team1_id:
                record.team2_wins += 1
            elif away_won and home_id == team2_id:
                record.team1_wins += 1
            else:
                record.draws += 1

            home_name = match["teams"]["home"]["name"]
            away_name = match["teams"]["away"]["name"]
            record.recent_results.append(
                f"{home_name} {home_goals}-{away_goals} {away_name}"
            )

        record.total_matches = valid_matches
        if valid_matches > 0:
            record.avg_total_goals = round(total_goals_sum / valid_matches, 2)
            record.btts_rate = round(100 * btts_count / valid_matches, 1)
            record.over_2_5_rate = round(100 * over_2_5_count / valid_matches, 1)

        return record

    # -- Cotes -----------------------------------------------------------

    def extract_best_odds(self, fixture_id: int) -> Optional[OddsSnapshot]:
        """Extrait les meilleures cotes disponibles pour les marchés principaux."""
        odds_response = self.client.get_odds_for_fixture(fixture_id)
        if not odds_response:
            return None

        snapshot = OddsSnapshot()
        try:
            bookmakers = odds_response[0].get("bookmakers", [])
            if not bookmakers:
                return None

            snapshot.bookmaker = bookmakers[0].get("name", "N/A")
            for bet in bookmakers[0].get("bets", []):
                bet_name = bet.get("name", "")
                values = bet.get("values", [])

                if bet_name == "Match Winner":
                    for v in values:
                        if v["value"] == "Home":
                            snapshot.home_win = float(v["odd"])
                        elif v["value"] == "Draw":
                            snapshot.draw = float(v["odd"])
                        elif v["value"] == "Away":
                            snapshot.away_win = float(v["odd"])

                elif bet_name == "Goals Over/Under":
                    for v in values:
                        if v["value"] == "Over 2.5":
                            snapshot.over_2_5 = float(v["odd"])
                        elif v["value"] == "Under 2.5":
                            snapshot.under_2_5 = float(v["odd"])

                elif bet_name == "Both Teams Score":
                    for v in values:
                        if v["value"] == "Yes":
                            snapshot.btts_yes = float(v["odd"])
                        elif v["value"] == "No":
                            snapshot.btts_no = float(v["odd"])

        except (KeyError, IndexError, ValueError) as exc:
            logger.warning("Erreur lors de l'extraction des cotes : %s", exc)
            return None

        return snapshot

    # -- Modèle de prédiction (Poisson simplifié + forme) --------------------

    def compute_prediction(
        self,
        fixture: FixtureInfo,
        home_form: TeamForm,
        away_form: TeamForm,
        h2h: H2HRecord,
        odds: Optional[OddsSnapshot],
    ) -> PredictionResult:
        """
        Calcule une prédiction consolidée à partir de :
          - la forme récente (poids principal)
          - l'historique H2H (poids secondaire)
          - un modèle de buts attendus basé sur les moyennes marquées/encaissées

        Le calcul de probabilités de résultat (1X2) utilise une approche
        de type force offensive/défensive, similaire dans l'esprit à un
        modèle de Poisson simplifié, sans tirage aléatoire.
        """
        result = PredictionResult(
            fixture=fixture,
            home_form=home_form,
            away_form=away_form,
            h2h=h2h,
            odds=odds,
        )

        # --- Buts attendus (xG simplifié) ---
        # Moyenne entre l'attaque de l'équipe et la défense adverse,
        # avec un bonus terrain pour l'équipe à domicile.
        home_attack = max(home_form.avg_goals_scored, 0.1)
        home_defense = max(home_form.avg_goals_conceded, 0.1)
        away_attack = max(away_form.avg_goals_scored, 0.1)
        away_defense = max(away_form.avg_goals_conceded, 0.1)

        home_advantage_factor = 1.10
        expected_home_goals = ((home_attack + away_defense) / 2) * home_advantage_factor
        expected_away_goals = (away_attack + home_defense) / 2

        # Ajustement léger avec l'historique H2H si suffisant de données
        if h2h.total_matches >= 3:
            h2h_avg_per_team = h2h.avg_total_goals / 2
            expected_home_goals = round((expected_home_goals * 0.75) + (h2h_avg_per_team * 0.25), 2)
            expected_away_goals = round((expected_away_goals * 0.75) + (h2h_avg_per_team * 0.25), 2)

        result.expected_goals_home = round(expected_home_goals, 2)
        result.expected_goals_away = round(expected_away_goals, 2)
        result.expected_total_goals = round(expected_home_goals + expected_away_goals, 2)

        # --- Probabilités 1X2 ---
        # Basées sur la différence de force (points par match) pondérée
        # par la différence de buts attendus.
        home_strength = (home_form.points_per_game * 0.6) + (expected_home_goals * 0.4)
        away_strength = (away_form.points_per_game * 0.6) + (expected_away_goals * 0.4)

        total_strength = home_strength + away_strength
        if total_strength <= 0:
            base_home, base_away = 0.40, 0.35
        else:
            base_home = home_strength / total_strength
            base_away = away_strength / total_strength

        # Poids H2H (si historique disponible, ajuste légèrement)
        if h2h.total_matches >= 3:
            h2h_home_rate = h2h.team1_wins / h2h.total_matches
            h2h_away_rate = h2h.team2_wins / h2h.total_matches
            base_home = (base_home * 0.8) + (h2h_home_rate * 0.2)
            base_away = (base_away * 0.8) + (h2h_away_rate * 0.2)

        # Marge de nul, influencée par l'écart de force (plus l'écart
        # est faible, plus la probabilité de nul augmente)
        strength_gap = abs(home_strength - away_strength)
        draw_base = max(0.18, 0.32 - (strength_gap * 0.05))

        # Normalisation pour que la somme fasse 100%
        remaining = 1 - draw_base
        total_ha = base_home + base_away
        if total_ha > 0:
            final_home = remaining * (base_home / total_ha)
            final_away = remaining * (base_away / total_ha)
        else:
            final_home = remaining / 2
            final_away = remaining / 2

        result.prob_home_win = round(final_home * 100, 1)
        result.prob_draw = round(draw_base * 100, 1)
        result.prob_away_win = round(final_away * 100, 1)

        # Normalisation finale pour garantir exactement 100%
        total_prob = result.prob_home_win + result.prob_draw + result.prob_away_win
        if total_prob != 100.0 and total_prob > 0:
            factor = 100.0 / total_prob
            result.prob_home_win = round(result.prob_home_win * factor, 1)
            result.prob_draw = round(result.prob_draw * factor, 1)
            result.prob_away_win = round(result.prob_away_win * factor, 1)

        # --- BTTS et Over/Under 2.5 ---
        btts_signal = (
            (100 - home_form.failed_to_score / max(home_form.matches_analyzed, 1) * 100) * 0.35
            + (100 - away_form.failed_to_score / max(away_form.matches_analyzed, 1) * 100) * 0.35
            + h2h.btts_rate * 0.30
        ) if h2h.total_matches > 0 else (
            (100 - home_form.failed_to_score / max(home_form.matches_analyzed, 1) * 100) * 0.5
            + (100 - away_form.failed_to_score / max(away_form.matches_analyzed, 1) * 100) * 0.5
        )
        result.prob_btts = round(min(max(btts_signal, 5), 95), 1)

        over_signal = min(100, (result.expected_total_goals / 2.5) * 55)
        if h2h.total_matches > 0:
            over_signal = (over_signal * 0.6) + (h2h.over_2_5_rate * 0.4)
        result.prob_over_2_5 = round(min(max(over_signal, 5), 95), 1)

        # --- Facteurs clés (explicabilité) ---
        result.key_factors = self._build_key_factors(home_form, away_form, h2h, result)

        # --- Niveau de confiance ---
        result.confidence_level = self._determine_confidence(home_form, away_form, h2h)

        # --- Pari recommandé + détection de value bet ---
        self._determine_recommendation(result, odds)

        return result

    def _build_key_factors(
        self,
        home_form: TeamForm,
        away_form: TeamForm,
        h2h: H2HRecord,
        result: PredictionResult,
    ) -> List[str]:
        """Génère une liste de facteurs clés ayant influencé la prédiction."""
        factors = []

        if home_form.win_rate >= 60:
            factors.append(
                f"{home_form.team_name} est en excellente forme à domicile "
                f"({home_form.wins}V sur {home_form.matches_analyzed} matchs)"
            )
        elif home_form.win_rate <= 20 and home_form.matches_analyzed >= 3:
            factors.append(
                f"{home_form.team_name} traverse une période difficile "
                f"({home_form.losses} défaites récentes)"
            )

        if away_form.win_rate >= 60:
            factors.append(
                f"{away_form.team_name} affiche une forme solide à l'extérieur "
                f"({away_form.wins}V sur {away_form.matches_analyzed} matchs)"
            )
        elif away_form.win_rate <= 20 and away_form.matches_analyzed >= 3:
            factors.append(
                f"{away_form.team_name} peine à l'extérieur récemment"
            )

        if home_form.avg_goals_conceded <= 0.8 and home_form.matches_analyzed >= 3:
            factors.append(f"Défense solide de {home_form.team_name} à domicile")
        if away_form.avg_goals_conceded <= 0.8 and away_form.matches_analyzed >= 3:
            factors.append(f"Défense solide de {away_form.team_name} à l'extérieur")

        if h2h.total_matches >= 3:
            factors.append(
                f"Historique H2H : {h2h.team1_wins} victoires, {h2h.draws} nuls, "
                f"{h2h.team2_wins} victoires adverses sur {h2h.total_matches} confrontations"
            )
            if h2h.over_2_5_rate >= 60:
                factors.append("Les confrontations directes produisent souvent plus de 2.5 buts")

        if result.prob_btts >= 65:
            factors.append("Les deux équipes marquent fréquemment dans leurs matchs récents")

        if not factors:
            factors.append("Données insuffisantes pour dégager des tendances marquées")

        return factors

    def _determine_confidence(
        self, home_form: TeamForm, away_form: TeamForm, h2h: H2HRecord
    ) -> str:
        """Détermine le niveau de confiance de la prédiction selon la qualité des données."""
        data_points = home_form.matches_analyzed + away_form.matches_analyzed + h2h.total_matches
        if data_points >= 12:
            return "Élevée"
        if data_points >= 6:
            return "Moyenne"
        return "Faible"

    def _determine_recommendation(
        self, result: PredictionResult, odds: Optional[OddsSnapshot]
    ) -> None:
        """Détermine le pari recommandé et détecte une éventuelle value bet."""
        probs = {
            "Victoire domicile": result.prob_home_win,
            "Match nul": result.prob_draw,
            "Victoire extérieur": result.prob_away_win,
        }
        best_outcome = max(probs, key=probs.get)
        result.recommended_bet = f"{best_outcome} ({probs[best_outcome]}%)"

        if odds is None:
            return

        # Détection de value bet : compare la probabilité calculée
        # à la probabilité implicite de la cote (1 / cote).
        comparisons = []
        if odds.home_win:
            implied = round(100 / odds.home_win, 1)
            comparisons.append(("Victoire domicile", result.prob_home_win, implied, odds.home_win))
        if odds.draw:
            implied = round(100 / odds.draw, 1)
            comparisons.append(("Match nul", result.prob_draw, implied, odds.draw))
        if odds.away_win:
            implied = round(100 / odds.away_win, 1)
            comparisons.append(("Victoire extérieur", result.prob_away_win, implied, odds.away_win))

        for label, our_prob, implied_prob, odd_value in comparisons:
            edge = our_prob - implied_prob
            if edge >= 8:  # notre modèle voit une proba significativement plus haute que le marché
                result.value_bet_detected = True
                result.value_bet_explanation = (
                    f"Value bet potentiel sur « {label} » : notre modèle estime {our_prob}% "
                    f"contre {implied_prob}% impliqué par la cote ({odd_value}). "
                    f"Écart de {round(edge, 1)} points."
                )
                break


# ==============================================================================
# 5. SERVICE GEMINI (rédaction du texte, jamais de calcul de probabilités)
# ==============================================================================

class GeminiServiceError(Exception):
    """Erreur levée lors d'un problème avec le service Gemini."""
    pass


class GeminiService:
    """
    Service responsable uniquement de la rédaction en langage naturel.

    IMPORTANT : Gemini ne calcule jamais de probabilités ni de statistiques.
    Il reçoit des données déjà calculées par PredictionEngine et les
    reformule en français dans un style professionnel et lisible.
    """

    SYSTEM_INSTRUCTION = (
        "Tu es un rédacteur sportif professionnel spécialisé en football. "
        "Tu reçois des statistiques déjà calculées (probabilités, forme, "
        "historique de confrontations, buts attendus). Ton rôle est UNIQUEMENT "
        "de rédiger un résumé clair, professionnel et engageant en français, "
        "à partir de ces données. Tu ne dois jamais inventer de statistiques, "
        "ni modifier les chiffres fournis. Reste factuel, concis, et structure "
        "ton texte en 3 courts paragraphes : contexte du match, analyse des "
        "tendances clés, conclusion avec le pari le plus probable. "
        "Rappelle systématiquement que ceci est une analyse statistique et "
        "non une garantie de résultat."
    )

    def __init__(self):
        self.api_key = Config.gemini_api_key()
        self._client = None

    @property
    def is_available(self) -> bool:
        return GENAI_AVAILABLE and bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            if not GENAI_AVAILABLE:
                raise GeminiServiceError(
                    "Le package google-genai n'est pas installé. "
                    "Installe-le avec : pip install google-genai"
                )
            if not self.api_key:
                raise GeminiServiceError(
                    "GEMINI_API_KEY n'est pas configurée (variable d'environnement "
                    "ou st.secrets)."
                )
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate_match_summary(self, prediction: PredictionResult) -> str:
        """Génère un résumé rédactionnel en français à partir de la prédiction."""
        if not self.is_available:
            return self._fallback_summary(prediction)

        try:
            client = self._get_client()
            prompt = self._build_prompt(prediction)

            response = client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    temperature=0.7,
                    max_output_tokens=600,
                ),
            )

            text = getattr(response, "text", None)
            if not text:
                logger.warning("Réponse Gemini vide, utilisation du résumé de secours.")
                return self._fallback_summary(prediction)
            return text.strip()

        except Exception as exc:
            logger.error("Erreur Gemini : %s", exc)
            return self._fallback_summary(prediction)

    def _build_prompt(self, p: PredictionResult) -> str:
        """Construit le prompt de données factuelles à envoyer à Gemini."""
        home_name = p.fixture.home_team.name if p.fixture.home_team else "Équipe A"
        away_name = p.fixture.away_team.name if p.fixture.away_team else "Équipe B"

        data = {
            "match": f"{home_name} vs {away_name}",
            "competition": p.fixture.league_name,
            "date": p.fixture.date,
            "probabilites": {
                "victoire_domicile": f"{p.prob_home_win}%",
                "match_nul": f"{p.prob_draw}%",
                "victoire_exterieur": f"{p.prob_away_win}%",
            },
            "buts_attendus": {
                "domicile": p.expected_goals_home,
                "exterieur": p.expected_goals_away,
                "total": p.expected_total_goals,
            },
            "probabilite_btts": f"{p.prob_btts}%",
            "probabilite_plus_2_5_buts": f"{p.prob_over_2_5}%",
            "forme_domicile": {
                "victoires": p.home_form.wins,
                "nuls": p.home_form.draws,
                "defaites": p.home_form.losses,
                "forme": p.home_form.form_string,
            },
            "forme_exterieur": {
                "victoires": p.away_form.wins,
                "nuls": p.away_form.draws,
                "defaites": p.away_form.losses,
                "forme": p.away_form.form_string,
            },
            "confrontations_directes": {
                "total": p.h2h.total_matches,
                "victoires_domicile": p.h2h.team1_wins,
                "nuls": p.h2h.draws,
                "victoires_exterieur": p.h2h.team2_wins,
            },
            "facteurs_cles": p.key_factors,
            "niveau_confiance": p.confidence_level,
            "pari_recommande": p.recommended_bet,
        }

        return (
            "Voici les données statistiques calculées pour ce match. "
            "Rédige le résumé demandé à partir de ces données uniquement :\n\n"
            f"{json.dumps(data, ensure_ascii=False, indent=2)}"
        )

    def _fallback_summary(self, p: PredictionResult) -> str:
        """Résumé généré sans Gemini, si le service est indisponible."""
        home_name = p.fixture.home_team.name if p.fixture.home_team else "Équipe A"
        away_name = p.fixture.away_team.name if p.fixture.away_team else "Équipe B"

        lines = [
            f"{home_name} reçoit {away_name} en {p.fixture.league_name}. "
            f"Notre modèle statistique donne {p.prob_home_win}% de victoire "
            f"pour {home_name}, {p.prob_draw}% de match nul, et {p.prob_away_win}% "
            f"de victoire pour {away_name}.",
            "",
            "Tendances clés : " + " ; ".join(p.key_factors) + ".",
            "",
            f"Le pari le plus probable selon notre analyse est : {p.recommended_bet}. "
            f"Niveau de confiance de cette prédiction : {p.confidence_level}. "
            "Cette analyse reste statistique et ne garantit aucun résultat.",
        ]
        return "\n".join(lines)


# ==============================================================================
# 6. SERVICE AUDIO (gTTS)
# ==============================================================================

class AudioServiceError(Exception):
    """Erreur levée lors de la génération audio."""
    pass


class AudioService:
    """Convertit un résumé texte en fichier audio MP3 (français)."""

    @staticmethod
    def is_available() -> bool:
        return GTTS_AVAILABLE

    @staticmethod
    def generate_audio_bytes(text: str) -> bytes:
        """Génère un fichier MP3 en mémoire à partir d'un texte français."""
        if not GTTS_AVAILABLE:
            raise AudioServiceError(
                "gTTS n'est pas installé. Installe-le avec : pip install gtts"
            )
        if not text or not text.strip():
            raise AudioServiceError("Le texte à convertir en audio est vide.")

        try:
            clean_text = AudioService._clean_text_for_speech(text)
            tts = gTTS(text=clean_text, lang=Config.AUDIO_LANGUAGE, tld=Config.AUDIO_TLD)
            buffer = io.BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            return buffer.read()
        except Exception as exc:
            raise AudioServiceError(f"Erreur lors de la génération audio : {exc}")

    @staticmethod
    def _clean_text_for_speech(text: str) -> str:
        """Nettoie le texte des symboles qui ne se prononcent pas bien."""
        replacements = {
            "%": " pour cent",
            "#": "",
            "*": "",
            "•": "",
            "—": ",",
        }
        cleaned = text
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        return cleaned


# ==============================================================================
# 7. UTILITAIRES D'AFFICHAGE / FORMATAGE
# ==============================================================================

class DisplayFormatter:
    """Utilitaires de formatage pour l'affichage Streamlit."""

    @staticmethod
    def format_percentage_bar(label: str, value: float, color: str = "#1f77b4") -> str:
        """Génère un petit bloc HTML représentant une barre de pourcentage."""
        return f"""
        <div style="margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 14px;">
                <span>{label}</span>
                <strong>{value}%</strong>
            </div>
            <div style="background-color: #eee; border-radius: 6px; height: 10px; width: 100%;">
                <div style="background-color: {color}; width: {min(value, 100)}%;
                            height: 10px; border-radius: 6px;"></div>
            </div>
        </div>
        """

    @staticmethod
    def confidence_badge(level: str) -> str:
        """Retourne un badge coloré HTML selon le niveau de confiance."""
        colors = {
            "Élevée": "#2e7d32",
            "Moyenne": "#f9a825",
            "Faible": "#c62828",
        }
        color = colors.get(level, "#757575")
        return (
            f'<span style="background-color:{color}; color:white; padding:4px 10px; '
            f'border-radius:12px; font-size:13px;">Confiance : {level}</span>'
        )

    @staticmethod
    def format_form_string(form_string: str) -> str:
        """Affiche la forme récente sous forme de pastilles colorées."""
        colors = {"V": "#2e7d32", "N": "#f9a825", "D": "#c62828"}
        badges = ""
        for letter in form_string:
            color = colors.get(letter, "#757575")
            badges += (
                f'<span style="background-color:{color}; color:white; '
                f'padding:2px 8px; margin-right:3px; border-radius:4px; '
                f'font-size:12px; font-weight:bold;">{letter}</span>'
            )
        return badges or "<em>Données insuffisantes</em>"


# ==============================================================================
# 8. LOGIQUE D'ORCHESTRATION (relie API-Football + moteur + Gemini)
# ==============================================================================

class MatchAnalyzer:
    """
    Orchestrateur principal : va chercher les données, calcule la prédiction,
    puis prépare tout ce dont l'interface a besoin pour l'affichage.
    """

    def __init__(self):
        self.api_client = ApiFootballClient()
        self.engine = PredictionEngine(self.api_client)
        self.gemini = GeminiService()

    def analyze_by_team_names(
        self, team1_name: str, team2_name: str
    ) -> PredictionResult:
        """Analyse un match à partir des noms d'équipes saisis par l'utilisateur."""
        fixture_raw = self.api_client.search_fixture_by_teams(team1_name, team2_name)
        if fixture_raw is None:
            raise ApiFootballError(
                f"Aucun match à venir trouvé entre « {team1_name} » et « {team2_name} ». "
                "Vérifie l'orthographe des noms d'équipes."
            )
        return self._analyze_fixture(fixture_raw)

    def analyze_by_fixture_id(self, fixture_id: int) -> PredictionResult:
        """Analyse un match à partir de son ID API-Football."""
        fixture_raw = self.api_client.get_fixture_by_id(fixture_id)
        if fixture_raw is None:
            raise ApiFootballError(f"Aucun match trouvé avec l'ID {fixture_id}.")
        return self._analyze_fixture(fixture_raw)

    def _analyze_fixture(self, fixture_raw: Dict[str, Any]) -> PredictionResult:
        """Construit la prédiction complète à partir des données brutes d'un match."""
        fixture = self._parse_fixture(fixture_raw)

        home_form = self.engine.build_team_form(
            fixture.home_team.id, fixture.home_team.name
        )
        away_form = self.engine.build_team_form(
            fixture.away_team.id, fixture.away_team.name
        )
        h2h = self.engine.build_h2h_record(fixture.home_team.id, fixture.away_team.id)

        try:
            odds = self.engine.extract_best_odds(fixture.id)
        except ApiFootballError as exc:
            logger.warning("Cotes indisponibles : %s", exc)
            odds = None

        prediction = self.engine.compute_prediction(
            fixture, home_form, away_form, h2h, odds
        )
        return prediction

    @staticmethod
    def _parse_fixture(raw: Dict[str, Any]) -> FixtureInfo:
        """Transforme la réponse brute de l'API en objet FixtureInfo."""
        fixture_data = raw["fixture"]
        league_data = raw["league"]
        teams_data = raw["teams"]
        goals_data = raw.get("goals", {})

        home_team = TeamInfo(
            id=teams_data["home"]["id"],
            name=teams_data["home"]["name"],
            logo_url=teams_data["home"].get("logo", ""),
        )
        away_team = TeamInfo(
            id=teams_data["away"]["id"],
            name=teams_data["away"]["name"],
            logo_url=teams_data["away"].get("logo", ""),
        )

        return FixtureInfo(
            id=fixture_data["id"],
            date=fixture_data.get("date", ""),
            league_name=league_data.get("name", ""),
            league_country=league_data.get("country", ""),
            home_team=home_team,
            away_team=away_team,
            status_short=fixture_data.get("status", {}).get("short", ""),
            home_score=goals_data.get("home"),
            away_score=goals_data.get("away"),
            venue=fixture_data.get("venue", {}).get("name", "") or "",
        )


# ==============================================================================
# 9. INTERFACE STREAMLIT
# ==============================================================================

def configure_page():
    """Configure les paramètres généraux de la page Streamlit."""
    st.set_page_config(
        page_title=Config.APP_NAME,
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_custom_css():
    """Injecte du CSS personnalisé pour une interface plus professionnelle."""
    st.markdown(
        """
        <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 0;
        }
        .sub-header {
            color: #666;
            font-size: 1rem;
            margin-top: 0;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 16px;
            border: 1px solid #e9ecef;
        }
        .stat-box {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 14px;
            border: 1px solid #eee;
            margin-bottom: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> Dict[str, Any]:
    """Affiche la barre latérale avec les options de configuration et de recherche."""
    with st.sidebar:
        st.markdown(f"### ⚽ {Config.APP_NAME}")
        st.caption(f"Version {Config.APP_VERSION}")
        st.divider()

        st.markdown("#### 🔍 Rechercher un match")
        search_mode = st.radio(
            "Mode de recherche",
            options=["Par noms d'équipes", "Par ID de match"],
            index=0,
        )

        team1_name = ""
        team2_name = ""
        fixture_id = None

        if search_mode == "Par noms d'équipes":
            team1_name = st.text_input("Équipe à domicile", placeholder="ex : Paris Saint Germain")
            team2_name = st.text_input("Équipe à l'extérieur", placeholder="ex : Marseille")
        else:
            fixture_id = st.number_input("ID du match (API-Football)", min_value=1, step=1)

        analyze_clicked = st.button("🔎 Analyser le match", use_container_width=True, type="primary")

        st.divider()
        st.markdown("#### ⚙️ État des services")

        api_key_ok = bool(Config.api_football_key())
        gemini_key_ok = bool(Config.gemini_api_key())

        st.markdown(
            f"- API-Football : {'✅ Configurée' if api_key_ok else '❌ Clé manquante'}"
        )
        st.markdown(
            f"- Gemini : {'✅ Configurée' if gemini_key_ok else '⚠️ Non configurée (résumé simplifié utilisé)'}"
        )
        st.markdown(
            f"- Audio (gTTS) : {'✅ Disponible' if GTTS_AVAILABLE else '❌ Non installé'}"
        )

        if not api_key_ok:
            st.warning(
                "Configure `API_FOOTBALL_KEY` dans les variables d'environnement "
                "ou dans `st.secrets` pour activer l'analyse."
            )

        return {
            "search_mode": search_mode,
            "team1_name": team1_name,
            "team2_name": team2_name,
            "fixture_id": int(fixture_id) if fixture_id else None,
            "analyze_clicked": analyze_clicked,
        }


def render_header():
    """Affiche l'en-tête principal de l'application."""
    st.markdown(f'<p class="main-header">⚽ {Config.APP_NAME}</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Analyse professionnelle de matchs basée sur des données réelles</p>',
        unsafe_allow_html=True,
    )


def render_match_header(prediction: PredictionResult):
    """Affiche l'en-tête du match analysé (équipes, compétition, date)."""
    fixture = prediction.fixture
    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.markdown(f"### 🏠 {fixture.home_team.name}")
    with col2:
        st.markdown("<h3 style='text-align:center;'>VS</h3>", unsafe_allow_html=True)
        try:
            match_date = dt.datetime.fromisoformat(fixture.date.replace("Z", "+00:00"))
            st.caption(f"📅 {match_date.strftime('%d/%m/%Y %H:%M')}")
        except (ValueError, AttributeError):
            st.caption(f"📅 {fixture.date}")
    with col3:
        st.markdown(f"### 🚌 {fixture.away_team.name}")

    st.caption(f"🏆 {fixture.league_name} ({fixture.league_country})")
    if fixture.venue:
        st.caption(f"📍 {fixture.venue}")

    st.markdown(DisplayFormatter.confidence_badge(prediction.confidence_level), unsafe_allow_html=True)
    st.markdown("---")


def render_probabilities_section(prediction: PredictionResult):
    """Affiche la section des probabilités 1X2."""
    st.markdown("#### 📊 Probabilités du résultat")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            DisplayFormatter.format_percentage_bar(
                f"Victoire {prediction.fixture.home_team.name}",
                prediction.prob_home_win,
                "#2e7d32",
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            DisplayFormatter.format_percentage_bar(
                "Match nul", prediction.prob_draw, "#f9a825"
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            DisplayFormatter.format_percentage_bar(
                f"Victoire {prediction.fixture.away_team.name}",
                prediction.prob_away_win,
                "#1565c0",
            ),
            unsafe_allow_html=True,
        )


def render_goals_section(prediction: PredictionResult):
    """Affiche la section des buts attendus et marchés de buts."""
    st.markdown("#### ⚽ Buts attendus")
    col1, col2, col3 = st.columns(3)

    col1.metric(f"Buts attendus — {prediction.fixture.home_team.name}", prediction.expected_goals_home)
    col2.metric(f"Buts attendus — {prediction.fixture.away_team.name}", prediction.expected_goals_away)
    col3.metric("Total attendu", prediction.expected_total_goals)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            DisplayFormatter.format_percentage_bar(
                "Les deux équipes marquent (BTTS)", prediction.prob_btts, "#6a1b9a"
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            DisplayFormatter.format_percentage_bar(
                "Plus de 2.5 buts", prediction.prob_over_2_5, "#00838f"
            ),
            unsafe_allow_html=True,
        )


def render_form_section(prediction: PredictionResult):
    """Affiche la forme récente des deux équipes."""
    st.markdown("#### 📈 Forme récente")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{prediction.home_form.team_name}**")
        st.markdown(
            DisplayFormatter.format_form_string(prediction.home_form.form_string),
            unsafe_allow_html=True,
        )
        st.caption(
            f"{prediction.home_form.wins}V • {prediction.home_form.draws}N • "
            f"{prediction.home_form.losses}D — "
            f"{prediction.home_form.avg_goals_scored} buts marqués/match, "
            f"{prediction.home_form.avg_goals_conceded} encaissés/match"
        )

    with col2:
        st.markdown(f"**{prediction.away_form.team_name}**")
        st.markdown(
            DisplayFormatter.format_form_string(prediction.away_form.form_string),
            unsafe_allow_html=True,
        )
        st.caption(
            f"{prediction.away_form.wins}V • {prediction.away_form.draws}N • "
            f"{prediction.away_form.losses}D — "
            f"{prediction.away_form.avg_goals_scored} buts marqués/match, "
            f"{prediction.away_form.avg_goals_conceded} encaissés/match"
        )


def render_h2h_section(prediction: PredictionResult):
    """Affiche l'historique des confrontations directes."""
    h2h = prediction.h2h
    st.markdown("#### 🤝 Confrontations directes (H2H)")

    if h2h.total_matches == 0:
        st.info("Aucune confrontation directe récente trouvée entre ces deux équipes.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric(f"Victoires {prediction.fixture.home_team.name}", h2h.team1_wins)
    col2.metric("Nuls", h2h.draws)
    col3.metric(f"Victoires {prediction.fixture.away_team.name}", h2h.team2_wins)

    st.caption(
        f"Moyenne de {h2h.avg_total_goals} buts par match • "
        f"BTTS dans {h2h.btts_rate}% des cas • "
        f"Plus de 2.5 buts dans {h2h.over_2_5_rate}% des cas"
    )

    with st.expander("Voir les derniers résultats"):
        for match_result in h2h.recent_results:
            st.text(f"• {match_result}")


def render_odds_section(prediction: PredictionResult):
    """Affiche les cotes disponibles et une éventuelle value bet."""
    st.markdown("#### 💰 Cotes du marché")

    if prediction.odds is None:
        st.info("Aucune cote disponible pour ce match pour le moment.")
        return

    odds = prediction.odds
    st.caption(f"Source : {odds.bookmaker}")

    col1, col2, col3 = st.columns(3)
    col1.metric("1 (Domicile)", odds.home_win or "N/A")
    col2.metric("N (Nul)", odds.draw or "N/A")
    col3.metric("2 (Extérieur)", odds.away_win or "N/A")

    if odds.over_2_5 or odds.under_2_5:
        col1, col2 = st.columns(2)
        col1.metric("Plus de 2.5 buts", odds.over_2_5 or "N/A")
        col2.metric("Moins de 2.5 buts", odds.under_2_5 or "N/A")

    if prediction.value_bet_detected:
        st.success(f"💎 {prediction.value_bet_explanation}")


def render_key_factors_section(prediction: PredictionResult):
    """Affiche les facteurs clés identifiés par le moteur de prédiction."""
    st.markdown("#### 🔑 Facteurs clés")
    for factor in prediction.key_factors:
        st.markdown(f"- {factor}")

    st.markdown("---")
    st.markdown(f"**🎯 Pari recommandé par l'analyse statistique :** {prediction.recommended_bet}")


def render_summary_section(prediction: PredictionResult, gemini_service: GeminiService):
    """Affiche le résumé rédactionnel généré (Gemini ou fallback) et l'audio."""
    st.markdown("#### 📝 Résumé de l'analyse")

    cache_key = f"summary_{prediction.fixture.id}"
    if cache_key not in st.session_state:
        with st.spinner("Génération du résumé en cours..."):
            st.session_state[cache_key] = gemini_service.generate_match_summary(prediction)

    summary_text = st.session_state[cache_key]
    st.markdown(summary_text)

    if not gemini_service.is_available:
        st.caption(
            "ℹ️ Résumé généré sans Gemini (clé API non configurée). "
            "Configure GEMINI_API_KEY pour un résumé rédigé par IA."
        )

    if AudioService.is_available():
        audio_key = f"audio_{prediction.fixture.id}"
        if st.button("🔊 Générer le résumé audio (français)"):
            with st.spinner("Génération de l'audio..."):
                try:
                    audio_bytes = AudioService.generate_audio_bytes(summary_text)
                    st.session_state[audio_key] = audio_bytes
                except AudioServiceError as exc:
                    st.error(str(exc))

        if audio_key in st.session_state:
            st.audio(st.session_state[audio_key], format="audio/mp3")
    else:
        st.caption("ℹ️ Installe `gtts` pour activer le résumé audio.")


def render_disclaimer():
    """Affiche l'avertissement légal / responsable en bas de page."""
    st.markdown("---")
    st.caption(
        "⚠️ **Avertissement** : Cette application fournit une analyse statistique "
        "à titre informatif uniquement. Elle ne constitue en aucun cas une garantie "
        "de résultat. Les paris sportifs comportent des risques financiers. "
        "Jouez de manière responsable."
    )


def render_empty_state():
    """Affiche un état d'accueil quand aucune analyse n'a encore été lancée."""
    st.info(
        "👈 Utilise le panneau latéral pour rechercher un match par noms d'équipes "
        "ou par ID de match API-Football, puis clique sur **Analyser le match**."
    )

    with st.expander("ℹ️ Comment configurer l'application"):
        st.markdown(
            """
            **1. Clé API-Football**
            Crée un compte sur [api-football.com](https://www.api-football.com/) ou
            via RapidAPI, puis configure la variable d'environnement
            `API_FOOTBALL_KEY` (ou ajoute-la dans `.streamlit/secrets.toml`).

            **2. Clé Gemini (optionnelle)**
            Crée une clé sur [Google AI Studio](https://aistudio.google.com/)
            et configure `GEMINI_API_KEY` pour activer les résumés rédigés par IA.
            Sans cette clé, un résumé simplifié est généré automatiquement.

            **3. Installation**
            ```bash
            pip install -r requirements.txt
            streamlit run betscope_stats.py
            ```
            """
        )


def render_requirements_file_hint():
    """Rappelle le contenu attendu du fichier requirements.txt."""
    with st.expander("📦 Contenu recommandé de requirements.txt"):
        st.code(
            "streamlit\n"
            "requests\n"
            "google-genai\n"
            "gtts\n",
            language="text",
        )


# ==============================================================================
# 10. POINT D'ENTRÉE PRINCIPAL
# ==============================================================================

def run_analysis(analyzer: MatchAnalyzer, sidebar_state: Dict[str, Any]) -> Optional[PredictionResult]:
    """Exécute l'analyse selon le mode choisi dans la barre latérale."""
    try:
        if sidebar_state["search_mode"] == "Par noms d'équipes":
            team1 = sidebar_state["team1_name"].strip()
            team2 = sidebar_state["team2_name"].strip()
            if not team1 or not team2:
                st.warning("Merci de renseigner les deux noms d'équipes.")
                return None
            with st.spinner(f"Recherche du match {team1} vs {team2}..."):
                return analyzer.analyze_by_team_names(team1, team2)
        else:
            fixture_id = sidebar_state["fixture_id"]
            if not fixture_id:
                st.warning("Merci de renseigner un ID de match valide.")
                return None
            with st.spinner(f"Recherche du match #{fixture_id}..."):
                return analyzer.analyze_by_fixture_id(fixture_id)

    except ApiFootballError as exc:
        st.error(f"❌ Erreur API-Football : {exc}")
        return None
    except Exception as exc:
        logger.exception("Erreur inattendue lors de l'analyse")
        st.error(f"❌ Erreur inattendue : {exc}")
        return None


def render_prediction_result(prediction: PredictionResult, gemini_service: GeminiService):
    """Affiche l'intégralité du résultat d'analyse pour un match."""
    render_match_header(prediction)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Probabilités", "📈 Forme & H2H", "💰 Cotes", "🔑 Facteurs clés", "📝 Résumé"]
    )

    with tab1:
        render_probabilities_section(prediction)
        st.markdown("---")
        render_goals_section(prediction)

    with tab2:
        render_form_section(prediction)
        st.markdown("---")
        render_h2h_section(prediction)

    with tab3:
        render_odds_section(prediction)

    with tab4:
        render_key_factors_section(prediction)

    with tab5:
        render_summary_section(prediction, gemini_service)

    render_disclaimer()


def main():
    """Point d'entrée principal de l'application Streamlit."""
    configure_page()
    render_custom_css()
    render_header()

    sidebar_state = render_sidebar()

    analyzer = MatchAnalyzer()

    if sidebar_state["analyze_clicked"]:
        if not Config.api_football_key():
            st.error(
                "❌ La clé API-Football n'est pas configurée. "
                "Ajoute `API_FOOTBALL_KEY` dans tes variables d'environnement "
                "ou dans `.streamlit/secrets.toml`."
            )
        else:
            prediction = run_analysis(analyzer, sidebar_state)
            if prediction is not None:
                st.session_state["last_prediction"] = prediction

    if "last_prediction" in st.session_state:
        render_prediction_result(st.session_state["last_prediction"], analyzer.gemini)
    else:
        render_empty_state()
        render_requirements_file_hint()


if __name__ == "__main__":
    main()
