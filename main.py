import time
from flask import Flask, request, render_template, url_for
from database import Database
from game_parser import Game
from lichess_export import get_total_user_games, get_user_games_list

# Retrieve games of username and returns tuple of rated and casual games number and list
def retrieve_games(username):
    db = Database()
    rated_games_number = get_total_user_games(username, True)
    casual_games_number = get_total_user_games(username, False)

    # Retrieve all games if user not in database
    if not db.user_exists(username):
        rated_games_list = get_user_games_list(username, True)
        casual_games_list = get_user_games_list(username, False)
    
    # Retrieve only new games not in database if user exists to reduce API retrieval time
    else:
        old_rated_games_number, old_casual_games_number = db.get_user_games_number(username)
        rated_games_list = []
        casual_games_list = []

        # Retrieve new games
        if old_rated_games_number < rated_games_number:
            rated_games_list = get_user_games_list(username, True, rated_games_number - old_rated_games_number)

        if old_casual_games_number < casual_games_number:
            casual_games_list = get_user_games_list(username, False, casual_games_number - old_casual_games_number)

    db.close()
    # Returns updated games number and all games list if new user, but only new games list if existing user (empty if no new games)
    return rated_games_number, casual_games_number, rated_games_list, casual_games_list

# Analyse games of username and returns dictionary of statistics and URL lists, accepts new games list from retrieve_games
def analyse_games(username, rated_games_list, casual_games_list):
    db = Database()

    if not db.user_exists(username):
        # Initialise values if new user
        rated_games_number = len(rated_games_list)
        casual_games_number = len(casual_games_list)

        total_rated_enpassant_accepted = 0
        total_rated_enpassant_declined = 0
        total_rated_enpassant_accepted_url_list = []
        total_rated_enpassant_declined_url_list = []
        
        total_casual_enpassant_accepted = 0
        total_casual_enpassant_declined = 0
        total_casual_enpassant_accepted_url_list = []
        total_casual_enpassant_declined_url_list = []
    else:
        # Retrieve from user_statistics.db if user exists
        rated_games_number = db.get_user_games_number(username)[0] + len(rated_games_list)
        casual_games_number = db.get_user_games_number(username)[1] + len(casual_games_list)

        total_rated_enpassant_accepted = db.get_user_stats(username, 'rated')[0]
        total_rated_enpassant_declined = db.get_user_stats(username, 'rated')[1]
        total_rated_enpassant_accepted_url_list = db.get_user_urls(username, 'rated', True)
        total_rated_enpassant_declined_url_list = db.get_user_urls(username, 'rated', False)

        total_casual_enpassant_accepted = db.get_user_stats(username, 'casual')[0]
        total_casual_enpassant_declined = db.get_user_stats(username, 'casual')[1]
        total_casual_enpassant_accepted_url_list = db.get_user_urls(username, 'casual', True)
        total_casual_enpassant_declined_url_list = db.get_user_urls(username, 'casual', False)

    total_games_number = rated_games_number + casual_games_number

    # Iterate through rated games to get en passant statistics
    for pgn_string in rated_games_list:
        game = Game(pgn_string)

        possible_enpassant_list = game.get_possible_enpassant_list()
        # If no possible en passant moments in the game, skip to the next game
        if not possible_enpassant_list:
            continue

        user_enpassant_list = game.get_user_enpassant_list(username, possible_enpassant_list)
        enpassant_accepted_list = game.is_enpassant_accepted(user_enpassant_list)
        enpassant_move_url_lists = game.get_enpassant_move_url_lists(username, user_enpassant_list, enpassant_accepted_list)

        total_rated_enpassant_accepted += len(enpassant_move_url_lists[0])
        total_rated_enpassant_declined += len(enpassant_move_url_lists[1])
        total_rated_enpassant_accepted_url_list.extend(enpassant_move_url_lists[0])
        total_rated_enpassant_declined_url_list.extend(enpassant_move_url_lists[1])

        # Add new URLs to user_urls table
        for url in enpassant_move_url_lists[0]:
            db.insert_user_url(username, 'rated', True, url)
        for url in enpassant_move_url_lists[1]:
            db.insert_user_url(username, 'rated', False, url)

    # Iterate through casual games to get en passant statistics
    for pgn_string in casual_games_list:
        game = Game(pgn_string)

        possible_enpassant_list = game.get_possible_enpassant_list()
        # If no possible en passant moments in the game, skip to the next game
        if not possible_enpassant_list:
            continue

        user_enpassant_list = game.get_user_enpassant_list(username, possible_enpassant_list)
        enpassant_accepted_list = game.is_enpassant_accepted(user_enpassant_list)
        enpassant_move_url_lists = game.get_enpassant_move_url_lists(username, user_enpassant_list, enpassant_accepted_list)

        total_casual_enpassant_accepted += len(enpassant_move_url_lists[0])
        total_casual_enpassant_declined += len(enpassant_move_url_lists[1])
        total_casual_enpassant_accepted_url_list.extend(enpassant_move_url_lists[0])
        total_casual_enpassant_declined_url_list.extend(enpassant_move_url_lists[1])

        # Add new URLs to user_urls table
        for url in enpassant_move_url_lists[0]:
            db.insert_user_url(username, 'casual', True, url)
        for url in enpassant_move_url_lists[1]:
            db.insert_user_url(username, 'casual', False, url)

    # Insert updated en passant statistics to user_stats table
    db.insert_user_stats(username, 'rated', total_rated_enpassant_accepted, total_rated_enpassant_declined)
    db.insert_user_stats(username, 'casual', total_casual_enpassant_accepted, total_casual_enpassant_declined)

    # Calculate rated en passant statistics
    total_rated_enpassant = total_rated_enpassant_accepted + total_rated_enpassant_declined
    rated_enpassant_accepted_percentage = total_rated_enpassant_accepted / total_rated_enpassant * 100 if total_rated_enpassant != 0 else 0

    # Calculate casual en passant statistics
    total_casual_enpassant = total_casual_enpassant_accepted + total_casual_enpassant_declined
    casual_enpassant_accepted_percentage = total_casual_enpassant_accepted / total_casual_enpassant * 100 if total_casual_enpassant != 0 else 0

    # Calculate total en passant statistics
    total_enpassant_accepted = total_rated_enpassant_accepted + total_casual_enpassant_accepted
    total_enpassant_declined = total_rated_enpassant_declined + total_casual_enpassant_declined
    total_enpassant = total_rated_enpassant + total_casual_enpassant
    total_enpassant_accepted_percentage = total_enpassant_accepted / total_enpassant * 100 if total_enpassant != 0 else 0

    results = {
        'ratedGames': rated_games_number,
        'casualGames': casual_games_number,
        'totalGames': total_games_number,
        'ratedAccepted': total_rated_enpassant_accepted,
        'ratedDeclined': total_rated_enpassant_declined,
        'ratedOpportunities': total_rated_enpassant,
        'ratedPercentage': round(rated_enpassant_accepted_percentage, 2),
        'casualAccepted': total_casual_enpassant_accepted,
        'casualDeclined': total_casual_enpassant_declined,
        'casualOpportunities': total_casual_enpassant,
        'casualPercentage': round(casual_enpassant_accepted_percentage, 2),
        'totalAccepted': total_enpassant_accepted,
        'totalDeclined': total_enpassant_declined,
        'totalOpportunities': total_enpassant,
        'totalPercentage': round(total_enpassant_accepted_percentage, 2),
        'ratedAcceptedList': total_rated_enpassant_accepted_url_list,
        'ratedDeclinedList': total_rated_enpassant_declined_url_list,
        'casualAcceptedList': total_casual_enpassant_accepted_url_list,
        'casualDeclinedList': total_casual_enpassant_declined_url_list
    }

    db.close()
    return results

def insert_user(username, rated_games_number, casual_games_number):
    db = Database()
    db.insert_user_games_number(username, rated_games_number, casual_games_number)
    db.close()

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username')

        start_time = time.time()

        rated_games_number, casual_games_number, rated_games_list, casual_games_list = retrieve_games(username)

        # Record time taken to retrieve games from lichess.org api using lichess_export.py
        retrieval_time = time.time()
        print(f'Retrieval time: {retrieval_time - start_time} seconds')

        results = analyse_games(username, rated_games_list, casual_games_list)

        # Record time taken to process game lists using game_parser.py
        processing_time = time.time()
        print(f'Processing time: {processing_time - retrieval_time} seconds')

        insert_user(username, rated_games_number, casual_games_number)

        return render_template('results.html', username = username, results = results)
    
    return render_template('index.html')

@app.route('/leaderboards')
def leaderboards():
    db = Database()

    percentage_results = db.percentage_leaderboard()
    declined_results = db.declined_leaderboard()

    db.close()
    return render_template('leaderboards.html', percentage_results = percentage_results, declined_results = declined_results)

if __name__ == '__main__':
    app.run()