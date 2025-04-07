from database_manager import Database
from chess_game_analyser import ChessGame
from lichess_api import get_user_games, get_user_info


def time_function(func):
    """Record and print time taken to run a function."""
    from time import time

    def wrapper(*args, **kwargs):
        start_time = time()
        return_value = func(*args, **kwargs)
        time_taken = time() - start_time
        function_name = func.__name__.replace('_', ' ')
        print(f"Time taken to {function_name}: {time_taken} seconds")
        return return_value

    return wrapper


@time_function
def retrieve_games(db_name, form_username):
    """Retrieve new games of case-insensitive username and returns tuple of case-sensitive username, rated and casual games number and list."""
    db = Database(db_name)
    # Retrieve case-sensitive username and number of games
    username, num_rated, num_casual = get_user_info(form_username)

    # Retrieve all games if user not in database
    if not db.user_exists(username):
        rated_list = get_user_games(username, is_rated=True)
        casual_list = get_user_games(username, is_rated=False)
    
    # Retrieve only new games not in database if user exists to reduce API retrieval time
    else:
        db_num_rated, db_num_casual = db.get_num_games(username)
        rated_list = []
        casual_list = []

        # Retrieve new games
        if db_num_rated < num_rated:
            rated_list = get_user_games(
                username, is_rated=True, num_new_games=num_rated-db_num_rated
            )

        if db_num_casual < num_casual:
            casual_list = get_user_games(
                username, is_rated=False, num_new_games=num_casual-db_num_casual
            )

    db.close()
    # Returns username with updated games number and all games list if new user, but only new games list if existing user (empty if no new games)
    return username, num_rated, num_casual, rated_list, casual_list


@time_function
def analyse_games(db_name, username, rated_list, casual_list):
    """Analyse games of username and returns dictionary of statistics and URL lists, accepts new games list from retrieve_games."""
    db = Database(db_name)

    # Initialise values to results, assuming new user
    results = {
        'ratedGames': len(rated_list),
        'casualGames': len(casual_list),
        'ratedAccepted': 0,
        'ratedDeclined': 0,
        'ratedAcceptedList': [],
        'ratedDeclinedList': [],
        'casualAccepted': 0,
        'casualDeclined': 0,
        'casualAcceptedList': [],
        'casualDeclinedList': []
    }

    if db.user_exists(username):
        # Retrieve from database if user exists and update results
        db_num_rated, db_num_casual = db.get_num_games(username)
        results['ratedGames'] += db_num_rated
        results['casualGames'] += db_num_casual

        for game_type in ['rated', 'casual']:
            (
                results[f'{game_type}Accepted'],
                results[f'{game_type}Declined']
            ) = db.get_stats(username, game_type)

            for accepted in [True, False]:
                decision = 'Accepted' if accepted else 'Declined'
                results[
                    f'{game_type}{decision}List'
                ] = db.get_urls(username, game_type, accepted)
    
    results['totalGames'] = results['ratedGames'] + results['casualGames']

    def update_results(games_list, game_type):
        """Helper function to update results dictionary for both rated and casual games."""
        # Iterate through games to get en passant statistics
        for pgn_string in games_list:
            game = ChessGame(pgn_string, username)

            en_passant_urls = game.get_en_passant_urls()

            opponent = game.get_opponent()

            for decision in ['accepted', 'declined']:
                key = f'{game_type}{decision.capitalize()}'

                results[key] += len(en_passant_urls[decision])

                for url in en_passant_urls[decision]:
                    # Store tuple of URL and opponent
                    results[f'{key}List'].append((url, opponent))

    update_results(rated_list, 'rated')
    update_results(casual_list, 'casual')

    # Calculate total en passant statistics and insert into results
    results.update({
        'ratedOpportunities': results['ratedAccepted'] + results['ratedDeclined'],
        'casualOpportunities': results['casualAccepted'] + results['casualDeclined'],
        'totalAccepted': results['ratedAccepted'] + results['casualAccepted'],
        'totalDeclined': results['ratedDeclined'] + results['casualDeclined']
    })
    results['totalOpportunities'] = results['totalAccepted'] + results['totalDeclined']
    
    def percentage(numerator, denominator):
        return round(numerator / denominator * 100, 2) if denominator != 0 else 0
    
    # Calculate percentages and insert into results
    results.update({
        'ratedPercentage': percentage(results['ratedAccepted'], results['ratedOpportunities']),
        'casualPercentage': percentage(results['casualAccepted'], results['casualOpportunities']),
        'totalPercentage': percentage(results['totalAccepted'], results['totalOpportunities'])
    })

    db.close()
    return results


@time_function
def update_database(db_name, username, num_rated, num_casual, results):
    """Handles all database insertion or update after retrieving and analysing games."""
    db = Database(db_name)

    # Add user by inserting actual number of games
    db.update_num_games(username, num_rated, num_casual)

    # Insert updated en passant statistics to user_stats table
    db.update_stats(username, 'rated', results['ratedAccepted'], results['ratedDeclined'])
    db.update_stats(username, 'casual', results['casualAccepted'], results['casualDeclined'])

    # Insert new URLs to user_urls table
    for url, opponent in results['ratedAcceptedList']:
        db.insert_url(username, opponent, 'rated', accepted=True, url=url)
    for url, opponent in results['ratedDeclinedList']:
        db.insert_url(username, opponent, 'rated', accepted=False, url=url)
    for url, opponent in results['casualAcceptedList']:
        db.insert_url(username, opponent, 'casual', accepted=True, url=url)
    for url, opponent in results['casualDeclinedList']:
        db.insert_url(username, opponent, 'casual', accepted=False, url=url)
        
    db.close()


@time_function
def get_leaderboards(db_name):
    """Queries database for sorted statistics across users."""
    db = Database(db_name)

    percentage_results = db.get_percentage_leaderboard()
    declined_results = db.get_declined_leaderboard()

    db.close()
    return percentage_results, declined_results