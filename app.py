import requests


def get_sportsdb_data(endpoint):
  # Utilisation de la clé de test gratuite '1' fournie par TheSportsDB
  api_key = '1'
  url = f'https://www.thesportsdb.com/api/v1/json/{api_key}/{endpoint}'

  try:
    response = requests.get(url, timeout=10)
    # Vérifie si la requête a réussi
    if response.status_code == 200:
      return response.json()
    else:
      print(f'Erreur de connexion API : Code {response.status_code}')
      return None
  except Exception as e:
    print(f"Erreur technique lors de la requête : {e}")
    return None


def analyser_matchs_00():
  print('--- RECHERCHE DES MATCHS EN COURS ---')

  # Exemple d'appel pour récupérer la liste des ligues ou des événements
  data = get_sportsdb_data('all_leagues.php')

  if data and 'leagues' in data:
    print('Connexion à TheSportsDB réussie avec succès !')
    # Ici, vous pouvez filtrer ou lister vos éléments pour votre application
    leagues = data['leagues']
    print(f'Nombre total de ligues disponibles : {len(leagues)}')
  else:
    print('Aucune donnée récupérée ou format de réponse invalide.')


if __name__ == '__main__':
  analyser_matchs_00()
