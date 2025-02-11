import sqlite3

class Database:
    def __init__(self, db='user_statistics.db'):
        self.conn = sqlite3.connect(db)
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
            gameType TEXT,
            accepted BOOLEAN,
            url TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )           
        ''')

        self.conn.commit()

    def insert_user_games_number(self, username, rated_games, casual_games):
        self.conn.execute('''
        INSERT OR REPLACE INTO users (username, ratedGames, casualGames)
        VALUES (?, ?, ?)
        ''', (username, rated_games, casual_games))
        self.conn.commit()

    def insert_user_stats(self, username, game_type, accepted_no, declined_no):
        self.conn.execute('''
        INSERT OR REPLACE INTO user_stats (username, gameType, acceptedNo, declinedNo)
        VALUES (?, ?, ?, ?)
        ''', (username, game_type, accepted_no, declined_no))
        self.conn.commit()

    def insert_user_url(self, username, game_type, accepted, url):
        self.conn.execute('''
        INSERT INTO user_urls (username, gameType, accepted, url)
        VALUES (?, ?, ?, ?)
        ''', (username, game_type, accepted, url))
        self.conn.commit()

    def get_user_games_number(self, username):
        cursor = self.conn.execute('''
        SELECT ratedGames, casualGames FROM users WHERE username = ?
        ''', (username,))
        return cursor.fetchone()

    def get_user_stats(self, username, game_type):
        cursor = self.conn.execute('''
        SELECT acceptedNo, declinedNo FROM user_stats WHERE username = ? AND gameType = ?
        ''', (username, game_type))
        return cursor.fetchone()

    def get_user_urls(self, username, game_type, accepted):
        cursor = self.conn.execute('''
        SELECT url FROM user_urls WHERE username = ? AND gameType = ? AND accepted = ?
        ''', (username, game_type, accepted))
        urls = cursor.fetchall()
        return [url[0] for url in urls]
    
    def user_exists(self, username):
        cursor = self.conn.execute('''
        SELECT 1 FROM users WHERE username = ?
        ''', (username,))
        return cursor.fetchone() is not None
    
    def percentage_leaderboard(self):
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

    def declined_leaderboard(self):
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