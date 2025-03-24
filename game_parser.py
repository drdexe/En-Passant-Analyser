import chess
import chess.pgn
from io import StringIO


class Game:
    def __init__(self, pgn_string: str):
        self.pgn = pgn_string.strip()

        # Converting the string into StringIO object and reading the game
        self.game = chess.pgn.read_game(StringIO(self.pgn))

        # Getting the game information
        self.game_info = self.game.headers

        # Creating a virtual chessboard
        self.board = chess.Board()

        # Setting initial position based on FEN tag if it exists, to account for Chess960 and From Position variants, and accounts for varaints with different initial positions
        if 'FEN' in self.game_info:
            self.initial_fen = self.game_info['FEN']
        elif self.get_variant() == 'Horde':
            self.initial_fen = 'rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP w kq - 0 1'
        elif self.get_variant() == 'Racing Kings':
            self.initial_fen = '8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1'
        else:
            self.initial_fen = chess.STARTING_FEN

    def get_event(self) -> str:
        return self.game_info['Event']

    def get_url(self) -> str:
        return self.game_info['Site']
    
    def get_date(self) -> str:
        return self.game_info['Date']
    
    def get_white_player(self) -> str:
        return self.game_info['White']
    
    def get_black_player(self) -> str:
        return self.game_info['Black']
    
    def get_user_colour(self, username: str) -> str:
        if self.get_white_player() == username:
            return 'White'
        elif self.get_black_player() == username:
            return 'Black'
        else:
            return None
    
    def get_result(self) -> str:
        return self.game_info['Result']
    
    def get_winner(self) -> str:
        result = self.get_result()

        if result == '1-0':
            return self.get_white_player()
        elif result == '0-1':
            return self.get_black_player()
        else:
            return 'Draw'
    
    def get_variant(self) -> str:
        return self.game_info['Variant']

    def get_fen(self, halfmove_number: int) -> str:
        """Getting the FEN of the board after a certain number of halfmoves, where halfmove 0 is the initial position"""
        self.board.set_fen(self.initial_fen)

        for number, move in enumerate(self.game.mainline_moves()): 
            if number == halfmove_number:   
                break
            self.board.push(move)
        
        return self.board.fen()

    def get_fen_list(self) -> list[str]:
        """Getting a list of FENs of every board position, including the initial position"""
        self.board.set_fen(self.initial_fen)
        fen_list = [self.board.fen()]

        for move in self.game.mainline_moves():
            self.board.push(move)
            fen = self.board.fen()
            fen_list.append(fen)
        
        return fen_list
    
    def get_uci_from_fens(self, start_fen: str, next_fen: str) -> str:
        """Getting the UCI move (e.g. e2e4) from the initial and final FENs where the move is made"""
        self.board.set_fen(start_fen)
        start_position = self.board.copy()

        self.board.set_fen(next_fen)
        next_position = self.board.copy()

        for move in start_position.legal_moves:
            # For each legal move in the start position, play the move on the board and check if the board position is the same as the next position
            self.board.set_fen(start_fen)
            self.board.push(move)

            if self.board.fen() == next_fen:
                return move.uci()
        
        return None
    
    def get_possible_enpassant_list(self) -> list[tuple]:
        """Getting a list of possible en passant moments, as a tuple containing the halfmove number it occurs and the target square if the capture is made"""
        self.board.set_fen(self.initial_fen)
        possible_enpassant_list = []

        for number, move in enumerate(self.game.mainline_moves()):
            self.board.push(move)

            fen = self.board.fen()
            # 4th field of FEN gives en passant target square if the move is possible else '-'
            target_square = fen.split()[3]

            if target_square != '-':
                possible_enpassant_list.append((number + 1, target_square))

        return possible_enpassant_list
    
    def get_user_enpassant_list(self, username: str, possible_enpassant_list: list[tuple]) -> list[tuple]:
        """Reducing the list of possible en passant moments to a list where the user is presented with the opportunity to make the capture"""
        user_colour = self.get_user_colour(username)
        user_enpassant_list = []

        if user_colour == 'White':
            # If user is white, we are only concerned with en passant captures onto the 6th rank
            user_enpassant_list = [element for element in possible_enpassant_list if element[1][1] == '6']
        elif user_colour == 'Black':
            # If user is black, we are only concerned with en passant captures onto the 3rd rank
            user_enpassant_list = [element for element in possible_enpassant_list if element[1][1] == '3']

        return user_enpassant_list
    
    def is_enpassant_accepted(self, user_enpassant_list: list[tuple]) -> list[bool]:
        """Getting a list of booleans indicating whether the user accepted en passant as a parallel list to the user_enpassant_list"""
        enpassant_accepted_list = []

        for element in user_enpassant_list:
            move_number = element[0]

            start_fen = self.get_fen(move_number)
            next_fen = self.get_fen(move_number + 1)

            uci_move = self.get_uci_from_fens(start_fen, next_fen)

            # get_uci_from_fens returns None if no legal move is found
            if uci_move:
                # Resetting the board to the start position
                self.board.set_fen(start_fen)
                # Convert UCI move to a chess.Move object
                move = chess.Move.from_uci(uci_move)
                # Appends True or False based on whether the move is an en passant capture
                enpassant_accepted_list.append(self.board.is_en_passant(move))
            else:
                # If en passant is possible in the final position but game ends, get_uci_from_fens returns None and user is taken to have declined en passant
                enpassant_accepted_list.append(False)

        return enpassant_accepted_list
    
    def get_enpassant_move_url_lists(self, username: str, user_enpassant_list: list[tuple], enpassant_accepted_list: list[bool]) -> tuple[list]:
        """Getting a tuple of 2 lists containing the URLs in one game where the user accepted or declined en passant (since there can be multiple en passant opportunities in one game)"""
        accepted_url_list = []
        declined_url_list = []

        user_colour = self.get_user_colour(username)
        # Appends to game URL to determine which board perspective (white or black) the game URL will load
        url = self.get_url() + '/' + user_colour.lower() 

        for i in range(len(user_enpassant_list)):
            halfmove_number = user_enpassant_list[i][0]
            # Appends the halfmove number to the game URL to load the game URL at that position
            move_url = url + '#' + str(halfmove_number)

            if enpassant_accepted_list[i]:
                accepted_url_list.append(move_url)
            else:
                declined_url_list.append(move_url)

        return accepted_url_list, declined_url_list