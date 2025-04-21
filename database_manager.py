import sqlite3


class Database:
    """Utility class for managing database CRUD."""
    def __init__(self, db_name='en_passant_stats.db'):
        """Initialise the database connection.

        Additionally, creates tables if they do not exist.

        Args:
          db_name (str): The name of the SQLite database file.
          Defaults to 'en_passant_stats.db'.
        """
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        """Create the neccessary tables if they do not already exist."""
        # Create users table
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            ratedGames INT,
            casualGames INT
        )           
        ''')

        # Create user_stats table
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS user_stats (
            username TEXT,
            gameType TEXT,
            acceptedNo INT,
            declinedNo INT,
            FOREIGN KEY (username) REFERENCES users(username),
            PRIMARY KEY (username, gameType)
        )           
        ''')

        # Create user_urls table
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS user_urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            opponent TEXT,
            gameType TEXT,
            accepted BOOLEAN,
            url TEXT UNIQUE,
            FOREIGN KEY (username) REFERENCES users(username)
        )           
        ''')

        self.conn.commit()

    def update_num_games(self, username, rated_games, casual_games):
        """Update user's total number of rated and casual games.

        Inserts new entry into database if user does not exist.

        Args:
          username (str): The username of the user.
          rated_games (int): The total number of rated games.
          casual_games (int): The total number of casual games.
        """
        self.conn.execute('''
        INSERT OR REPLACE INTO users (username, ratedGames, casualGames)
        VALUES (?, ?, ?)
        ''', (username, rated_games, casual_games))
        self.conn.commit()

    def update_stats(self, username, game_type, accepted_no, declined_no):
        """Update user's en passant statistics.

        Inserts entries into database if user does not exist.

        Args:
          username (str): The username of the user.
          game_type (str): The type of game ('rated' or 'casual').
          accepted_no (int): The number of en passants accepted.
          declined_no (int): The number of en passants declined.
        """
        self.conn.execute('''
        INSERT OR REPLACE INTO user_stats (username, gameType, acceptedNo, declinedNo)
        VALUES (?, ?, ?, ?)
        ''', (username, game_type, accepted_no, declined_no))
        self.conn.commit()

    def insert_url(self, username, opponent, game_type, accepted, url):
        """Insert a URL for an en passant opportunity into database.
        
        Args:
          username (str): The username of the user.
          opponent (str): The opponent's username.
          game_type (str): The type of game ('rated' or 'casual').
          accepted (bool): Whether the en passant opportunity was accepted.
          url (str): The URL of the game.
        """
        self.conn.execute('''
        INSERT INTO user_urls (username, opponent, gameType, accepted, url)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (url) DO NOTHING;
        ''', (username, opponent, game_type, accepted, url))
        self.conn.commit()

    def get_num_games(self, username):
        """Retrieve user's total number of rated and casual games.

        Args:
          username (str): The username of the user.

        Returns:
          tuple: A tuple containing:
            - int: The total number of rated games.
            - int: The total number of casual games.
        """
        cursor = self.conn.execute('''
        SELECT ratedGames, casualGames FROM users WHERE username = ?
        ''', (username,))
        return cursor.fetchone()

    def get_stats(self, username, game_type):
        """Retrieve the en passant statistics for a user.

        Args:
          username (str): The username of the user.
          game_type (str): The type of game ('rated' or 'casual').

        Returns:
          tuple: A tuple containing:
            - int: The number of en passants accepted.
            - int: The number of en passants declined.
        """
        cursor = self.conn.execute('''
        SELECT acceptedNo, declinedNo FROM user_stats WHERE username = ? AND gameType = ?
        ''', (username, game_type))
        return cursor.fetchone()

    def get_urls(self, username, game_type, accepted):
        """Retrieve the URLs for en passant opportunities for a user.

        Args:
          username (str): The username of the user.
          game_type (str): The type of game ('rated' or 'casual').
          accepted (bool): Whether en passant was accepted.

        Returns:
          list: A list of tuples, where each tuple contains:
            - str: The URL of the game.
            - str: The opponent's username.
        """
        cursor = self.conn.execute('''
        SELECT url, opponent FROM user_urls WHERE username = ? AND gameType = ? AND accepted = ?
        ''', (username, game_type, accepted))
        return cursor.fetchall()
    
    def user_exists(self, username):
        """Check if a user exists in the database.

        Args:
          username (str): The username of the user.

        Returns:
          bool: True if the user exists, False otherwise.
        """
        cursor = self.conn.execute('''
        SELECT 1 FROM users WHERE username = ?
        ''', (username,))
        return cursor.fetchone() is not None
    
    def get_percentage_leaderboard(self):
        """Retrieve the leaderboard sorted by acceptance %.

        Returns:
          list: A list of tuples, where each tuple contains:
            - str: The username.
            - int: The total number of en passant opportunities.
            - float: The percentage of en passant captures accepted.
        """
        cursor = self.conn.execute('''
            SELECT u.username,
            (SUM(s.acceptedNo) + SUM(s.declinedNo)) AS opportunities,
            (CAST(SUM(s.acceptedNo) AS FLOAT) / (SUM(s.acceptedNo) + SUM(s.declinedNo))) * 100 AS acceptedPercentage
            FROM user_stats s
            JOIN users u ON s.username = u.username
            GROUP BY u.username
            HAVING opportunities > 0
            ORDER BY acceptedPercentage;
        ''')
        return cursor.fetchall()

    def get_declined_leaderboard(self):
        """Retrieve the leaderboard sorted by the total declines.

        Returns:
          list: A list of tuples, where each tuple contains:
            - str: The username.
            - int: The total number of games played.
            - int: The total number of en passant captures declined.
        """
        cursor = self.conn.execute('''
            SELECT u.username,
            (u.ratedGames + u.casualGames) AS totalGames,
            SUM(s.declinedNo) AS totalDeclined
            FROM users u
            JOIN user_stats s ON u.username = s.username
            GROUP BY u.username
            ORDER BY totalDeclined DESC;
        ''')
        return cursor.fetchall()

    def close(self):
        """Close the database connection."""
        self.conn.close()