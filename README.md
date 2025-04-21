# En Passant Analyser

Inspired by [Rosen Score](https://rosenscore.com/)

https://github.com/fitztrev/rosen-score/

This repository is a Python-based tool that extracts a user's games from https://lichess.org and determines **en passant** statistics.

Key features:
- Extracts games using the [Lichess API](https://lichess.org/api).
- Analyses en passant opportunities and outcomes.
- Stores results in a database for faster subsequent queries.
- Provides a Flask-based web interface with user statistics and leaderboards.

Specifically, it finds all moments in a user's games where an opportunity to capture the opponent's pawn via "en passant" was presented, then checks whether the user accepted or declined the capture.

A user is queried via a form in a webpage run by a Flask application. The results are then generated in a new webpage, along with leaderboards for all users who have been queried.

Since it takes a long time to extract all a user's game using the Lichess API, especially if they have many games, results for queried users are stored in a database for subsequent retrieval. This database is also used to display the leaderboards.

When a user who is already in the database is queried subsequently, the program only extracts new games from the API and updates that user's statistics.

## Setup

Follow these steps to setup and run En Passant Analyser:

### 1. Clone Repository
```bash
git clone https://github.com/drdexe/en-passant-analyser.git
cd en-passant-analyser
```

### 2. Setup Virtual Environment
Create and activate a virtual environment to manage dependencies.

#### On Windows:
```bash
python -m venv .venv
.venv\Scripts\Activate
```

#### On macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
Install the required Python packages in your virtual environment using Package Installer for Python ([PIP](https://pypi.org/project/pip/)).
```bash
pip install -r requirements.txt
```

### 4. Run Application
```bash
python main.py
```
will start a local server at https://localhost:5000/.

By default, application uses (or creates if it does not exist) `en_passant_stats.db` in the project directory as the SQLite database. If you want to specify a different database, use the `--db` argument:
```bash
python main.py --db custom_database_name.db
```

## How it works

The Lichess API provides games in [Portable Game Notation](https://en.wikipedia.org/wiki/Portable_Game_Notation) (PGN) format. It provides game metadata and the moves in algebraic notation. However, this format is not very helpful as tracking board states is tedious with moves having to be manually played through from the start.

[Forsyth-Edwards Notation](https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation) (FEN) is more useful as it gives the board state in a specific position. The 4th field of the FEN gives the target square if en passant is possible.

The [python-chess](https://python-chess.readthedocs.io/en/latest/) package solves this issue by providing many useful functions to run analysis on chess games, such as allowing conversion from PGN to FENs and checking whether a move is
an en passant capture.

```python
import chess

board = chess.Board()
board.set_fen(chess.STARTING_FEN)

board.push(chess.Move.from_uci('e2e4'))
board.push(chess.Move.from_uci('e7e6'))
board.push(chess.Move.from_uci('e4e5'))
# En passant not possible, target square field is '-'
>>> board.fen()
'rnbqkbnr/pppp1ppp/4p3/4P3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2'

board.push(chess.Move.from_uci('d7d5'))
# En passant possible, target square field is 'd6'
>>> board.fen()
'rnbqkbnr/ppp2ppp/4p3/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3'

# En passant capture made
>>> board.is_en_passant(chess.Move.from_uci('e5d6'))
True
# En passant capture not made
>>> board.is_en_passant(chess.Move.from_uci('d2d4'))
False
```