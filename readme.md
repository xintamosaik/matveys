# Pygame Starter

A minimal two-player arena game using pygame.

## 1) Create and activate a virtual environment

Linux/macOS:

python3 -m venv .venv
source .venv/bin/activate

Windows (PowerShell):

python -m venv .venv
.venv\Scripts\Activate.ps1

## 2) Install dependencies

pip install -r requirements.txt

## 3) Run the game

python main.py

## Controls

- Player 1 move: W A S D
- Player 1 shoot: Space
- Player 2 move: Arrow keys
- Player 2 shoot: Right Ctrl
- Exit after match: Esc
- Quit: close the window

## Game rules

- The map has walls that block movement and bullets.
- Each player starts with 5 HP.
- First player to reduce the opponent to 0 HP wins.

## Project files

- main.py: starter game loop and rendering
- requirements.txt: pinned pygame dependency range
- .gitignore: Python and virtual environment ignores

-