import requests


# Default 3 newlines between PGN strings of games from lichess API
PGN_DELIMITER = '\n' * 3


class LichessErrorHandler:
    """Utility class for handling Lichess API HTTP erros."""
    class APIError(Exception):
        """Base exception for Lichess API errors."""
        pass

    class UserNotFoundError(APIError):
        """Exception raised when the username is invalid (404)."""
        pass

    class ServerError(APIError):
        """Exception raised for server-side errors (500+)."""
        pass

    @staticmethod
    def handle(username: str, status_code: int) -> None:
        if status_code == 404:
            raise LichessErrorHandler.UserNotFoundError(
                f'404: User {username} not found!'
            )
        elif 500 <= status_code < 600:
            raise LichessErrorHandler.ServerError(
                f'{status_code}: Lichess server error!'
            )
        else:
            raise LichessErrorHandler.APIError(
                f'{status_code}: Failed to retrieve games for {username}!'
            )


def get_user_info(username: str) -> tuple:
    """Retrieve case-sensitive username, total number of rated, and casual games of user which is >= than length of user_games_list due to missing games in lichess.org database in certain time period. Returns tuple."""
    url = f'https://lichess.org/api/user/{username}'
    response = requests.get(url)

    # Status code 200 is OK successful response
    if response.status_code == 200:
        user_data = response.json()
        
        try:
            user_games_data = user_data['count']
        except KeyError:
            # Some invalid usernames still get 200 status code
            LichessErrorHandler.handle(username, 404);
        
        return (
            user_data['username'],
            user_games_data['rated'],
            user_games_data['all'] - user_games_data['rated']
        )

    LichessErrorHandler.handle(username, response.status_code)


def get_user_games(username: str, is_rated: bool, num_new_games: int = None) -> list[str]:
    """Retrieving all rated or casual games of a user by default, or specify only latest new_games_count number from lichess.org and returning as a list of PGN strings."""
    url = f'https://lichess.org/api/games/user/{username}?rated='

    url += 'true' if is_rated else 'false'

    if num_new_games is not None:
        url += f'&max={num_new_games}'

    response = requests.get(url)

    # Status code 200 is OK successful response
    if response.status_code == 200:
        # Split pgn_strings by triple newlines and filter out empty strings
        return [
            game for game in response.text.split(PGN_DELIMITER) if game.strip()
        ][::-1]  # Returns games from oldest to newest
    
    LichessErrorHandler.handle(username, response.status_code)