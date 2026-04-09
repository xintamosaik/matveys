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
- Player 1 run: Left Shift (no stamina limit)
- Player 1 fire: Space (first 2 shots are smoke grenades)
- Player 1 controller: Left Stick or D-pad move, LB/RB run, A/B/X/Y fire
- Player 2 move: Arrow keys
- Player 2 run: Right Shift (no stamina limit)
- Player 2 fire: Right Ctrl (first 2 shots are smoke grenades)
- Player 2 controller: Left Stick or D-pad move, LB/RB run, A/B/X/Y fire
- Exit anytime: Esc
- Quit: close the window

## Game rules

- The map has walls that block movement and bullets.
- Each player starts with 5 HP.
- Each player starts with 2 smoke grenades and they auto-refill (1 charge every 20 seconds, up to 2).
- Smoke grenades create a large AOE cloud where players can hide.
- Hidden players cannot be seen and cannot be hit by direct bullets while inside smoke.
- First player to reduce the opponent to 0 HP wins.

## Project files

- main.py: starter game loop and rendering
- requirements.txt: pinned pygame dependency range
- .gitignore: Python and virtual environment ignores

-