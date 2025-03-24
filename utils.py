from database import Database
from game_parser import Game
from lichess_export import get_total_user_games, get_user_games_list


def time_function(func):
    """Record and print time taken to run a function"""
    from time import time

    def wrapper(*args, **kwargs):
        start_time = time()
        return_value = func(*args, **kwargs)
        time_taken = time() - start_time
        print(f"Time taken to {func.__name__.replace('_', ' ')}: {time_taken} seconds")
        return return_value

    return wrapper


@time_function
def retrieve_games(username):
    """Retrieve new games of username and returns tuple of rated and casual games number and list"""
    db = Database()
    rated_games_number = get_total_user_games(username, is_rated=True)
    casual_games_number = get_total_user_games(username, is_rated=False)

    # Retrieve all games if user not in database
    if not db.user_exists(username):
        rated_games_list = get_user_games_list(username, is_rated=True)
        casual_games_list = get_user_games_list(username, is_rated=False)
    
    # Retrieve only new games not in database if user exists to reduce API retrieval time
    else:
        old_rated_games_number, old_casual_games_number = db.get_user_games_number(username)
        rated_games_list = []
        casual_games_list = []

        # Retrieve new games
        if old_rated_games_number < rated_games_number:
            rated_games_list = get_user_games_list(username, is_rated=True, new_games_count=rated_games_number-old_rated_games_number)

        if old_casual_games_number < casual_games_number:
            casual_games_list = get_user_games_list(username, is_rated=False, new_games_count=casual_games_number-old_casual_games_number)

    db.close()
    # Returns updated games number and all games list if new user, but only new games list if existing user (empty if no new games)
    return rated_games_number, casual_games_number, rated_games_list, casual_games_list


@time_function
def analyse_games(username, rated_games_list, casual_games_list):
    """Analyse games of username and returns dictionary of statistics and URL lists, accepts new games list from retrieve_games"""
    db = Database()

    # Initialise values to results, assuming new user
    results = {
        'ratedGames': len(rated_games_list),
        'casualGames': len(casual_games_list),
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
        results.update({
            'ratedGames': db.get_user_games_number(username)[0] + results['ratedGames'],
            'casualGames': db.get_user_games_number(username)[1] + results['casualGames'],
            'ratedAccepted': db.get_user_stats(username, 'rated')[0],
            'ratedDeclined': db.get_user_stats(username, 'rated')[1],
            'ratedAcceptedList': db.get_user_urls(username, 'rated', accepted=True),
            'ratedDeclinedList': db.get_user_urls(username, 'rated', accepted=False),
            'casualAccepted': db.get_user_stats(username, 'casual')[0],
            'casualDeclined': db.get_user_stats(username, 'casual')[1],
            'casualAcceptedList': db.get_user_urls(username, 'casual', accepted=True),
            'casualDeclinedList': db.get_user_urls(username, 'casual', accepted=False)
        })
    
    results['totalGames'] = results['ratedGames'] + results['casualGames']

    def update_results(games_list, game_type):
        """Helper function to update results dictionary for both rated and casual games"""
        # Iterate through games to get en passant statistics
        for pgn_string in games_list:
            game = Game(pgn_string)

            possible_enpassant_list = game.get_possible_enpassant_list()
            # If no possible en passant moments in the game, skip to the next game
            if not possible_enpassant_list:
                continue

            user_enpassant_list = game.get_user_enpassant_list(username, possible_enpassant_list)
            enpassant_accepted_list = game.is_enpassant_accepted(user_enpassant_list)
            accepted_url_list, declined_url_list = game.get_enpassant_move_url_lists(username, user_enpassant_list, enpassant_accepted_list)

            results[game_type + 'Accepted'] += len(accepted_url_list)
            results[game_type + 'Declined'] += len(declined_url_list)
            results[game_type + 'AcceptedList'].extend(accepted_url_list)
            results[game_type + 'DeclinedList'].extend(declined_url_list)

    update_results(rated_games_list, 'rated')
    update_results(casual_games_list, 'casual')

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
def update_user_statistics(username, rated_games_number, casual_games_number, results):
    """Handles all database insertion or update after retrieving and analysing games"""
    db = Database()

    # Add user by inserting actual number of games
    db.insert_user_games_number(username, rated_games_number, casual_games_number)

    # Insert updated en passant statistics to user_stats table
    db.insert_user_stats(username, 'rated', results['ratedAccepted'], results['ratedDeclined'])
    db.insert_user_stats(username, 'casual', results['casualAccepted'], results['casualDeclined'])

    # Insert new URLs to user_urls table
    for url in results['ratedAcceptedList']:
        db.insert_user_url(username, 'rated', accepted=True, url=url)
    for url in results['ratedDeclinedList']:
        db.insert_user_url(username, 'rated', accepted=False, url=url)
    for url in results['casualAcceptedList']:
        db.insert_user_url(username, 'casual', accepted=True, url=url)
    for url in results['casualDeclinedList']:
        db.insert_user_url(username, 'casual', accepted=False, url=url)
        
    db.close()


@time_function
def get_leaderboards():
    """Queries database for sorted statistics across users"""
    db = Database()

    percentage_results = db.percentage_leaderboard()
    declined_results = db.declined_leaderboard()

    db.close()
    return percentage_results, declined_results