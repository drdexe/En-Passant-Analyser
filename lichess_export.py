import requests


def get_total_user_games(username: str, is_rated: bool) -> int:
    """Retrieve total number of rated or casual games of user which is >= than length of user_games_list due to missing games in lichess.org database in certain time period"""
    url = f'https://lichess.org/api/user/{username}'
    response = requests.get(url)

    # Status code 200 is OK successful response
    if response.status_code == 200:
        user_data = response.json()
        
        user_games_data = user_data['count']
        if is_rated:   
            return user_games_data['rated']
        else:
            return user_games_data['all'] - user_games_data['rated']
    else:
        raise Exception(f'Failed to retrieve total user games for {username}, status code: {response.status_code}')


def get_user_games_list(username: str, is_rated: bool, new_games_count: int = None) -> list[str]:
    """Retrieving all rated or casual games of a user by default, or specify only latest new_games_count number from lichess.org and returning as a list of PGN strings"""
    url = f'https://lichess.org/api/games/user/{username}?rated='

    url += 'true' if is_rated else 'false'

    if new_games_count is not None:
        url += f'&max={str(new_games_count)}'

    response = requests.get(url)

    # Status code 200 is OK successful response
    if response.status_code == 200:
        user_games_list = response.text.split('\n\n\n')
        user_games_list.pop()

        # Returns games from oldest to newest
        return user_games_list[::-1]
    else:
        raise Exception(f'Failed to retrieve user games list for {username}, status code: {response.status_code}')