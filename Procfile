release: python manage.py migrate --noinput
web: gunicorn nosypet.wsgi:application --bind 0.0.0.0:$PORT --workers 3
