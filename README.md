# NosyPet

A virtual pet web app inspired by Pou and Tamagotchi.
Feed it, play with it, let it sleep, and watch it grow.

## Stack
- Backend: Django 5.x (Python)
- Frontend: HTML, CSS, vanilla JavaScript
- Database: SQLite (development), Postgres (production)
- Static files: WhiteNoise
- Server: Gunicorn

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

## Configuration

All environment-driven settings live in `.env` (copy from `.env.example`).
Settings are loaded with `python-decouple`. The defaults make `runserver`
work without any `.env` file.

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Required in production |
| `DJANGO_DEBUG` | `True` in dev, `False` in prod |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated list of hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated origins for CSRF |
| `DATABASE_URL` | Postgres URL; falls back to SQLite |

## Project structure

- `nosypet/` project settings and root URL config
- `accounts/` user authentication, signup, signal that creates a Pet
- `pets/` Pet model, services, JSON API, dashboard, shop
- `templates/` shared base + auth templates
- `static/pets/` CSS and JS for the dashboard

## Game loop

1. Sign up. A Pet is created automatically (egg stage, level 1).
2. Stats decay over time (computed on every read; no background worker needed).
3. Feed, play, sleep restore stats and earn XP and coins.
4. XP fills the bar, the pet levels up, and progresses through stages: egg, baby, teen, adult.
5. Spend coins in the shop on snacks, toys, and potions for bigger boosts.

## Deployment

The project ships with `Procfile`, `runtime.txt`, WhiteNoise, and
`dj-database-url`, so it deploys cleanly to Railway, Render, or Heroku-like
platforms. Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`,
`DJANGO_ALLOWED_HOSTS`, and `DATABASE_URL` in the platform dashboard,
then run a one-off `python manage.py collectstatic --noinput`.

## Status
All 11 phases implemented: foundation through production prep.
