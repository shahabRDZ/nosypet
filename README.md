# NosyPet

A virtual pet web app inspired by Pou and Tamagotchi.
Feed it, play with it, let it sleep, and watch it grow.

## Stack
- Backend: Django 5.x (Python)
- Frontend: HTML, CSS, vanilla JavaScript
- Database: SQLite (development), Postgres (production)

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

## Project structure

- `nosypet/` project settings and root URL config
- `accounts/` user authentication and profiles
- `pets/` pet model, actions, and game logic

## Status
Phase 1 of 11: Foundation complete.
