import argparse

from flask import Flask, request, render_template, redirect, url_for
from pathvalidate import is_valid_filename

from lichess_api import LichessErrorHandler
from utils import retrieve_games, analyse_games, update_database, get_leaderboards


def main():
    """Main entry point for the application."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the En Passant Analyser Flask app.')
    parser.add_argument(
        '--db',
        type=str,
        default='en_passant_stats.db',
        help='The name of the SQLite database file to use.'
    )
    db_name = parser.parse_args().db

    # Validate database name
    if not(db_name.endswith('.db') and is_valid_filename(db_name)):
        raise ValueError('Usage: python main.py [--db valid_filename.db]')
    
    # Create and run the Flask app
    app = create_app(db_name)
    app.run()


def create_app(db_name):
    """Create and configure the Flask app."""
    app = Flask(__name__)

    @app.route('/', methods=['GET', 'POST'])
    def index():
        """Handle the main page of the application.

        For GET requests, renders the index page with a form for the
        user to input their username.
        For POST requests, retrieves and analyses the user's games
        for Lichess, update their statistics in the database,
        and redirects to the results page for the user.

        Returns:
          Rendered HTML template for the index
          or a redirect to the results page.
        """
        if request.method == 'POST':
            form_username = request.form.get('username')

            # Check if username is blank
            if not form_username.strip():
                return render_template('index.html', error='Username cannot be blank!')
            
            # Redirect to results page after getting form username
            return redirect(url_for('results', username=form_username))
        
        return render_template('index.html')


    @app.route('/results/<username>')
    def results(username):
        """Handle the results page for a specific user.

        Retrieves the user's game data from lichess.org
        analyses en passant statistics and updates the database,
        then renders the results page.

        Returns:
          Rendered HTML template for the results page.
        """
        try:
            (
                username,
                num_rated,
                num_casual,
                rated_list,
                casual_list
            ) = retrieve_games(db_name, username)
        except (
            LichessErrorHandler.APIError,
            LichessErrorHandler.UserNotFoundError,
            LichessErrorHandler.ServerError
        ) as e:
            # If HTTP error, redirect back to index with error message
            return render_template('index.html', error=str(e))
            
        results = analyse_games(db_name, username, rated_list, casual_list)

        update_database(db_name, username, num_rated, num_casual, results)

        return render_template('results.html', username=username, results=results)


    @app.route('/leaderboards')
    def leaderboards():
        """Handle the leaderboards page for the application.

        Retrieves leaderboard data for en passant statistics from
        the database and renders leaderboards page.

        Returns:
          Rendered HTML template for the leaderboards page. 
        """
        percentage_results, declined_results = get_leaderboards(db_name)
        return render_template(
            'leaderboards.html',
            percentage_results=percentage_results,
            declined_results=declined_results
        )
    
    return app


if __name__ == '__main__':
    main()