"""
chess_game_analyser.py

This module provides a `ChessGame` class for analyzing chess games
using the python-chess library. It supports extracting metadata,
analyzing moves, and identifying en passant opportunities.

Classes:
    ChessGame: A utility class for analyzing chess games and
    extracting information.

Key Technical Terms:
    - FEN (Forsyth-Edwards Notation): A standard notation for
      describing a chessboard position. It consists of six fields
      separated by spaces:
        1. Piece placement
        2. Active color (white or black to move)
        3. Castling availability
        4. En passant target square
        5. Halfmove clock
        6. Fullmove number
    - PGN (Portable Game Notation): A text-based format for recording
      chess games, including moves and metadata.
    - En passant: A special pawn capture that can occur when a pawn
      moves two squares forward from its starting position and lands
      beside an opponent's pawn.
"""


from io import StringIO

import chess
import chess.pgn


# Chess Variants
HORDE_INITIAL_FEN = 'rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP w kq - 0 1'
RACING_KINGS_INITIAL_FEN = '8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1'

# 4th field of FEN is the en passant target square
TARGET_SQUARE_FIELD = 4
# '-' as 4th field of FEN indicates no possible en passant in given position
TARGET_SQUARE_EMPTY = '-'

WHITE = 'white'
BLACK = 'black'


class ChessGame:
    """Utility class for extracting all information from a chess game and running analysis."""
    def __init__(self, pgn_string: str, username: str):
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

        # Set initial position based on FEN tag if it exists, to account for Chess960 and From Position variants, and accounts for varaints with different initial positions
        if 'FEN' in self._game_info:
            self._initial_fen = self._game_info['FEN']
        elif self.get_variant() == 'Horde':
            self._initial_fen = HORDE_INITIAL_FEN
        elif self.get_variant() == 'Racing Kings':
            self._initial_fen = RACING_KINGS_INITIAL_FEN
        else:
            self._initial_fen = chess.STARTING_FEN

    def get_user(self) -> str:
        return self._user
    
    def get_opponent(self) -> str:
        return self._opponent

    def get_event(self) -> str:
        return self._game_info['Event']

    def get_url(self) -> str:
        return self._game_info['Site']
    
    def get_date(self) -> str:
        return self._game_info['Date']
    
    def get_white_player(self) -> str:
        return self._game_info['White']
    
    def get_black_player(self) -> str:
        return self._game_info['Black']
    
    def get_user_color(self) -> str:
        return WHITE if self._user == self.get_white_player() else BLACK
    
    def get_result(self) -> str:
        return self._game_info['Result']
    
    def get_winner(self) -> str:
        result = self.get_result()

        if result == '1-0':
            return self.get_white_player()
        elif result == '0-1':
            return self.get_black_player()
        else:
            return 'Draw'
    
    def get_variant(self) -> str:
        return self._game_info['Variant']
    
    def get_en_passant_urls(self) -> tuple[list]:
        """Getting a dictionary containing the sets of URLs in one game where the user accepted or declined en passant (since there can be multiple en passant opportunities in one game)."""
        en_passant_urls = {'accepted': set(), 'declined': set()}

        game_url = self.get_url()
        user_color = self.get_user_color()
        # Appends to game URL to determine which board perspective (white or black) the game URL will load
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
                # Handle chess variants like 'Atomic' not supported by 'chess' module
                break

            fen = self._board.fen()
            # 4th field of FEN gives en passant target square if the move is possible else '-'
            target_square = fen.split()[TARGET_SQUARE_FIELD - 1]

            if target_square == TARGET_SQUARE_EMPTY:
                continue
            if user_color == WHITE and halfmove_num % 2 == 1:
                continue
            if user_color == BLACK and halfmove_num % 2 == 0:
                continue

            # User has opportunity to en passant on next halfmove
            opportunity = True
            # Appends the halfmove number to the game URL to load the game URL at that position
            move_url = f'{url}#{halfmove_num}'

        return en_passant_urls