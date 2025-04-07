import sqlite3


class Database:
    """Utility class for managing database creation, insertion, and selection."""
    def __init__(self, db_name='en_passant_stats.db'):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        # Creating users table
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            ratedGames INT,
            casualGames INT
        )           
        ''')

        # Creating user_stats table
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

        # Creating user_urls table
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
        self.conn.execute('''
        INSERT OR REPLACE INTO users (username, ratedGames, casualGames)
        VALUES (?, ?, ?)
        ''', (username, rated_games, casual_games))
        self.conn.commit()

    def update_stats(self, username, game_type, accepted_no, declined_no):
        self.conn.execute('''
        INSERT OR REPLACE INTO user_stats (username, gameType, acceptedNo, declinedNo)
        VALUES (?, ?, ?, ?)
        ''', (username, game_type, accepted_no, declined_no))
        self.conn.commit()

    def insert_url(self, username, opponent, game_type, accepted, url):
        self.conn.execute('''
        INSERT INTO user_urls (username, opponent, gameType, accepted, url)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (url) DO NOTHING;
        ''', (username, opponent, game_type, accepted, url))
        self.conn.commit()

    def get_num_games(self, username):
        cursor = self.conn.execute('''
        SELECT ratedGames, casualGames FROM users WHERE username = ?
        ''', (username,))
        return cursor.fetchone()

    def get_stats(self, username, game_type):
        cursor = self.conn.execute('''
        SELECT acceptedNo, declinedNo FROM user_stats WHERE username = ? AND gameType = ?
        ''', (username, game_type))
        return cursor.fetchone()

    def get_urls(self, username, game_type, accepted):
        cursor = self.conn.execute('''
        SELECT url, opponent FROM user_urls WHERE username = ? AND gameType = ? AND accepted = ?
        ''', (username, game_type, accepted))
        return cursor.fetchall()
    
    def user_exists(self, username):
        cursor = self.conn.execute('''
        SELECT 1 FROM users WHERE username = ?
        ''', (username,))
        return cursor.fetchone() is not None
    
    def get_percentage_leaderboard(self):
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
        self.conn.close()