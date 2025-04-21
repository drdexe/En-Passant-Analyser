import requests


# Default 3 newlines between PGN strings of games from Lichess API
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
    def handle(username, status_code):
        """Handle Lichess API errors based on the HTTP status code.

        Args:
          username (str): The username for which the error occured.
          status_code (int) The HTTP status code returned.

        Raises:
          UserNotFoundError: If the status code is 404.
          ServerError: If the status code is 500-599.
          APIError: For all other non-successful status codes.
        """
        if status_code == 404:
            raise LichessErrorHandler.UserNotFoundError(
                f"404 User '{username}' not found!"
            )
        elif 500 <= status_code < 600:
            raise LichessErrorHandler.ServerError(
                f'{status_code} Lichess server error!'
            )
        else:
            raise LichessErrorHandler.APIError(
                f"{status_code} Failed to retrieve games for '{username}'!"
            )


def get_user_info(username):
    """Retrieve user information from the Lichess API.

    Fetches the case-sensitive username, total number of rated games,
    and total number of casual games for the specified user.
    This will be >= length of the games list retrieved subsequently
    due to missing games in the Lichess database during a certain
    time period. Handles cases where the username is invalid or
    the API response is incomplete.

    Args:
      username (str): The username to retrieve information for.

    Returns:
      tuple: A tuple containing:
        - str: The case-sensitive username.
        - int: The total number of rated games.
        - int: The total number of casual games.

    Raises:
      UserNotFoundError: If the username is invalid or not found.
      ServerError: If the Lichess server encounters an error.
      APIError: For other API-related errors.
    """
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


def get_user_games(username, is_rated, num_new_games=None):
    """Retrieve games for a user from the Lichess API.
    
    Fetches all rated or casual games for the specified user.
    Optionally, retrieves only the latest `num_new_games` games.
    Returns the games as a list of PGN strings.

    Args:
      username (str): The username to retrieve games for.
      is_rated (bool): Whether to retrieve rated games (`True`)
      or casual games (`False`).
      num_new_games (int, optional): The max number of latest games
      to retrieve. Defaults to `None`, which retrieves all games.

    Returns:
      list[str]: A list of PGN strings representing the games.

    Raises:
      UserNotFoundError: If the username is invalid or not found.
      ServerError: If the Lichess server encounters an error.
      APIError: For other API-related errors.
    """
    url = f'https://lichess.org/api/games/user/{username}?rated='

    url += 'true' if is_rated else 'false'

    if num_new_games is not None:
        url += f'&max={num_new_games}'

    response = requests.get(url)

    # Status code 200 is OK successful response
    if response.status_code == 200:
        # Split PGNs by triple newlines and filter out empty strings
        return [
            game for game in response.text.split(PGN_DELIMITER) if game.strip()
        ][::-1]  # Returns games from oldest to newest
    
    LichessErrorHandler.handle(username, response.status_code)