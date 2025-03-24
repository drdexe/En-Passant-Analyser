from flask import Flask, request, render_template
from utils import *


app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username')

        rated_games_number, casual_games_number, rated_games_list, casual_games_list = retrieve_games(username)

        results = analyse_games(username, rated_games_list, casual_games_list)

        update_user_statistics(username, rated_games_number, casual_games_number, results)

        return render_template('results.html', username=username, results=results)
    
    return render_template('index.html')


@app.route('/leaderboards')
def leaderboards():
    percentage_results, declined_results = get_leaderboards()
    return render_template('leaderboards.html', percentage_results=percentage_results, declined_results=declined_results)


if __name__ == '__main__':
    app.run()