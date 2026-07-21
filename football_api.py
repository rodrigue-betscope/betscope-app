import requests
from config import SPORT_API_KEY


BASE_URL = "https://v3.football.api-sports.io"


HEADERS = {
    "x-apisports-key": SPORT_API_KEY
}



def rechercher_equipe(nom):

    url = f"{BASE_URL}/teams"

    params = {
        "search": nom
    }

    r = requests.get(
        url,
        headers=HEADERS,
        params=params
    )

    return r.json()



def derniers_matchs(team_id):

    url = f"{BASE_URL}/fixtures"

    params = {
        "team": team_id,
        "last": 10
    }

    r = requests.get(
        url,
        headers=HEADERS,
        params=params
    )

    return r.json()



def blessures(team_id):

    url = f"{BASE_URL}/injuries"

    params = {
        "team": team_id
    }

    r = requests.get(
        url,
        headers=HEADERS,
        params=params
    )

    return r.json()



def h2h(team1,team2):

    url = f"{BASE_URL}/fixtures/headtohead"

    params = {
        "h2h": f"{team1}-{team2}",
        "last": 10
    }

    r = requests.get(
        url,
        headers=HEADERS,
        params=params
    )

    return r.json()
