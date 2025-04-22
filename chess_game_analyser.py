"""
chess_game_analyser.py

This module provides a `ChessGame` class for analyzing chess games
using the python-chess library. It supports extracting metadata,
analyzing moves, and identifying en passant opportunities.

Classes:
    ChessGame: A utility class for analyzing chess games and
    extracting information.

Key Technical Terms:
    - En passant: A special pawn capture that can occur when a pawn
      moves two squares forward from its starting position and lands
      beside an opponent's pawn. Only on the next turn, the opponent
      pawn has the opportunity to en passant, where the pawn can be
      captured in passing as if it had only moved one square.
    - Halfmove: A turn made by either white or black, since one move
      consists of a turn by each player. 
    - PGN (Portable Game Notation): A text-based format for recording
      chess games, including moves and metadata.
    - FEN (Forsyth-Edwards Notation): A standard notation for
      describing a chessboard position. It consists of six fields
      separated by spaces:
        1. Piece placement
        2. Active color (white or black to move)
        3. Castling availability
        4. En passant target square
        5. Halfmove clock
        6. Fullmove number
"""


from io import StringIO

import chess
import chess.pgn


# Chess Variants
HORDE_INITIAL_FEN = 'rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP w kq - 0 1'
RACING_KINGS_INITIAL_FEN = '8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1'

# 4th field of FEN is the en passant target square
TARGET_SQUARE_FIELD = 4
# 4th field of '-' in FEN means no en passant possible in position
TARGET_SQUARE_EMPTY = '-'

WHITE = 'white'
BLACK = 'black'


class ChessGame:
    """Utility class for extracting information from a chess game."""
    def __init__(self, pgn_string, username):
        """Initialise the ChessGame object.

        Args:
          pgn_string (str): The PGN string representing the game.
          username (str): The username of the player being analysed.

        Raises:
          ValueError: If the provided username is not a player in the
          game.
        """
        self._pgn = pgn_string

        # Convert the string into StringIO object and read the game
        self._game = chess.pgn.read_game(StringIO(self._pgn))

        # Get the game information
        self._game_info = self._game.headers

        if username == self.get_white_player():
            self._opponent = self.get_black_player()
        elif username == self.get_black_player():
            self._opponent = self.get_white_player()
        else:
            raise ValueError(f'{username} is not a player in this game!')
        # Externally get username we are processing stats for
        self._user = username

        # Create a virtual chessboard
        self._board = chess.Board()

        if 'FEN' in self._game_info:
            # Set initial position based on FEN tag if it exists
            # Accounts for Chess960 and From Position variants
            self._initial_fen = self._game_info['FEN']
        elif self.get_variant() == 'Horde':
            # Horde variant has different initial position
            self._initial_fen = HORDE_INITIAL_FEN
        elif self.get_variant() == 'Racing Kings':
            # Racing Kings variant has different initial position
            self._initial_fen = RACING_KINGS_INITIAL_FEN
        else:
            # Standard chess starting position
            self._initial_fen = chess.STARTING_FEN

    def get_user(self):
        """Return username of player being analysed."""
        return self._user
    
    def get_opponent(self):
        """Return opponent's username."""
        return self._opponent

    def get_event(self):
        """Return event name of the game."""
        return self._game_info['Event']

    def get_url(self):
        """Return base URL of the game."""
        return self._game_info['Site']
    
    def get_date(self):
        """Return date of the game."""
        return self._game_info['Date']
    
    def get_white_player(self):
        """Return username of white player."""
        return self._game_info['White']
    
    def get_black_player(self):
        """Return username of black player."""
        return self._game_info['Black']
    
    def get_user_color(self):
        """Return colour of user being analysed."""
        return WHITE if self._user == self.get_white_player() else BLACK
    
    def get_result(self):
        """Return result of the game."""
        return self._game_info['Result']
    
    def get_winner(self):
        """Return username of winner."""
        result = self.get_result()

        if result == '1-0':
            return self.get_white_player()
        elif result == '0-1':
            return self.get_black_player()
        else:
            return 'Draw'
    
    def get_variant(self):
        """Return name of chess variant."""
        return self._game_info['Variant']
    
    def get_en_passant_urls(self):
        """Get URLs for the en passant opportunities in the game.

        Identifies all en passant opportunities in the game and
        categorises them as 'accepted' or 'declined' based on whether
        the user captured the pawn.

        Returns:
          dict: A dictionary with two keys:
            - 'accepted': A set of URLs where en passant was accepted.
            - 'declined': A set of URLS where en passant was declined.
        """
        en_passant_urls = {'accepted': set(), 'declined': set()}

        game_url = self.get_url()
        user_color = self.get_user_color()
        # Appends colour to base game URL
        # Determines which board perspective will load
        url = f'{game_url}/{user_color}'

        self._board.set_fen(self._initial_fen)
        opportunity = False

        for halfmove_num, move in enumerate(self._game.mainline_moves(), start=1):
            if opportunity:
                if self._board.is_en_passant(move):
                    en_passant_urls['accepted'].add(move_url)
                else:
                    en_passant_urls['declined'].add(move_url)

                opportunity = False
            
            try:
                self._board.push(move)
            except AssertionError:
                # Handle variants not supported by 'chess' module ('Atomic')
                break

            fen = self._board.fen()
            target_square = fen.split()[TARGET_SQUARE_FIELD - 1]

            # En passant not possible
            if target_square == TARGET_SQUARE_EMPTY:
                continue

            # En passant possible but for opponent
            if user_color == WHITE and halfmove_num % 2 == 1:
                continue
            if user_color == BLACK and halfmove_num % 2 == 0:
                continue

            # User has opportunity to en passant on next halfmove
            opportunity = True
            # Appends the halfmove number to URL
            # Loads the game at that position
            move_url = f'{url}#{halfmove_num}'

        return en_passant_urls